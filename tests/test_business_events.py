import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.gateway.app import main
from apps.gateway.app.billing import UsageEvent
from apps.gateway.app.business_events import daily_snapshot, snapshot_page
from apps.gateway.app.business_event_worker import dispatch
from apps.gateway.app.operations import IntegrationOutbox


@pytest.fixture
def store(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    for model in (main.Tenant, UsageEvent, IntegrationOutbox):
        model.__table__.create(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(main, "DB", factory)
    with factory() as s:
        s.add_all([main.Tenant(id="a", name="A"), main.Tenant(id="b", name="B")])
        s.commit()
    yield factory
    engine.dispose()


def meter(s, tenant, key, quantity=1, day=None, unit="accepted_message"):
    day = day or datetime.now(timezone.utc).date() - timedelta(days=1)
    s.add(UsageEvent(id=key, tenant_id=tenant, subscription_id="sub", event_key=key,
                     unit=unit, quantity=quantity, price_id="price",
                     occurred_at=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)))


def test_usage_is_tenant_unit_and_utc_day_scoped_and_replayable(store):
    day = datetime.now(timezone.utc).date() - timedelta(days=1)
    with store() as s:
        meter(s, "a", "one", 3)
        meter(s, "b", "other-tenant", 99)
        meter(s, "a", "other-unit", 99, unit="storage")
        meter(s, "a", "other-day", 99, day=day-timedelta(days=1))
        first = daily_snapshot(s, "a", day)
        s.commit()
        original = first.payload_json
        assert json.loads(original)["event"]["data"]["quantity"] == 3
        assert daily_snapshot(s, "a", day).id == first.id
        meter(s, "a", "late", 2)
        revised = daily_snapshot(s, "a", day)
        s.commit()
        assert revised.id != first.id
        assert json.loads(revised.payload_json)["event"]["data"]["quantity"] == 5
        assert s.get(IntegrationOutbox, first.id).payload_json == original


def test_snapshot_rollback_does_not_acknowledge_or_publish(store):
    day = datetime.now(timezone.utc).date() - timedelta(days=1)
    with store() as s:
        daily_snapshot(s, "a", day)
        s.rollback()
        assert s.scalar(select(IntegrationOutbox)) is None
        assert snapshot_page(s, day, limit=1) == "a"
        s.commit()
        assert snapshot_page(s, day, after="a", limit=1) == "b"
        with pytest.raises(ValueError, match="closed"):
            daily_snapshot(s, "a", datetime.now(timezone.utc).date())


@pytest.mark.parametrize("response", [
    httpx.Response(200, text="<!DOCTYPE html><html>login</html>"),
    httpx.Response(202, text="<!DOCTYPE html>"),
    httpx.Response(202, json={"status": "ACCEPTED"}),
    httpx.Response(503, json={"error": "offline"}),
    httpx.Response(302, headers={"location": "https://elsewhere.invalid"}),
])
def test_transport_failure_retains_event_then_recovery_drains(store, monkeypatch, response):
    import apps.gateway.app.business_event_worker as worker
    day = datetime.now(timezone.utc).date() - timedelta(days=1)
    with store() as s:
        item = daily_snapshot(s, "a", day)
        s.commit()
        item_id, original = item.id, item.payload_json
    monkeypatch.setenv("KLYROW_BUSINESS_EVENTS_URL", "https://middleware.test/internal/v1/events/klyrow")
    monkeypatch.setattr(main, "runtime_secret", lambda _: "fixture-service-identity")
    requests = []
    outcomes = [response, httpx.Response(202, json={"operation_id": "op-1", "status": "ACCEPTED"})]
    real_client = httpx.AsyncClient
    def handler(request):
        requests.append(json.loads(request.content))
        return outcomes.pop(0)
    monkeypatch.setattr(worker.httpx, "AsyncClient", lambda **kwargs: real_client(
        transport=httpx.MockTransport(handler), **kwargs))
    assert asyncio.run(dispatch()) == 0
    with store() as s:
        row = s.get(IntegrationOutbox, item_id)
        assert row.state == "RETRY" and row.payload_json == original
        row.next_attempt_at = datetime.now(timezone.utc)-timedelta(seconds=1)
        s.commit()
    assert asyncio.run(dispatch()) == 1
    assert requests[0] == requests[1]
    with store() as s:
        assert s.get(IntegrationOutbox, item_id).state == "COMPLETED"


def test_expired_last_attempt_goes_to_dlq_without_loss(store, monkeypatch):
    day = datetime.now(timezone.utc).date()-timedelta(days=1)
    with store() as s:
        row = daily_snapshot(s, "a", day)
        row.state = "PROCESSING"
        row.attempts = 8
        row.lease_expires_at = datetime.now(timezone.utc)-timedelta(seconds=1)
        s.commit()
        item_id = row.id
    monkeypatch.setenv("KLYROW_BUSINESS_EVENTS_URL", "https://middleware.test/internal/v1/events/klyrow")
    monkeypatch.setattr(main, "runtime_secret", lambda _: "fixture-service-identity")
    assert asyncio.run(dispatch()) == 0
    with store() as s:
        row = s.get(IntegrationOutbox, item_id)
        assert row.state == "DEAD_LETTER" and row.payload_json


def test_stale_worker_cannot_complete_another_workers_lease(store, monkeypatch):
    import apps.gateway.app.business_event_worker as worker
    day = datetime.now(timezone.utc).date()-timedelta(days=1)
    with store() as s:
        row = daily_snapshot(s, "a", day)
        s.commit()
        item_id = row.id
    monkeypatch.setenv("KLYROW_BUSINESS_EVENTS_URL", "https://middleware.test/internal/v1/events/klyrow")
    monkeypatch.setattr(main, "runtime_secret", lambda _: "fixture-service-identity")
    def handler(request):
        with store() as s:
            row = s.get(IntegrationOutbox, item_id)
            row.attempts += 1
            row.lease_expires_at = datetime.now(timezone.utc)+timedelta(minutes=2)
            s.commit()
        return httpx.Response(202, json={"operation_id": "op-1", "status": "ACCEPTED"})
    real_client = httpx.AsyncClient
    monkeypatch.setattr(worker.httpx, "AsyncClient", lambda **kwargs: real_client(
        transport=httpx.MockTransport(handler), **kwargs))
    assert asyncio.run(dispatch()) == 0
    with store() as s:
        row = s.get(IntegrationOutbox, item_id)
        assert row.state == "PROCESSING" and row.attempts == 2
