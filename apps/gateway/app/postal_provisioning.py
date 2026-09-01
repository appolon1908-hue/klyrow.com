"""Durable tenant-to-Postal provisioning and tenant-scoped delivery credentials."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import DateTime, Integer, String, Text, or_, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .auth_bff import BrowserSession, browser_context, csrf_guard
from .main import (
    Base,
    DB,
    EmailOutbox,
    Event,
    Message,
    ProductionCanaryGate,
    SAFE_MODE,
    SECRET,
    Tenant,
    User,
    campaign_execution_mode,
    campaign_worker_payload_allowed,
    canary_configuration,
    canary_gate_key,
    canary_payload_allowed,
    db,
    set_core_message_status,
)
from .tenancy_onboarding import resolve_identity_context

router = APIRouter(tags=["Postal provisioning"])
READY = "READY"
CLAIMABLE = {"PENDING", "RETRYABLE_FAILURE"}
MAX_ATTEMPTS = 8
now = lambda: datetime.now(timezone.utc)


class PostalTenantMapping(Base):
    __tablename__ = "postal_tenant_mappings"
    tenant_id: Mapped[str] = mapped_column(String, primary_key=True)
    state: Mapped[str] = mapped_column(String, default="PENDING", index=True)
    provider_organization_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    provider_organization_permalink: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    provider_server_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    provider_server_permalink: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    provider_mode: Mapped[str] = mapped_column(String, default="Development")
    api_key_ciphertext: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_key_fingerprint: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PostalProvisioningOutbox(Base):
    __tablename__ = "postal_provisioning_outbox"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True)
    state: Mapped[str] = mapped_column(String, default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    lease_owner: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


def _provider_key() -> bytes:
    path = os.getenv("KLYROW_PROVIDER_CREDENTIAL_KEY_FILE", "").strip()
    if path:
        try:
            material = Path(path).read_bytes().strip()
        except OSError as exc:
            raise RuntimeError("provider credential key unavailable") from exc
        if len(material) < 32:
            raise RuntimeError("provider credential key too short")
        return hashlib.sha256(material).digest()
    if os.getenv("KLYROW_ENV", "development").lower() == "production":
        raise RuntimeError("provider credential key file required in production")
    return hashlib.sha256(("klyrow-provider:" + SECRET).encode()).digest()


def encrypt_provider_secret(value: str) -> str:
    nonce = secrets.token_bytes(12)
    body = nonce + AESGCM(_provider_key()).encrypt(nonce, value.encode(), b"klyrow-postal-tenant-v1")
    return __import__("base64").urlsafe_b64encode(body).decode()


def decrypt_provider_secret(value: str) -> str:
    body = __import__("base64").urlsafe_b64decode(value.encode())
    return AESGCM(_provider_key()).decrypt(body[:12], body[12:], b"klyrow-postal-tenant-v1").decode()


def credential_fingerprint(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()[:20]


def _management_required(ctx: dict) -> None:
    if ctx.get("role") not in {"OWNER", "ADMIN"}:
        raise HTTPException(403, "tenant_management_denied")


def enqueue_postal_provisioning(s: Session, tenant_id: str) -> PostalProvisioningOutbox:
    tenant = s.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404, "tenant_not_found")
    mapping = s.get(PostalTenantMapping, tenant_id)
    if mapping and mapping.state == READY:
        job = s.scalar(select(PostalProvisioningOutbox).where(PostalProvisioningOutbox.tenant_id == tenant_id).order_by(PostalProvisioningOutbox.created_at.desc()))
        if job:
            return job
    if not mapping:
        mapping = PostalTenantMapping(tenant_id=tenant_id, state="PENDING", provider_mode="Development")
        s.add(mapping)
    key = f"postal-tenant:{tenant_id}:v1"
    job = s.scalar(select(PostalProvisioningOutbox).where(PostalProvisioningOutbox.idempotency_key == key))
    if not job:
        job = PostalProvisioningOutbox(id=str(uuid.uuid4()), tenant_id=tenant_id, idempotency_key=key, state="PENDING", available_at=now())
        s.add(job)
    s.commit()
    return job


def resolve_identity_context_with_provisioning(s: Session, claims: dict):
    identity, user, membership = resolve_identity_context(s, claims)
    enqueue_postal_provisioning(s, membership.tenant_id)
    return identity, user, membership


def _bridge_token() -> str:
    path = os.getenv("KLYROW_POSTAL_PROVISIONER_TOKEN_FILE", "").strip()
    if not path:
        raise RuntimeError("postal provisioner token file required")
    try:
        token = Path(path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError("postal provisioner token unavailable") from exc
    if len(token) < 32:
        raise RuntimeError("postal provisioner token too short")
    return token


async def _call_bridge(tenant: Tenant) -> dict:
    base = os.getenv("KLYROW_POSTAL_PROVISIONER_URL", "http://postal-provisioner:9090").rstrip("/")
    headers = {"Authorization": "Bearer " + _bridge_token(), "Content-Type": "application/json"}
    payload = {"tenant_id": tenant.id, "tenant_name": tenant.name, "send_limit": max(100, min(int(tenant.quota or 1000), 10000))}
    async with httpx.AsyncClient(timeout=15, trust_env=False, follow_redirects=False) as client:
        response = await client.post(base + "/v1/provision", headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
    required = ("organization_id", "server_id", "api_key")
    if any(not str(result.get(key) or "").strip() for key in required):
        raise RuntimeError("postal provisioner returned incomplete mapping")
    if str(result.get("mode") or "") != "Development":
        raise RuntimeError("postal provisioner must create development-mode servers")
    return result


def _recover_expired_leases(s: Session) -> None:
    current = now()
    rows = s.scalars(select(PostalProvisioningOutbox).where(PostalProvisioningOutbox.state == "RUNNING", PostalProvisioningOutbox.lease_expires_at < current)).all()
    for row in rows:
        row.state = "BLOCKED" if row.attempts >= MAX_ATTEMPTS else "RETRYABLE_FAILURE"
        row.available_at = current + timedelta(seconds=min(900, 2 ** max(row.attempts, 1)))
        row.lease_owner = None
        row.lease_expires_at = None
        row.last_error = "lease_expired"
        mapping = s.get(PostalTenantMapping, row.tenant_id)
        if mapping:
            mapping.state = row.state
            mapping.last_error = row.last_error
            mapping.updated_at = current
    s.commit()


async def provisioning_tick() -> int:
    worker_id = os.getenv("HOSTNAME", "provisioning-worker") + ":" + str(os.getpid())
    snapshot: Optional[tuple[str, str]] = None
    with DB() as s:
        _recover_expired_leases(s)
        current = now()
        item = s.scalar(
            select(PostalProvisioningOutbox)
            .where(PostalProvisioningOutbox.state.in_(CLAIMABLE), PostalProvisioningOutbox.available_at <= current)
            .order_by(PostalProvisioningOutbox.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not item:
            return 0
        item.state = "RUNNING"
        item.attempts += 1
        item.lease_owner = worker_id
        item.lease_expires_at = current + timedelta(seconds=60)
        item.updated_at = current
        mapping = s.get(PostalTenantMapping, item.tenant_id) or PostalTenantMapping(tenant_id=item.tenant_id)
        mapping.state = "RUNNING"
        mapping.last_error = None
        mapping.updated_at = current
        s.add(mapping)
        snapshot = (item.id, item.tenant_id)
        s.commit()
    try:
        with DB() as s:
            tenant = s.get(Tenant, snapshot[1])
            if not tenant or not tenant.enabled:
                raise RuntimeError("tenant unavailable for provisioning")
            tenant_snapshot = Tenant(id=tenant.id, name=tenant.name, quota=tenant.quota, enabled=tenant.enabled)
        result = await _call_bridge(tenant_snapshot)
        with DB() as s:
            item = s.get(PostalProvisioningOutbox, snapshot[0])
            mapping = s.get(PostalTenantMapping, snapshot[1])
            if not item or not mapping or item.state != "RUNNING":
                return 0
            raw_key = str(result["api_key"])
            mapping.state = READY
            mapping.provider_organization_id = str(result["organization_id"])
            mapping.provider_organization_permalink = str(result.get("organization_permalink") or result["organization_id"])
            mapping.provider_server_id = str(result["server_id"])
            mapping.provider_server_permalink = str(result.get("server_permalink") or result["server_id"])
            mapping.provider_mode = "Development"
            mapping.api_key_ciphertext = encrypt_provider_secret(raw_key)
            mapping.api_key_fingerprint = credential_fingerprint(raw_key)
            mapping.last_error = None
            mapping.updated_at = now()
            item.state = READY
            item.last_error = None
            item.lease_owner = None
            item.lease_expires_at = None
            item.completed_at = now()
            item.updated_at = now()
            s.commit()
        return 1
    except Exception as exc:
        with DB() as s:
            item = s.get(PostalProvisioningOutbox, snapshot[0]) if snapshot else None
            if item:
                blocked = item.attempts >= MAX_ATTEMPTS or isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {400, 401, 403, 409, 422}
                item.state = "BLOCKED" if blocked else "RETRYABLE_FAILURE"
                item.last_error = type(exc).__name__
                item.available_at = now() + timedelta(seconds=min(900, 2 ** max(item.attempts, 1)))
                item.lease_owner = None
                item.lease_expires_at = None
                item.updated_at = now()
                mapping = s.get(PostalTenantMapping, item.tenant_id)
                if mapping:
                    mapping.state = item.state
                    mapping.last_error = item.last_error
                    mapping.updated_at = now()
                s.commit()
        return 0


def tenant_postal_api_key(s: Session, tenant_id: str) -> str:
    mapping = s.get(PostalTenantMapping, tenant_id)
    if mapping and mapping.state == READY and mapping.api_key_ciphertext:
        return decrypt_provider_secret(mapping.api_key_ciphertext)
    allow_legacy = os.getenv("KLYROW_ALLOW_LEGACY_GLOBAL_POSTAL_KEY", "false").lower() == "true"
    if allow_legacy:
        path = os.getenv("KLYROW_POSTAL_API_KEY_FILE", "").strip()
        if path:
            key = Path(path).read_text(encoding="utf-8").strip()
            if key:
                return key
    raise RuntimeError("postal tenant is not provisioned")


async def tenant_email_outbox_loop() -> None:
    """Delegate to the sole hardened delivery implementation.

    The import is intentionally deferred because the canonical worker imports
    ``tenant_postal_api_key`` from this module. Keeping one implementation
    prevents the web and service worker entrypoints from diverging on lease,
    cancellation, priority, and ambiguous provider-outcome behavior.
    """

    from .tenant_postal_delivery import tenant_email_outbox_loop as hardened_loop

    await hardened_loop()


def _mapping_status(s: Session, tenant_id: str) -> dict:
    mapping = s.get(PostalTenantMapping, tenant_id)
    job = s.scalar(select(PostalProvisioningOutbox).where(PostalProvisioningOutbox.tenant_id == tenant_id).order_by(PostalProvisioningOutbox.created_at.desc()))
    return {
        "tenant_id": tenant_id,
        "state": mapping.state if mapping else "NOT_REQUESTED",
        "provider_mode": mapping.provider_mode if mapping else None,
        "organization": mapping.provider_organization_permalink if mapping else None,
        "server": mapping.provider_server_permalink if mapping else None,
        "credential_fingerprint": mapping.api_key_fingerprint if mapping else None,
        "last_error": mapping.last_error if mapping else None,
        "attempts": job.attempts if job else 0,
        "updated_at": mapping.updated_at if mapping else None,
    }


@router.get("/app/api/provisioning/postal")
def provisioning_status(ctx: dict = Depends(browser_context), s: Session = Depends(db)):
    return _mapping_status(s, ctx["tenant"])


@router.post("/app/api/provisioning/postal", status_code=202)
def request_provisioning(ctx: dict = Depends(browser_context), _session: BrowserSession = Depends(csrf_guard), s: Session = Depends(db)):
    _management_required(ctx)
    enqueue_postal_provisioning(s, ctx["tenant"])
    return _mapping_status(s, ctx["tenant"])


@router.post("/app/api/provisioning/postal/retry", status_code=202)
def retry_provisioning(ctx: dict = Depends(browser_context), _session: BrowserSession = Depends(csrf_guard), s: Session = Depends(db)):
    _management_required(ctx)
    job = s.scalar(select(PostalProvisioningOutbox).where(PostalProvisioningOutbox.tenant_id == ctx["tenant"]).order_by(PostalProvisioningOutbox.created_at.desc()))
    if not job:
        enqueue_postal_provisioning(s, ctx["tenant"])
    else:
        job.state = "PENDING"; job.attempts = 0; job.available_at = now(); job.last_error = None; job.lease_owner = None; job.lease_expires_at = None; job.updated_at = now()
        mapping = s.get(PostalTenantMapping, ctx["tenant"])
        if mapping: mapping.state = "PENDING"; mapping.last_error = None; mapping.updated_at = now()
        s.commit()
    return _mapping_status(s, ctx["tenant"])


@router.get("/app/api/admin/provisioning/postal")
def admin_provisioning(ctx: dict = Depends(browser_context), s: Session = Depends(db)):
    user = s.get(User, ctx["sub"])
    if not user or user.role != "platform_admin":
        raise HTTPException(403, "platform_admin_required")
    rows = s.scalars(select(PostalTenantMapping).where(PostalTenantMapping.state != READY).order_by(PostalTenantMapping.updated_at.desc()).limit(100)).all()
    return [_mapping_status(s, row.tenant_id) for row in rows]


@router.post("/app/api/admin/provisioning/postal/{tenant_id}/retry", status_code=202)
def admin_retry_provisioning(tenant_id: str, ctx: dict = Depends(browser_context), _session: BrowserSession = Depends(csrf_guard), s: Session = Depends(db)):
    user = s.get(User, ctx["sub"])
    if not user or user.role != "platform_admin":
        raise HTTPException(403, "platform_admin_required")
    job = s.scalar(select(PostalProvisioningOutbox).where(PostalProvisioningOutbox.tenant_id == tenant_id).order_by(PostalProvisioningOutbox.created_at.desc()))
    if not job:
        enqueue_postal_provisioning(s, tenant_id)
    else:
        job.state = "PENDING"; job.attempts = 0; job.available_at = now(); job.last_error = None; job.lease_owner = None; job.lease_expires_at = None; job.updated_at = now()
        mapping = s.get(PostalTenantMapping, tenant_id)
        if mapping: mapping.state = "PENDING"; mapping.last_error = None; mapping.updated_at = now()
        s.commit()
    return _mapping_status(s, tenant_id)
