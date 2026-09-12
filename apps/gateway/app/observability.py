"""Middleware-owned observability ingress and Odoo synchronization status.

This module deliberately does not call Prometheus, Alertmanager, Grafana,
Superset, OpenBao, or Odoo.  Prometheus and Alertmanager remain signal
producers; Middleware remains the only component allowed to write Odoo.  The
gateway only validates normalized inputs and records durable Odoo-bound
outbox work for the existing Middleware integration worker.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .capabilities import has_service_permission
from .main import audit, auth, db
from .operations import IntegrationOutbox


router = APIRouter(prefix="/v1/internal/integrations", tags=["Observability integrations"])

OBSERVABILITY_READ = "klyrow.observability.read"
OBSERVABILITY_WRITE = "klyrow.observability.write"
ODOO_TARGET = "ODOO"

FORBIDDEN_LABELS = frozenset(
    {
        "tenant_id",
        "customer_id",
        "organization_id",
        "user_id",
        "email",
        "phone",
        "recipient",
        "sender",
        "message_id",
        "trace_id",
        "request_id",
        "raw_url",
        "query_string",
        "idempotency_key",
        "smtp_username",
    }
)
ALLOWED_LABEL_KEY = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
ALLOWED_LABELS = frozenset(
    {
        "codestra_business",
        "application",
        "alertname",
        "service",
        "environment",
        "server",
        "region",
        "deployment",
        "job",
        "instance",
        "target",
        "state",
        "status",
        "severity",
        "outcome",
    }
)
PROMETHEUS_KPI_REFERENCES = frozenset(
    {
        "klyrow:http_requests:rate5m",
        "klyrow:http_errors:ratio5m",
        "klyrow:mail_events:rate15m",
        "klyrow:provider_queue:sum",
        "klyrow:integration_outbox:sum",
        "klyrow:email_outbox_oldest_seconds:max",
    }
)
KPI_STATUS = frozenset({"observed", "stale", "unavailable"})


class AlertmanagerAlert(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    status: Literal["firing", "resolved"]
    labels: dict[str, str] = Field(default_factory=dict, max_length=40)
    annotations: dict[str, str] = Field(default_factory=dict, max_length=20)
    starts_at: str = Field(alias="startsAt", min_length=1, max_length=80)
    ends_at: str = Field(alias="endsAt", default="", max_length=80)
    generator_url: str = Field(alias="generatorURL", default="", max_length=2000)
    fingerprint: str = Field(min_length=8, max_length=200)


class AlertmanagerEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    receiver: str = Field(default="", max_length=200)
    status: Literal["firing", "resolved"] = "firing"
    alerts: list[AlertmanagerAlert] = Field(min_length=1, max_length=100)
    group_key: str = Field(alias="groupKey", default="", max_length=500)
    external_url: str = Field(alias="externalURL", default="", max_length=2000)


class KpiSnapshotIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str = Field(min_length=8, max_length=200)
    kpi_key: str = Field(min_length=3, max_length=160)
    query_ref: str = Field(min_length=3, max_length=200)
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(default="ratio", min_length=1, max_length=40)
    observed_at: datetime
    window_start: datetime | None = None
    window_end: datetime | None = None
    service: str = Field(min_length=1, max_length=120)
    environment: str = Field(min_length=1, max_length=80)
    labels: dict[str, str] = Field(default_factory=dict, max_length=40)
    status: str = Field(default="observed", max_length=20)

    @field_validator("query_ref")
    @classmethod
    def vetted_query_reference(cls, value: str) -> str:
        if value not in PROMETHEUS_KPI_REFERENCES:
            raise ValueError("unapproved_prometheus_query_reference")
        return value

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in KPI_STATUS:
            raise ValueError("invalid_kpi_status")
        return value


class OdooReconcileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scopes: list[str] = Field(default_factory=lambda: ["alerts", "kpis"], min_length=1, max_length=10)

    @field_validator("scopes")
    @classmethod
    def valid_scopes(cls, value: list[str]) -> list[str]:
        allowed = {"alerts", "kpis", "usage", "deliverability", "billing"}
        normalized = sorted(set(value))
        if not set(normalized) <= allowed:
            raise ValueError("invalid_odoo_reconcile_scope")
        return normalized


def _require_observability(permission: str):
    def dependency(ctx: dict[str, Any] = Depends(auth)) -> dict[str, Any]:
        if not has_service_permission(ctx, permission):
            raise HTTPException(403, "observability_service_scope_required")
        return ctx

    dependency.__name__ = "require_observability_" + permission.rsplit(".", 1)[-1]
    return dependency


require_observability_read = _require_observability(OBSERVABILITY_READ)
require_observability_write = _require_observability(OBSERVABILITY_WRITE)


def _normalize_labels(labels: dict[str, str]) -> dict[str, str]:
    if len(labels) > 40:
        raise HTTPException(422, "observability_label_limit_exceeded")
    normalized: dict[str, str] = {}
    for raw_key, raw_value in labels.items():
        key = str(raw_key).strip()
        if key.lower() in FORBIDDEN_LABELS:
            raise HTTPException(422, "forbidden_observability_label")
        if key not in ALLOWED_LABELS or not ALLOWED_LABEL_KEY.fullmatch(key):
            raise HTTPException(422, "unapproved_observability_label")
        value = str(raw_value)
        if len(value) > 200:
            raise HTTPException(422, "observability_label_value_too_long")
        normalized[key] = value
    return dict(sorted(normalized.items()))


def _normal_time(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(422, "invalid_observability_timestamp") from exc
    if parsed.tzinfo is None:
        raise HTTPException(422, "observability_timestamp_requires_timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def _safe_annotations(annotations: dict[str, str]) -> dict[str, str]:
    allowed = {"summary", "description", "runbook_url", "dashboard_url"}
    result: dict[str, str] = {}
    for key in allowed:
        value = annotations.get(key)
        if value is not None:
            result[key] = str(value)[:4000]
    return result


def _payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _enqueue_odoo(
    session: Session,
    context: dict[str, Any],
    *,
    event_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
    idempotency_key: str,
) -> tuple[IntegrationOutbox, bool]:
    """Insert one Odoo-bound operation using the existing durable outbox.

    The savepoint handles two Middleware replicas submitting the same event at
    the same time.  The unique outbox key remains the source of truth; callers
    never blindly create a second operation after a unique-key race.
    """

    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True, default=str)
    prior = session.scalar(
        select(IntegrationOutbox).where(
            IntegrationOutbox.tenant_id == context["tenant"],
            IntegrationOutbox.target == ODOO_TARGET,
            IntegrationOutbox.idempotency_key == idempotency_key,
        )
    )
    if prior is not None:
        if prior.payload_json != payload_json:
            raise HTTPException(409, "observability_idempotency_conflict")
        return prior, True

    item = IntegrationOutbox(
        id=str(uuid.uuid4()),
        tenant_id=context["tenant"],
        target=ODOO_TARGET,
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload_json=payload_json,
        idempotency_key=idempotency_key,
    )
    try:
        with session.begin_nested():
            session.add(item)
            session.flush()
    except IntegrityError:
        prior = session.scalar(
            select(IntegrationOutbox).where(
                IntegrationOutbox.tenant_id == context["tenant"],
                IntegrationOutbox.target == ODOO_TARGET,
                IntegrationOutbox.idempotency_key == idempotency_key,
            )
        )
        if prior is None:
            raise
        if prior.payload_json != payload_json:
            raise HTTPException(409, "observability_idempotency_conflict")
        return prior, True
    return item, False


def _alert_payload(alert: AlertmanagerAlert, correlation_id: str) -> dict[str, Any]:
    labels = _normalize_labels(alert.labels)
    severity = labels.get("severity", "warning")
    if severity not in {"info", "warning", "critical"}:
        raise HTTPException(422, "invalid_alert_severity")
    starts_at = _normal_time(alert.starts_at)
    ends_at = _normal_time(alert.ends_at) if alert.ends_at else None
    return {
        "schema_version": "1.0",
        "source_system": "alertmanager",
        "event_type": "klyrow.observability.alert.v1",
        "record_key": alert.fingerprint,
        "status": alert.status,
        "alert_name": labels.get("alertname", "unknown"),
        "severity": severity,
        "labels": labels,
        "annotations": _safe_annotations(alert.annotations),
        "starts_at": starts_at,
        "ends_at": ends_at,
        "generator_url": alert.generator_url,
        "correlation_id": correlation_id,
        "odoo_model": "kyyow.ops.alert",
        "direct_odoo_database_write": False,
    }


@router.post("/alertmanager/events", status_code=202)
def receive_alertmanager_events(
    body: AlertmanagerEnvelope,
    ctx: dict[str, Any] = Depends(require_observability_write),
    session: Session = Depends(db),
    x_correlation_id: str = Header(default="", alias="X-Correlation-ID", max_length=200),
) -> dict[str, Any]:
    correlation = x_correlation_id.strip() or "alertmanager:" + _payload_hash(body.model_dump())[:32]
    accepted: list[str] = []
    duplicates = 0
    for alert in body.alerts:
        payload = _alert_payload(alert, correlation)
        key = f"observability:alert:{alert.fingerprint}:{alert.status}:{payload['starts_at']}"
        item, duplicate = _enqueue_odoo(
            session,
            ctx,
            event_type="KlyrowObservabilityAlertV1",
            aggregate_id=alert.fingerprint,
            payload=payload,
            idempotency_key=key,
        )
        accepted.append(item.id)
        duplicates += int(duplicate)
    audit(session, ctx, "observability.alertmanager.received")
    session.commit()
    return {
        "accepted": len(accepted) - duplicates,
        "duplicates": duplicates,
        "operations": accepted,
        "target": "middleware-odoo-outbox",
        "direct_odoo_database_write": False,
    }


@router.post("/kpis/snapshots", status_code=202)
def receive_kpi_snapshot(
    body: KpiSnapshotIn,
    ctx: dict[str, Any] = Depends(require_observability_write),
    session: Session = Depends(db),
) -> dict[str, Any]:
    labels = _normalize_labels(body.labels)
    observed_at = body.observed_at.astimezone(timezone.utc).isoformat()
    if body.window_start and body.window_end and body.window_start > body.window_end:
        raise HTTPException(422, "invalid_kpi_window")
    payload = {
        "schema_version": "1.0",
        "source_system": "middleware-prometheus-poller",
        "event_type": "klyrow.observability.kpi_snapshot.v1",
        "record_key": body.snapshot_id,
        "kpi_key": body.kpi_key,
        "query_ref": body.query_ref,
        "value": body.value,
        "unit": body.unit,
        "status": body.status,
        "observed_at": observed_at,
        "window_start": body.window_start.astimezone(timezone.utc).isoformat() if body.window_start else None,
        "window_end": body.window_end.astimezone(timezone.utc).isoformat() if body.window_end else None,
        "service": body.service,
        "environment": body.environment,
        "labels": labels,
        "odoo_model": "kyyow.kpi.snapshot",
        "direct_odoo_database_write": False,
    }
    item, duplicate = _enqueue_odoo(
        session,
        ctx,
        event_type="KlyrowKpiSnapshotV1",
        aggregate_id=body.kpi_key,
        payload=payload,
        idempotency_key=f"observability:kpi:{body.snapshot_id}",
    )
    audit(session, ctx, "observability.kpi_snapshot.received")
    session.commit()
    return {
        "operation_id": item.id,
        "snapshot_id": body.snapshot_id,
        "duplicate": duplicate,
        "state": item.state,
        "target": "middleware-odoo-outbox",
        "direct_odoo_database_write": False,
    }


def _outbox_summary(session: Session) -> dict[str, Any]:
    rows = session.execute(
        select(IntegrationOutbox.state, func.count())
        .where(IntegrationOutbox.target == ODOO_TARGET)
        .group_by(IntegrationOutbox.state)
    ).all()
    counts = {str(state): int(count) for state, count in rows}
    oldest = session.scalar(
        select(IntegrationOutbox.created_at)
        .where(
            IntegrationOutbox.target == ODOO_TARGET,
            IntegrationOutbox.state.in_(("PENDING", "PROCESSING", "RETRY")),
        )
        .order_by(IntegrationOutbox.created_at)
        .limit(1)
    )
    oldest_seconds = 0.0
    if oldest:
        if oldest.tzinfo is None:
            oldest = oldest.replace(tzinfo=timezone.utc)
        oldest_seconds = max(0.0, (datetime.now(timezone.utc) - oldest).total_seconds())
    return {"counts": counts, "oldest_pending_seconds": round(oldest_seconds, 3)}


def _transport_configured() -> bool:
    def configured_file(name: str) -> bool:
        value = os.getenv(name, "").strip()
        if not value:
            return False
        path = os.path.abspath(value)
        if os.getenv("KLYROW_ENV", "development").lower() == "production":
            candidate = os.path.abspath(value)
            if not os.path.isabs(value) or os.path.islink(candidate):
                return False
        return os.path.isfile(path)

    return bool(
        (os.getenv("KLYROW_MIDDLEWARE_URL", "").strip() or os.getenv("KLYROW_EMAIL_EVENT_URL", "").strip())
        and configured_file("KLYROW_MIDDLEWARE_API_KEY_FILE")
        and configured_file("KLYROW_SERVER_A_CA_FILE")
        and configured_file("KLYROW_SERVER_A_CLIENT_CERT_FILE")
        and configured_file("KLYROW_SERVER_A_CLIENT_KEY_FILE")
    )


@router.get("/odoo/health")
def odoo_health(
    ctx: dict[str, Any] = Depends(require_observability_read),
    session: Session = Depends(db),
) -> dict[str, Any]:
    del ctx
    summary = _outbox_summary(session)
    dead_letters = summary["counts"].get("DEAD_LETTER", 0)
    configured = _transport_configured()
    status = "healthy" if configured and dead_letters == 0 else "degraded"
    return {
        "status": status,
        "authority": "middleware",
        "target": "odoo",
        "transport": "private_mtls",
        "configured": configured,
        "direct_odoo_database_write": False,
        **summary,
    }


@router.get("/odoo/checkpoints")
def odoo_checkpoints(
    ctx: dict[str, Any] = Depends(require_observability_read),
    session: Session = Depends(db),
) -> dict[str, Any]:
    del ctx
    rows = session.execute(
        select(
            IntegrationOutbox.event_type,
            IntegrationOutbox.state,
            func.count(),
            func.max(IntegrationOutbox.updated_at),
        )
        .where(IntegrationOutbox.target == ODOO_TARGET)
        .group_by(IntegrationOutbox.event_type, IntegrationOutbox.state)
        .order_by(IntegrationOutbox.event_type, IntegrationOutbox.state)
    ).all()
    return {
        "items": [
            {
                "event_type": event_type,
                "state": state,
                "count": int(count),
                "last_updated_at": updated_at.isoformat() if updated_at else None,
            }
            for event_type, state, count, updated_at in rows
        ],
        "authority": "middleware",
        "direct_odoo_database_write": False,
    }


@router.post("/odoo/reconcile", status_code=202)
def request_odoo_reconcile(
    body: OdooReconcileIn,
    ctx: dict[str, Any] = Depends(require_observability_write),
    session: Session = Depends(db),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=200),
) -> dict[str, Any]:
    payload = {
        "schema_version": "1.0",
        "source_system": "klyrow",
        "event_type": "klyrow.odoo.reconcile.requested.v1",
        "record_key": "odoo-reconcile",
        "scopes": body.scopes,
        "requested_by": ctx["sub"],
        "odoo_model": "kyyow.integration.run",
        "direct_odoo_database_write": False,
    }
    item, duplicate = _enqueue_odoo(
        session,
        ctx,
        event_type="KlyrowOdooReconcileRequestedV1",
        aggregate_id="odoo-reconcile",
        payload=payload,
        idempotency_key=f"observability:odoo-reconcile:{idempotency_key}",
    )
    audit(session, ctx, "observability.odoo_reconcile.requested")
    session.commit()
    return {
        "operation_id": item.id,
        "state": item.state,
        "duplicate": duplicate,
        "target": "middleware-odoo-outbox",
        "direct_odoo_database_write": False,
    }


@router.get("/observability/contract")
def observability_contract(
    ctx: dict[str, Any] = Depends(require_observability_read),
) -> dict[str, Any]:
    del ctx
    return {
        "schema_version": "1.0",
        "service_id": "klyrow-gateway",
        "metrics_path": "/metrics",
        "health_path": "/health/ready",
        "signal_owners": {
            "metrics": "Codestra-Prometheus",
            "alerts": "Codestra-Alertmanager",
            "logs": "Codestra-Loki",
            "traces": "Codestra-Tempo",
            "dashboards": "Codestra-Grafana",
            "analytics": "Superset",
            "secrets": "Codestra-OpenBao",
        },
        "integrations": {
            "middleware": "sole_cross_system_write_boundary",
            "odoo": "receives_summaries_through_middleware_only",
        },
        "forbidden_direct_writers": [
            "Codestra-Prometheus",
            "Codestra-Alertmanager",
            "Codestra-Grafana",
            "Codestra-Loki",
            "Codestra-Tempo",
            "Superset",
            "Codestra-OpenBao",
            "klyrow-gateway",
        ],
        "forbidden_metric_labels": sorted(FORBIDDEN_LABELS),
        "direct_odoo_database_write": False,
    }


__all__ = [
    "AlertmanagerAlert",
    "AlertmanagerEnvelope",
    "KpiSnapshotIn",
    "OdooReconcileIn",
    "router",
]
