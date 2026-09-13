from __future__ import annotations

import os

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute, iter_route_contexts
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("KLYROW_DATABASE_URL", "sqlite:///./test-observability.db")
os.environ.setdefault(
    "KLYROW_SESSION_SECRET",
    "test-secret-observability-minimum-32-characters-long",
)
os.environ.setdefault("KLYROW_SAFE_MODE", "true")
os.environ.setdefault("KLYROW_ENV", "test")

from apps.gateway.app.main import Base
from apps.gateway.app.operations import IntegrationOutbox
from apps.gateway.app.platform import app
from apps.gateway.app import observability


SERVICE_CONTEXT = {
    "sub": "middleware-observability",
    "tenant": "tenant-a",
    "identity_type": "SERVICE",
    "service": True,
    "permissions": [
        observability.OBSERVABILITY_READ,
        observability.OBSERVABILITY_WRITE,
    ],
}


@pytest.fixture
def isolated_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as session:
        yield session
    engine.dispose()


def test_observability_routes_are_unique_and_openapi_classified() -> None:
    expected = {
        ("POST", "/v1/internal/integrations/alertmanager/events"),
        ("POST", "/v1/internal/integrations/kpis/snapshots"),
        ("GET", "/v1/internal/integrations/odoo/health"),
        ("GET", "/v1/internal/integrations/odoo/checkpoints"),
        ("POST", "/v1/internal/integrations/odoo/reconcile"),
        ("GET", "/v1/internal/integrations/observability/contract"),
    }
    effective_routes = [
        context.original_route
        for context in iter_route_contexts(app.routes)
        if isinstance(context.original_route, APIRoute)
    ]
    actual = {
        (method, route.path)
        for route in effective_routes
        if route.path in {path for _method, path in expected}
        for method in route.methods or set()
    }
    assert actual == expected
    for method, path in expected:
        assert sum(
            method in (route.methods or set()) and route.path == path
            for route in effective_routes
        ) == 1

    schema = app.openapi()
    reconcile = schema["paths"]["/v1/internal/integrations/odoo/reconcile"]["post"]
    for method, path in expected:
        operation = schema["paths"][path][method.lower()]
        assert operation["security"] == [{"serviceBearer": []}]
        assert operation["x-klyrow-auth-model"] == "DEDICATED_SERVICE_BEARER_ON_PRIVATE_ROUTE"
    assert reconcile["x-klyrow-audience"] == "INTERNAL"
    assert reconcile["x-idempotency-required"] is True
    assert "Idempotency-Key" in {
        parameter["name"] for parameter in reconcile["parameters"]
    }


def test_labels_fail_closed_for_customer_and_unbounded_dimensions() -> None:
    with pytest.raises(HTTPException) as exc:
        observability._normalize_labels({"tenant_id": "tenant-a"})
    assert exc.value.status_code == 422

    with pytest.raises(HTTPException) as exc:
        observability._normalize_labels({"unknown_dimension": "value"})
    assert exc.value.status_code == 422


def test_alert_firing_and_resolved_events_are_durable_and_idempotent(isolated_session) -> None:
    firing = observability.AlertmanagerEnvelope.model_validate(
        {
            "receiver": "middleware",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "KlyrowEmailQueueStalled",
                        "severity": "critical",
                        "service": "klyrow-gateway",
                        "environment": "production",
                    },
                    "annotations": {"summary": "queue stalled"},
                    "startsAt": "2026-09-12T10:00:00Z",
                    "fingerprint": "queue-stalled-fingerprint",
                }
            ],
        }
    )

    first = observability.receive_alertmanager_events(
        firing, SERVICE_CONTEXT, isolated_session, "correlation-1"
    )
    replay = observability.receive_alertmanager_events(
        firing, SERVICE_CONTEXT, isolated_session, "correlation-retry"
    )
    assert first["accepted"] == 1
    assert first["duplicates"] == 0
    assert replay["accepted"] == 0
    assert replay["duplicates"] == 1

    resolved = observability.AlertmanagerEnvelope.model_validate(
        {
            "status": "resolved",
            "alerts": [
                {
                    "status": "resolved",
                    "labels": firing.alerts[0].labels,
                    "startsAt": "2026-09-12T10:00:00Z",
                    "endsAt": "2026-09-12T10:05:00Z",
                    "fingerprint": "queue-stalled-fingerprint",
                }
            ],
        }
    )
    completed = observability.receive_alertmanager_events(
        resolved, SERVICE_CONTEXT, isolated_session, "correlation-2"
    )
    assert completed["accepted"] == 1

    rows = isolated_session.scalars(
        select(IntegrationOutbox).where(IntegrationOutbox.target == "ODOO")
    ).all()
    assert len(rows) == 2
    assert {row.event_type for row in rows} == {"KlyrowObservabilityAlertV1"}
    assert all('"direct_odoo_database_write":false' in row.payload_json for row in rows)


def test_kpi_snapshot_accepts_only_vetted_recording_rules(isolated_session) -> None:
    snapshot = observability.KpiSnapshotIn.model_validate(
        {
            "snapshot_id": "snapshot-20260912-1",
            "kpi_key": "http_error_ratio",
            "query_ref": "klyrow:http_errors:ratio5m",
            "value": 0.01,
            "unit": "ratio",
            "observed_at": "2026-09-12T10:00:00Z",
            "service": "klyrow-gateway",
            "environment": "production",
            "labels": {"service": "klyrow-gateway", "environment": "production"},
        }
    )
    response = observability.receive_kpi_snapshot(snapshot, SERVICE_CONTEXT, isolated_session)
    assert response["duplicate"] is False
    assert response["target"] == "middleware-odoo-outbox"
    assert response["direct_odoo_database_write"] is False

    with pytest.raises(ValueError, match="unapproved_prometheus_query_reference"):
        observability.KpiSnapshotIn.model_validate(
            {
                **snapshot.model_dump(),
                "snapshot_id": "snapshot-20260912-2",
                "query_ref": "up{job=\"klyrow\"}",
            }
        )


@pytest.mark.parametrize("field", ["observed_at", "window_start", "window_end"])
def test_kpi_timestamps_require_explicit_timezone(field):
    payload = {
        "snapshot_id": "timezone-test-snapshot",
        "kpi_key": "http_error_ratio",
        "query_ref": "klyrow:http_errors:ratio5m",
        "value": 0.01,
        "observed_at": "2026-09-12T10:00:00Z",
        "window_start": "2026-09-12T09:00:00Z",
        "window_end": "2026-09-12T10:00:00Z",
        "service": "gateway",
        "environment": "test",
    }
    payload[field] = "2026-09-12T10:00:00"
    with pytest.raises(ValueError, match="observability_timestamp_requires_timezone"):
        observability.KpiSnapshotIn.model_validate(payload)


def test_status_summaries_are_partitioned_by_tenant(isolated_session):
    for tenant, state in (("tenant-a", "PENDING"), ("tenant-b", "DEAD_LETTER")):
        isolated_session.add(IntegrationOutbox(
            id=tenant, tenant_id=tenant, target="ODOO", event_type="TestEvent",
            aggregate_id=tenant, payload_json="{}", idempotency_key=tenant, state=state,
        ))
    isolated_session.commit()
    assert observability._outbox_summary(isolated_session, "tenant-a")["counts"] == {"PENDING": 1}
    assert observability._outbox_summary(isolated_session, "empty")["counts"] == {}
    checkpoints = observability.odoo_checkpoints(SERVICE_CONTEXT, isolated_session)
    assert [(item["state"], item["count"]) for item in checkpoints["items"]] == [("PENDING", 1)]
