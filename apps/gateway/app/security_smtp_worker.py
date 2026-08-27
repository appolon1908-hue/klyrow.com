"""Postal delivery worker for governed, non-sandbox provider messages.

SECURITY mail retains its dedicated gates. Other streams require the separate
provider live-delivery gate. Transport selection is sender-domain aware, so a
domain hosted on a second Postal server never receives the default credential.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid
from datetime import timedelta
from email import policy
from email.message import Message
from email.parser import BytesParser
from typing import Any

import httpx
from sqlalchemy import select

from .main import DB
from .postal_transport import postal_headers, resolve_postal_transport
from .provider import ProviderAudit, ProviderEvent, ProviderMessage, TenantMailPolicy, now
from .smtp_policy import security_live_delivery_enabled

MAX_ATTEMPTS = 5
LEASE_SECONDS = 120


def _decode_part(part: Message) -> str:
    try:
        content = part.get_content()
    except (LookupError, UnicodeError, ValueError):
        payload = part.get_payload(decode=True) or b""
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    if isinstance(content, bytes):
        return content.decode(part.get_content_charset() or "utf-8", errors="replace")
    return str(content)


def parse_postal_body(raw: bytes) -> tuple[str, str]:
    """Extract plain and HTML bodies without including attachments."""

    message = BytesParser(policy=policy.default).parsebytes(raw)
    plain_parts: list[str] = []
    html_parts: list[str] = []
    candidates = message.walk() if message.is_multipart() else [message]
    for part in candidates:
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        content_type = part.get_content_type().lower()
        if content_type == "text/plain":
            plain_parts.append(_decode_part(part))
        elif content_type == "text/html":
            html_parts.append(_decode_part(part))
    return "\n".join(plain_parts), "\n".join(html_parts)


def postal_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Convert either governed SMTP MIME or structured API JSON for Postal."""

    encoded = snapshot["payload"].get("raw_b64")
    if isinstance(encoded, str) and encoded:
        raw = base64.b64decode(encoded, validate=True)
        plain_body, html_body = parse_postal_body(raw)
    else:
        plain_body = snapshot["payload"].get("text") or ""
        html_body = snapshot["payload"].get("html") or ""
    if not plain_body and not html_body:
        raise ValueError("provider message has no deliverable text body")
    payload: dict[str, Any] = {
        "to": [snapshot["recipient"]],
        "from": snapshot["sender"],
        "subject": snapshot["subject"],
        "tag": snapshot["correlation_id"],
        "stream": snapshot["stream"].lower(),
    }
    if plain_body:
        payload["plain_body"] = plain_body
    if html_body:
        payload["html_body"] = html_body
    reply_to = snapshot["payload"].get("reply_to")
    message_domain = snapshot["sender"].rsplit("@", 1)[-1]
    payload["headers"] = {
        "Message-ID": f'<{snapshot["id"]}@{message_domain}>',
        "X-Klyrow-Message-Id": snapshot["id"],
        "X-Klyrow-Correlation-Id": snapshot["correlation_id"],
    }
    if reply_to:
        payload["headers"]["Reply-To"] = reply_to
    tracking_mode = snapshot.get("tracking_mode", "DISABLED")
    payload["track_opens"] = tracking_mode in {"OPEN", "OPEN_CLICK"}
    payload["track_clicks"] = tracking_mode in {"CLICK", "OPEN_CLICK"}
    return payload


def enabled_live_streams() -> frozenset[str]:
    streams: set[str] = set()
    if os.getenv("KLYROW_PROVIDER_LIVE_DELIVERY_ENABLED", "false").lower() == "true":
        streams.update({"TRANSACTIONAL", "SYSTEM", "MARKETING", "BULK"})
    if security_live_delivery_enabled():
        streams.add("SECURITY")
    return frozenset(streams)


