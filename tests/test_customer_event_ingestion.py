import os
from datetime import datetime

os.environ.update(
    KLYROW_DATABASE_URL="sqlite:///./customer-event-test.db",
    KLYROW_SESSION_SECRET="test-session-secret-at-least-32-bytes",
    KLYROW_WEBHOOK_SECRET="hook-secret",
    KLYROW_SAFE_MODE="true",
    KLYROW_RATE_PER_MINUTE="1000",
    KLYROW_AUTH_RATE_PER_MINUTE="1000",
)

from fastapi.testclient import TestClient

from apps.gateway.app.main import Base, DB, Tenant, User, app, engine, ph


client = TestClient(app)


def setup_module():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with DB() as session:
        for tenant in ("event-tenant", "batch-tenant", "lookup-tenant", "other-event-tenant", "other"):
            session.add(Tenant(id=tenant, name=tenant, quota=100))
            session.add(User(id=tenant, tenant_id=tenant, email=f"{tenant}@example.com", password_hash=ph.hash("long-enough-password"), role="tenant_admin"))
        session.commit()


def headers(tenant: str = "event-tenant") -> dict[str, str]:
    response = client.post("/v1/auth/login", json={"email": f"{tenant}@example.com", "password": "long-enough-password"})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def profile(tenant: str = "event-tenant") -> str:
    response = client.post(
        "/v1/profiles",
        headers=headers(tenant),
        json={"external_id": f"crm-{tenant}"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_event_idempotency_is_tenant_and_source_scoped():
    profile_id = profile()
    payload = {
        "profile_id": profile_id,
        "name": "checkout.completed",
        "source": "storefront",
        "idempotency_key": "checkout-42",
        "properties": {"order": "42"},
    }
    first = client.post("/v1/events", headers=headers(), json=payload)
    replay = client.post("/v1/events", headers=headers(), json=payload)
    assert first.status_code == replay.status_code == 202
    assert replay.json() == {"id": first.json()["id"], "accepted": True, "replayed": True}

    conflict = client.post("/v1/events", headers=headers(), json={**payload, "name": "checkout.failed"})
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "event_idempotency_conflict"

    other_profile = profile("other-event-tenant")
    other = client.post("/v1/events", headers=headers("other-event-tenant"), json={**payload, "profile_id": other_profile})
    assert other.status_code == 202
    assert other.json()["id"] != first.json()["id"]


def test_batch_reports_partial_failures_without_losing_valid_events():
    profile_id = profile("batch-tenant")
    response = client.post(
        "/v1/events/batch",
        headers=headers("batch-tenant"),
        json={"events": [
            {"profile_id": profile_id, "name": "valid", "idempotency_key": "one"},
            {"profile_id": "foreign-profile", "name": "invalid"},
            {"profile_id": profile_id, "name": "also.valid", "idempotency_key": "two"},
        ]},
    )
    assert response.status_code == 207, response.text
    assert response.json()["accepted"] == 2
    assert response.json()["rejected"] == 1
    timeline = client.get(f"/v1/profiles/{profile_id}/timeline", headers=headers("batch-tenant"))
    assert {event["name"] for event in timeline.json()} == {"valid", "also.valid"}


def test_event_requires_timezone_and_lookup_is_tenant_scoped():
    profile_id = profile("lookup-tenant")
    naive = client.post(
        "/v1/events",
        headers=headers("lookup-tenant"),
        json={"profile_id": profile_id, "name": "bad.time", "occurred_at": datetime(2026, 1, 1).isoformat()},
    )
    assert naive.status_code == 422
    assert naive.json()["detail"] == "occurred_at_timezone_required"

    found = client.get("/v1/profiles/lookup", headers=headers("lookup-tenant"), params={"external_id": "crm-lookup-tenant"})
    assert found.status_code == 200
    assert found.json()["id"] == profile_id
    assert client.get("/v1/profiles/lookup", headers=headers("other"), params={"external_id": "crm-lookup-tenant"}).status_code == 404
    assert client.get("/v1/profiles/lookup", headers=headers("lookup-tenant"), params={"external_id": "x", "phone": "y"}).status_code == 422


def test_header_replay_binds_complete_timestamp_payload():
    pid = profile()
    h = {**headers(), "Idempotency-Key": "header-timestamp"}
    payload = {"profile_id": pid, "name": "clock", "occurred_at": "2026-01-01T00:00:00Z"}
    first = client.post("/v1/events", headers=h, json=payload)
    assert first.status_code == 202, first.text
    replay = client.post("/v1/events", headers=h, json={**payload, "occurred_at": "2025-12-31T19:00:00-05:00"})
    assert replay.json()["replayed"] is True
    assert replay.json()["id"] == first.json()["id"]
    assert client.post("/v1/events", headers=h, json={**payload, "occurred_at": "2026-01-02T00:00:00Z"}).status_code == 409
    assert client.post("/v1/events", headers=h, json={"profile_id": pid, "name": "clock"}).status_code == 409
    assert client.post("/v1/events", headers=h, json={**payload, "idempotency_key": "different"}).status_code == 422


def test_batch_header_replays_items_and_preserves_partial_conflicts():
    pid = profile()
    h = {**headers(), "Idempotency-Key": "batch-header"}
    items = [{"profile_id": pid, "name": "batch.first"}, {"profile_id": pid, "name": "batch.second"}]
    first = client.post("/v1/events/batch", headers=h, json={"events": items})
    replay = client.post("/v1/events/batch", headers=h, json={"events": items})
    assert first.status_code == replay.status_code == 207
    assert all(r["replayed"] for r in replay.json()["results"])
    assert [r["id"] for r in first.json()["results"]] == [r["id"] for r in replay.json()["results"]]
    changed = client.post("/v1/events/batch", headers=h, json={"events": [items[0], {**items[1], "name": "changed"}]})
    assert changed.json()["accepted"] == changed.json()["rejected"] == 1
    assert changed.json()["results"][1]["code"] == "event_idempotency_conflict"


def test_event_openapi_describes_optional_header_and_non_atomic_batch():
    schema = app.openapi()
    for path, model in [("/v1/events", "OPTIONAL_REQUEST_SCOPED"), ("/v1/events/batch", "OPTIONAL_ITEM_SCOPED_NON_ATOMIC")]:
        operation = schema["paths"][path]["post"]
        assert operation["x-idempotency-required"] is False
        assert operation["x-idempotency-model"] == model
        assert any(p["name"].lower() == "idempotency-key" for p in operation["parameters"])
