"""Bounded asynchronous Mautic adapter backed by the durable integration outbox."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import quote, urlsplit

import httpx
from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .main import Base, DB, runtime_secret
from .operations import IntegrationOutbox, IntegrationResult


now = lambda: datetime.now(timezone.utc)
MAX_ATTEMPTS = 5
LEASE_SECONDS = 30


class MauticAdapterState(Base):
    __tablename__ = "mautic_adapter_state"

    state_key: Mapped[str] = mapped_column(String, primary_key=True)
    failure_streak: Mapped[int] = mapped_column(Integer, default=0)
    circuit_open_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_success_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def _bounded_id(value: Any, field: str) -> str:
    if not isinstance(value, (str, int)):
        raise ValueError(field + "_required")
    result = str(value).strip()
    if not result or len(result) > 160 or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in result):
        raise ValueError(field + "_invalid")
    return quote(result, safe="")


def mautic_request(command: str, payload: dict[str, Any]) -> tuple[str, str, dict[str, Any] | None]:
    """Translate the governed command vocabulary into Mautic's canonical API."""

    provider_id = payload.get("provider_id")
    if command.startswith("contact."):
        resource = "contacts"
    elif command.startswith("segment."):
        resource = "segments"
    elif command.startswith("campaign."):
        resource = "campaigns"
    else:
        resource = ""

    if command.endswith(".upsert.v1") and resource:
        path = f"/api/v2/{resource}"
        if provider_id is not None:
            path += "/" + _bounded_id(provider_id, "provider_id")
        body = {key: value for key, value in payload.items() if key != "provider_id"}
        return ("PATCH" if provider_id is not None else "POST", path, body)
    if command.endswith(".delete.v1") and resource:
        return "DELETE", f"/api/v2/{resource}/{_bounded_id(provider_id, 'provider_id')}", None
    if command in {"campaign.publish.v1", "campaign.pause.v1"}:
        return (
            "PATCH",
            "/api/v2/campaigns/" + _bounded_id(provider_id, "provider_id"),
            {"isPublished": command == "campaign.publish.v1"},
        )
    if command in {"campaign_membership.add.v1", "campaign_membership.remove.v1"}:
        campaign_id = _bounded_id(payload.get("campaign_id"), "campaign_id")
        contact_id = _bounded_id(payload.get("contact_id"), "contact_id")
        action = "add" if command.endswith("add.v1") else "remove"
        return "POST", f"/api/campaigns/{campaign_id}/contact/{contact_id}/{action}", {}
    if command == "email_campaign.state.v1":
        email_id = _bounded_id(payload.get("email_id"), "email_id")
        return "PATCH", f"/api/v2/emails/{email_id}", {"isPublished": bool(payload.get("published"))}
    if command == "event.record.v1":
        return "POST", "/api/v2/events", payload
    if command == "webhook.register.v1":
        return "POST", "/api/v2/webhooks", payload
    if command == "sync.request.v1":
        resource_name = payload.get("resource")
        if resource_name not in {"contacts", "segments", "campaigns", "emails", "events", "webhooks"}:
            raise ValueError("sync_resource_invalid")
        path = "/api/v2/" + resource_name
        if provider_id is not None:
            path += "/" + _bounded_id(provider_id, "provider_id")
        return "GET", path, None
    raise ValueError("mautic_command_unsupported")


def _configuration() -> tuple[str, str]:
    base_url = os.getenv("KLYROW_MAUTIC_API_URL", "http://mautic").rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme != "http" or parsed.hostname != "mautic" or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError("KLYROW_MAUTIC_API_URL must be the private http://mautic endpoint")
    token = runtime_secret("KLYROW_MAUTIC_API_TOKEN")
    if len(token.encode()) < 32:
        raise RuntimeError("KLYROW_MAUTIC_API_TOKEN must contain at least 32 bytes")
    return base_url, token


def _recover_expired(session: Session, current: datetime) -> None:
    rows = session.scalars(
        select(IntegrationOutbox).where(
            IntegrationOutbox.target == "MAUTIC",
            IntegrationOutbox.state == "PROCESSING",
            IntegrationOutbox.lease_expires_at < current,
        )
    ).all()
    for item in rows:
        item.state = "DEAD_LETTER"
        item.last_error = "worker_lease_expired_ambiguous"
        item.lease_expires_at = None
        item.updated_at = current
    session.commit()