def _claim_one() -> dict[str, Any] | None:
    streams = enabled_live_streams()
    if not streams:
        return None
    with DB() as session:
        item = session.scalar(
            select(ProviderMessage)
            .where(
                ProviderMessage.stream.in_(streams),
                ProviderMessage.sandbox.is_(False),
                ProviderMessage.status.in_(["QUEUED", "DEFERRED"]),
                ProviderMessage.available_at <= now(),
                ProviderMessage.attempts < MAX_ATTEMPTS,
            )
            .order_by(ProviderMessage.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not item:
            return None
        item.status = "PROCESSING"
        item.attempts += 1
        item.lease_expires_at = now() + timedelta(seconds=LEASE_SECONDS)
        item.updated_at = now()
        tenant_policy = session.get(TenantMailPolicy, item.tenant_id)
        snapshot = {
            "id": item.id,
            "tenant_id": item.tenant_id,
            "sender": item.sender,
            "recipient": item.recipient,
            "subject": item.subject,
            "stream": item.stream,
            "correlation_id": item.correlation_id,
            "idempotency_key": item.idempotency_key,
            "attempts": item.attempts,
            "tracking_mode": tenant_policy.tracking_mode if tenant_policy else "DISABLED",
            "payload": json.loads(item.payload_json),
        }
        session.commit()
        return snapshot


def _mark_submitted(snapshot: dict[str, Any], provider_message_id: str) -> None:
    with DB() as session:
        item = session.get(ProviderMessage, snapshot["id"])
        if not item or item.status != "PROCESSING":
            return
        item.status = "SUBMITTED"
        item.provider_message_id = provider_message_id
        item.lease_expires_at = None
        item.last_error = None
        item.updated_at = now()
        event_id = str(uuid.uuid4())
        session.add(
            ProviderEvent(
                id=event_id,
                tenant_id=item.tenant_id,
                message_id=item.id,
                kind="message.submitted",
                payload_json=json.dumps(
                    {
                        "event_id": event_id,
                        "tenant_id": item.tenant_id,
                        "message_id": item.id,
                        "provider_message_id": provider_message_id,
                        "correlation_id": item.correlation_id,
                        "event": "message.submitted",
                        "provider": "postal",
                        "stream": item.stream,
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            )
        )
        session.add(
            ProviderAudit(
                id=str(uuid.uuid4()),
                tenant_id=item.tenant_id,
                actor="worker:klyrow-provider-delivery",
                action="provider.message.submitted",
                outcome="accepted",
                correlation_id=item.correlation_id,
                resource_id=item.id,
            )
        )
        session.commit()


def _mark_failed(snapshot: dict[str, Any], error_name: str) -> None:
    with DB() as session:
        item = session.get(ProviderMessage, snapshot["id"])
        if not item or item.status != "PROCESSING":
            return
        exhausted = item.attempts >= MAX_ATTEMPTS
        item.status = "DEAD_LETTER" if exhausted else "DEFERRED"
        item.available_at = now() + timedelta(
            seconds=min(300, 2 ** max(item.attempts, 1))
        )
        item.lease_expires_at = None
        item.last_error = error_name[:120]
        item.updated_at = now()
        session.add(
            ProviderAudit(
                id=str(uuid.uuid4()),
                tenant_id=item.tenant_id,
                actor="worker:klyrow-provider-delivery",
                action="provider.message.delivery_failed",
                outcome="dead_letter" if exhausted else "retry",
                correlation_id=item.correlation_id,
                resource_id=item.id,
            )
        )
        session.commit()


async def process_one_live_message() -> bool:
    """Submit one eligible governed provider message to its Postal server."""

    snapshot = _claim_one()
    if snapshot is None:
        return False
    try:
        transport = resolve_postal_transport(snapshot["sender"])
        headers = postal_headers(transport, "klyrow-provider:" + snapshot["id"])
        async with httpx.AsyncClient(
            timeout=10,
            trust_env=False,
            follow_redirects=False,
        ) as client:
            response = await client.post(
                transport.api_url + "/api/v1/send/message",
                headers=headers,
                json=postal_payload(snapshot),
            )
            response.raise_for_status()
            body = response.json()
        provider_message_id = str(
            body.get("data", {}).get("message_id") or snapshot["id"]
        )
        _mark_submitted(snapshot, provider_message_id)
        return True
    except Exception as exc:  # noqa: BLE001 - error type only is persisted/logged
        _mark_failed(snapshot, type(exc).__name__)
        print(
            json.dumps(
                {
                    "level": "warning",
                    "system": "klyrow-provider-delivery",
                    "event": "postal_submission_failed",
                    "message_id": snapshot["id"],
                    "correlation_id": snapshot["correlation_id"],
                    "error": type(exc).__name__,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return False


async def process_one_security_message() -> bool:
    """Backward-compatible worker entry point retained for existing services."""

    return await process_one_live_message()


async def security_smtp_delivery_loop() -> None:
    while True:
        try:
            processed = await process_one_live_message()
        except Exception as exc:  # noqa: BLE001 - keep the worker alive
            print(
                json.dumps(
                    {
                        "level": "error",
                        "system": "klyrow-provider-delivery",
                        "event": "worker_tick_failed",
                        "error": type(exc).__name__,
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            processed = False
        await asyncio.sleep(1 if processed else 3)
