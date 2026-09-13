"""Leased, fenced delivery of immutable business facts to Middleware."""
import json
import os
import ssl
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select

from .business_events import EventEnvelope
from .telemetry import traced, trace_carrier


async def dispatch(limit=50):
    from .main import DB, runtime_secret
    from .operations import IntegrationOutbox
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("invalid_dispatch_limit")
    endpoint = os.getenv("KLYROW_BUSINESS_EVENTS_URL", "")
    if not endpoint:
        return 0
    parsed = urlsplit(endpoint)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path != "/internal/v1/events/klyrow"):
        raise ValueError("invalid_business_events_endpoint")
    credential = runtime_secret("KLYROW_BUSINESS_EVENTS_TOKEN")
    if not credential:
        return 0
    tls = ssl.create_default_context(cafile=os.getenv("KLYROW_BUSINESS_EVENTS_CA_FILE") or None)
    certificate = os.getenv("KLYROW_BUSINESS_EVENTS_CLIENT_CERT_FILE")
    private_key = os.getenv("KLYROW_BUSINESS_EVENTS_CLIENT_KEY_FILE")
    if bool(certificate) != bool(private_key):
        raise ValueError("business_events_mtls_pair_required")
    if certificate:
        tls.load_cert_chain(certificate, private_key)
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(seconds=60)
    with DB() as session:
        expired = session.scalars(select(IntegrationOutbox).where(
            IntegrationOutbox.target == "MIDDLEWARE", IntegrationOutbox.state == "PROCESSING",
            IntegrationOutbox.lease_expires_at < now,
        ).with_for_update(skip_locked=True).limit(limit)).all()
        for item in expired:
            item.state = "DEAD_LETTER" if item.attempts >= 8 else "RETRY"
            item.next_attempt_at = now
            item.lease_expires_at = None
            item.last_error = "business_event_lease_expired"
        session.flush()
        items = session.scalars(select(IntegrationOutbox).where(
            IntegrationOutbox.target == "MIDDLEWARE", IntegrationOutbox.state.in_(["PENDING", "RETRY"]),
            IntegrationOutbox.next_attempt_at <= now,
        ).order_by(IntegrationOutbox.created_at, IntegrationOutbox.id)
          .with_for_update(skip_locked=True).limit(limit)).all()
        snapshots = []
        for item in items:
            item.state = "PROCESSING"
            item.attempts += 1
            item.lease_expires_at = deadline
            snapshots.append((item.id, item.tenant_id, item.payload_json, item.attempts))
        session.commit()
    delivered = 0
    for item_id, tenant_id, raw, attempt in snapshots:
        ok = False
        try:
            payload = json.loads(raw)
            event = EventEnvelope.model_validate(payload["event"])
            if event.source != "klyrow" or event.tenant_id != tenant_id:
                raise ValueError("event_identity_mismatch")
            with traced("business event publish", payload.get("trace_context")):
                headers = {"Authorization": "Bearer " + credential,
                           "X-Correlation-Id": event.correlation_id,
                           "Idempotency-Key": event.id, **trace_carrier()}
                async with httpx.AsyncClient(timeout=5, follow_redirects=False, trust_env=False, verify=tls) as client:
                    response = await client.post(endpoint, json=event.model_dump(mode="json"), headers=headers)
                # Durable acceptance must be explicit; an HTML 200 login page
                # or a redirect can never cause a business event to disappear.
                if response.status_code == 202 and response.headers.get("content-type", "").split(";", 1)[0] == "application/json":
                    result = response.json()
                    ok = isinstance(result, dict) and result.get("status") == "ACCEPTED" and isinstance(result.get("operation_id"), str) and bool(result["operation_id"])
        except Exception:
            pass  # retain immutable payload; never log secrets or request data
        with DB() as session:
            item = session.scalar(select(IntegrationOutbox).where(
                IntegrationOutbox.id == item_id, IntegrationOutbox.target == "MIDDLEWARE",
                IntegrationOutbox.state == "PROCESSING", IntegrationOutbox.attempts == attempt,
                IntegrationOutbox.lease_expires_at == deadline,
            ).with_for_update())
            if item is None:
                continue
            item.state = "COMPLETED" if ok else ("DEAD_LETTER" if attempt >= 8 else "RETRY")
            item.last_error = None if ok else "business_event_not_accepted"
            item.lease_expires_at = None
            item.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=min(900, 2 ** attempt))
            item.updated_at = datetime.now(timezone.utc)
            session.commit()
        delivered += int(ok)
    return delivered