def _claim(session: Session) -> IntegrationOutbox | None:
    current = now()
    _recover_expired(session, current)
    circuit = session.get(MauticAdapterState, "primary")
    if circuit and circuit.circuit_open_until and circuit.circuit_open_until > current:
        return None
    item = session.scalar(
        select(IntegrationOutbox)
        .where(
            IntegrationOutbox.target == "MAUTIC",
            IntegrationOutbox.state.in_(("PENDING", "RETRY")),
            IntegrationOutbox.next_attempt_at <= current,
        )
        .order_by(IntegrationOutbox.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if item:
        item.state = "PROCESSING"
        item.attempts += 1
        item.lease_expires_at = current + timedelta(seconds=LEASE_SECONDS)
        item.updated_at = current
        session.commit()
    return item


def _failure(session: Session, item_id: str, error: str, *, retryable: bool) -> None:
    current = now()
    item = session.get(IntegrationOutbox, item_id)
    circuit = session.get(MauticAdapterState, "primary") or MauticAdapterState(state_key="primary")
    circuit.failure_streak += 1
    circuit.last_failure_at = current
    circuit.updated_at = current
    if circuit.failure_streak >= 5:
        circuit.circuit_open_until = current + timedelta(seconds=60)
    session.add(circuit)
    if item:
        can_retry = retryable and item.attempts < MAX_ATTEMPTS
        item.state = "RETRY" if can_retry else "DEAD_LETTER"
        item.next_attempt_at = current + timedelta(seconds=min(300, 2 ** item.attempts))
        item.lease_expires_at = None
        item.last_error = error[:500]
        item.updated_at = current
    session.commit()


def _success(session: Session, item_id: str, response: dict[str, Any]) -> None:
    current = now()
    item = session.get(IntegrationOutbox, item_id)
    if not item:
        return
    item.state = "COMPLETED"
    item.lease_expires_at = None
    item.last_error = None
    item.updated_at = current
    result_key = "mautic:" + item.id
    if not session.scalar(select(IntegrationResult).where(IntegrationResult.result_key == result_key)):
        session.add(IntegrationResult(id=item.id, tenant_id=item.tenant_id, outbox_id=item.id, source="MAUTIC", result_key=result_key, payload_json=json.dumps(response, separators=(",", ":"), sort_keys=True)))
    circuit = session.get(MauticAdapterState, "primary") or MauticAdapterState(state_key="primary")
    circuit.failure_streak = 0
    circuit.circuit_open_until = None
    circuit.last_success_at = current
    circuit.updated_at = current
    session.add(circuit)
    session.commit()


async def dispatch_mautic_outbox(limit: int = 20) -> dict[str, int]:
    completed = failed = 0
    try:
        base_url, token = _configuration()
    except RuntimeError:
        return {"completed": 0, "failed": 0, "disabled": 1}
    timeout = httpx.Timeout(10.0, connect=3.0)
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, follow_redirects=False) as client:
        for _ in range(limit):
            with DB() as session:
                item = _claim(session)
                if not item:
                    break
                snapshot = (item.id, item.event_type, json.loads(item.payload_json), item.idempotency_key)
            item_id, command, stored, idempotency_key = snapshot
            try:
                method, path, body = mautic_request(command, stored.get("payload") or {})
                response = await client.request(method, path, json=body, headers={"Authorization": "Bearer " + token, "Idempotency-Key": idempotency_key, "X-Correlation-ID": stored["envelope"]["correlation_id"], "Accept": "application/json"})
                if response.status_code == 429:
                    raise httpx.HTTPStatusError("mautic_rate_limited", request=response.request, response=response)
                if response.status_code >= 500:
                    with DB() as session:
                        _failure(session, item_id, "mautic_ambiguous_http_" + str(response.status_code), retryable=False)
                    failed += 1
                    continue
                response.raise_for_status()
                if len(response.content) > 1048576:
                    raise RuntimeError("mautic_response_too_large")
                result = response.json() if response.content else {"status_code": response.status_code}
                with DB() as session:
                    _success(session, item_id, result)
                completed += 1
            except httpx.HTTPStatusError as error:
                retryable = error.response.status_code == 429
                with DB() as session:
                    _failure(session, item_id, "mautic_http_" + str(error.response.status_code), retryable=retryable)
                failed += 1
            except httpx.ConnectError:
                with DB() as session:
                    _failure(session, item_id, "mautic_connect_error", retryable=True)
                failed += 1
            except (httpx.TimeoutException, httpx.TransportError):
                with DB() as session:
                    _failure(session, item_id, "mautic_transport_ambiguous", retryable=False)
                failed += 1
            except (KeyError, TypeError, ValueError, RuntimeError, json.JSONDecodeError) as error:
                with DB() as session:
                    _failure(session, item_id, type(error).__name__, retryable=False)
                failed += 1
    return {"completed": completed, "failed": failed, "disabled": 0}


async def mautic_worker_loop() -> None:
    while True:
        await dispatch_mautic_outbox()
        await asyncio.sleep(2)
