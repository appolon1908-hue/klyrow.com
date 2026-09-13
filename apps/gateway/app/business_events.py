"""Versioned business facts; persistence is part of the caller's transaction.

The business worker delivers these facts only to Middleware. It never loads
an Odoo credential, and mail acceptance never waits for this transport.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select

SOURCES = ("klyrow", "telnexa", "vicidial", "integration")
KLYROW_EVENTS = (
    "klyrow.tenant.created", "klyrow.subscription.changed", "klyrow.email.accepted",
    "klyrow.email.delivered", "klyrow.email.bounced", "klyrow.email.complained",
    "klyrow.campaign.summary", "klyrow.usage.daily", "klyrow.kpi.daily",
    "klyrow.domain.status", "klyrow.provider.health", "klyrow.account.held",
)


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=200)
    type: str = Field(pattern=r"^[a-z]+\.[a-z][a-z0-9_.]+$", max_length=120)
    version: Literal[1] = 1
    source: Literal["klyrow", "telnexa", "vicidial", "integration"]
    tenant_id: str = Field(min_length=1, max_length=200)
    correlation_id: str = Field(min_length=1, max_length=200)
    causation_id: str = Field(min_length=1, max_length=200)
    occurred_at: AwareDatetime
    data: dict

    @field_validator("occurred_at")
    @classmethod
    def utc(cls, value):
        return value.astimezone(timezone.utc)


class DailyUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: date
    unit: Literal["accepted_message"] = "accepted_message"
    quantity: int = Field(ge=0)
    # Each revision is an immutable snapshot. Consumers upsert the daily key
    # using snapshot_at ordering; they must never add snapshot totals together.
    snapshot_at: AwareDatetime


def enqueue_event(session, event: EventEnvelope):
    from .operations import IntegrationOutbox
    from .telemetry import trace_carrier

    if event.source != "klyrow" or event.type not in KLYROW_EVENTS:
        raise ValueError("unsupported_klyrow_business_event")
    if event.type == "klyrow.usage.daily":
        DailyUsage.model_validate(event.data)
    key = "codestra:event:" + event.id
    existing = session.scalar(select(IntegrationOutbox).where(
        IntegrationOutbox.tenant_id == event.tenant_id,
        IntegrationOutbox.target == "MIDDLEWARE",
        IntegrationOutbox.idempotency_key == key,
    ))
    document = event.model_dump(mode="json")
    if existing:
        if json.loads(existing.payload_json)["event"] != document:
            raise ValueError("business_event_idempotency_conflict")
        return existing
    item = IntegrationOutbox(
        id=str(uuid.uuid4()), tenant_id=event.tenant_id, target="MIDDLEWARE",
        event_type=event.type, aggregate_id=event.id, idempotency_key=key,
        payload_json=json.dumps({"event": document, "trace_context": trace_carrier()},
                                separators=(",", ":"), sort_keys=True),
    )
    session.add(item)
    return item


def daily_snapshot(session, tenant_id: str, day: date):
    """Snapshot one closed UTC day from the authoritative metering ledger.

Locking the tenant serializes snapshot revisions. A changed ledger produces a
new immutable event; unchanged replays return the original stored envelope.
"""
    from .billing import UsageEvent
    from .main import Tenant
    from .operations import IntegrationOutbox

    current = datetime.now(timezone.utc)
    if day >= current.date():
        raise ValueError("usage_day_must_be_closed")
    if session.get_bind().dialect.name == "postgresql":
        session.execute(select(func.set_config("statement_timeout", "5000", True)))
    if session.scalar(select(Tenant.id).where(Tenant.id == tenant_id).with_for_update()) is None:
        raise ValueError("tenant_not_found")
    current = datetime.now(timezone.utc)
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    if session.get_bind().dialect.name == "postgresql":
        session.execute(select(func.set_config("statement_timeout", "5000", True)))
    quantity = int(session.scalar(select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(
        UsageEvent.tenant_id == tenant_id, UsageEvent.unit == "accepted_message",
        UsageEvent.occurred_at >= start, UsageEvent.occurred_at < end,
    )))
    aggregate = f"usage:{tenant_id}:{day.isoformat()}"
    prior = session.scalar(select(IntegrationOutbox).where(
        IntegrationOutbox.tenant_id == tenant_id, IntegrationOutbox.target == "MIDDLEWARE",
        IntegrationOutbox.event_type == "klyrow.usage.daily", IntegrationOutbox.aggregate_id == aggregate,
    ).order_by(IntegrationOutbox.created_at.desc(), IntegrationOutbox.id.desc()).limit(1))
    if prior and json.loads(prior.payload_json)["event"]["data"]["quantity"] == quantity:
        return prior
    if prior:
        previous_time = datetime.fromisoformat(json.loads(prior.payload_json)["event"]["data"]["snapshot_at"].replace("Z", "+00:00"))
        current = max(current, previous_time + timedelta(microseconds=1))
    event_id = "evt_" + uuid.uuid4().hex
    data = DailyUsage(date=day, quantity=quantity, snapshot_at=current)
    event = EventEnvelope(id=event_id, type="klyrow.usage.daily", source="klyrow",
                          tenant_id=tenant_id, correlation_id=event_id, causation_id=aggregate,
                          occurred_at=current, data=data.model_dump(mode="json"))
    item = enqueue_event(session, event)
    item.aggregate_id = aggregate
    item.created_at = current
    return item


def snapshot_page(session, day: date, after: str = "", limit: int = 100):
    """Bounded keyset traversal; persist every page before advancing the cursor."""
    from .main import Tenant
    if not 1 <= limit <= 100:
        raise ValueError("invalid_snapshot_page_limit")
    tenants = list(session.scalars(select(Tenant.id).where(Tenant.id > after).order_by(Tenant.id).limit(limit)))
    for tenant_id in tenants:
        daily_snapshot(session, tenant_id, day)
    return tenants[-1] if len(tenants) == limit else None
