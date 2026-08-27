"""Production mail readiness, role inbox, placement, and activation controls."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import dns.reversename
import dns.resolver
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func, or_, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .agent_mailboxes import (
    AgentMailbox,
    CampaignEmailDomain,
    MailboxInboundRoute,
    OutboundSenderAuthorization,
)
from .mail_roles import OUTBOUND_ROLE_ADDRESSES, ROLE_ADDRESSES, role_address_manifest
from .main import (
    AllowedSender,
    Audit,
    Base,
    Domain,
    Event,
    InboundRouteConfig,
    PostalEvent,
    Tenant,
    audit,
    auth,
    db,
    require,
)
from .postal_transport import transport_status
from .provider import (
    DkimKey,
    ProviderDomain,
    ProviderEvent,
    ProviderInbound,
    ProviderMessage,
    TenantMailPolicy,
    TrackingToken,
    domain_dns_evidence,
)
from .tenancy import ScopedApiKey, ServiceAccount


router = APIRouter(prefix="/v1", tags=["Mail operations"])
now = lambda: datetime.now(timezone.utc)


class SeedMailbox(Base):
    __tablename__ = "seed_mailboxes"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_seed_mailbox_tenant_email"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    email: Mapped[str] = mapped_column(String, index=True)
    provider: Mapped[str] = mapped_column(String, default="GMAIL")
    credential_secret_ref: Mapped[str] = mapped_column(String)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PlacementCheck(Base):
    __tablename__ = "placement_checks"
    __table_args__ = (
        UniqueConstraint("seed_mailbox_id", "message_id", name="uq_placement_seed_message"),
    )
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    seed_mailbox_id: Mapped[str] = mapped_column(ForeignKey("seed_mailboxes.id"), index=True)
    message_id: Mapped[str] = mapped_column(String, index=True)
    folder: Mapped[str] = mapped_column(String, index=True)
    opened: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String, default="GMAIL_API")
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RoleProvisionIn(BaseModel):
    tenant_id: str
    domains: list[str] = Field(default_factory=list, max_length=200)
    destination_refs: dict[str, str] = Field(default_factory=dict)
    activate: bool = False


class RouteActivationIn(BaseModel):
    destination_ref: str = Field(min_length=3, max_length=500)
    attestation: str = Field(min_length=10, max_length=500)


class DomainActivationIn(BaseModel):
    enable_sending: bool = True
    enable_inbound: bool = False
    attestation: str = Field(min_length=10, max_length=500)


class CampaignActivationIn(BaseModel):
    enable_sending: bool = True
    enable_receiving: bool = True
    attestation: str = Field(min_length=10, max_length=500)


class EventRetryIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class SeedMailboxIn(BaseModel):
    email: EmailStr
    provider: str = Field(default="GMAIL", pattern="^(GMAIL)$")
    credential_secret_ref: str = Field(pattern=r"^secret://[A-Za-z0-9_.:/-]+$")
    enabled: bool = False

    @field_validator("credential_secret_ref")
    @classmethod
    def validate_secret_reference(cls, value: str) -> str:
        from .gmail_seed import seed_secret_path
        try:
            seed_secret_path(value)
        except RuntimeError as exc:
            raise ValueError("invalid_seed_credential_reference") from exc
        return value


class PlacementCheckIn(BaseModel):
    seed_mailbox_id: str
    message_id: str = Field(min_length=3, max_length=998)
    folder: str = Field(pattern="^(INBOX|SPAM|PROMOTIONS|UPDATES|SOCIAL|FORUMS|TRASH|NOT_FOUND|UNKNOWN)$")
    opened: bool = False
    source: str = Field(default="GMAIL_API", pattern="^(GMAIL_API|IMAP)$")


class PlacementRunIn(BaseModel):
    seed_mailbox_id: str
    message_id: str = Field(min_length=3, max_length=998)
    rfc_message_id: str = Field(min_length=5, max_length=998, pattern=r"^<[^<>\s]+>$")


def ptr_readiness() -> dict:
    outbound_ip = os.getenv("KLYROW_OUTBOUND_IP", "").strip()
    expected = os.getenv("KLYROW_EXPECTED_PTR", "mail.klyrow.com").strip().lower().rstrip(".")
    if not outbound_ip:
        return {"ready": False, "outbound_ip": None, "expected": expected, "actual": [], "error": "outbound_ip_not_configured"}
    try:
        resolver = dns.resolver.Resolver(configure=True)
        resolver.lifetime = 3
        actual = sorted({str(answer).lower().rstrip(".") for answer in resolver.resolve(dns.reversename.from_address(outbound_ip), "PTR")})
    except Exception as exc:
        return {"ready": False, "outbound_ip": outbound_ip, "expected": expected, "actual": [], "error": type(exc).__name__}
    return {"ready": expected in actual, "outbound_ip": outbound_ip, "expected": expected, "actual": actual}


def _count(s: Session, model, *conditions) -> int:
    return int(s.scalar(select(func.count()).select_from(model).where(*conditions)) or 0)


def _check(number: int, name: str, ready: bool, detail: dict, action_url: str) -> dict:
    return {"number": number, "name": name, "status": "PASS" if ready else "BLOCKED", "detail": detail, "action_url": action_url}


def readiness_report(s: Session, tenant_id: Optional[str]) -> dict:
    tenant_condition = [] if tenant_id is None else [Domain.tenant_id == tenant_id]
    verified_domains = list(s.scalars(select(Domain).where(Domain.verified == True, *tenant_condition).order_by(Domain.domain)).all())
    route_condition = [] if tenant_id is None else [InboundRouteConfig.tenant_id == tenant_id]
    routes_total = _count(s, InboundRouteConfig, *route_condition)
    routes_active = _count(s, InboundRouteConfig, *route_condition, InboundRouteConfig.verified == True, InboundRouteConfig.enabled == True)
    event_condition = [] if tenant_id is None else [PostalEvent.tenant_id == tenant_id]
    event_retry = _count(s, PostalEvent, *event_condition, PostalEvent.state == "retry")
    event_dlq = _count(s, PostalEvent, *event_condition, PostalEvent.state == "dlq")
    credential_condition = [] if tenant_id is None else [ScopedApiKey.tenant_id == tenant_id]
    service_condition = [] if tenant_id is None else [ServiceAccount.tenant_id == tenant_id]
    current = now()
    machine_credentials = _count(s, ScopedApiKey, *credential_condition, ScopedApiKey.revoked_at == None,
        or_(ScopedApiKey.expires_at == None, ScopedApiKey.expires_at > current)) + _count(s, ServiceAccount,
        *service_condition, ServiceAccount.revoked_at == None,
        or_(ServiceAccount.expires_at == None, ServiceAccount.expires_at > current))
    message_condition = [] if tenant_id is None else [ProviderMessage.tenant_id == tenant_id]
    live_queued = _count(s, ProviderMessage, *message_condition, ProviderMessage.sandbox == False, ProviderMessage.status.in_(["QUEUED", "DEFERRED", "PROCESSING"]))
    provider_dead = _count(s, ProviderMessage, *message_condition, ProviderMessage.status == "DEAD_LETTER")
    ptr = ptr_readiness()
    campaign_condition = [] if tenant_id is None else [CampaignEmailDomain.tenant_id == tenant_id]
    campaign_total = _count(s, CampaignEmailDomain, *campaign_condition)
    campaign_active = _count(s, CampaignEmailDomain, *campaign_condition, CampaignEmailDomain.status == "active", CampaignEmailDomain.sending_enabled == True)
    policy_condition = [] if tenant_id is None else [TenantMailPolicy.tenant_id == tenant_id]
    tracking_policies = _count(s, TenantMailPolicy, *policy_condition, TenantMailPolicy.tracking_mode != "DISABLED")
    seed_condition = [] if tenant_id is None else [SeedMailbox.tenant_id == tenant_id]
    seed_rows = list(s.scalars(select(SeedMailbox).where(*seed_condition, SeedMailbox.enabled == True)).all())
    from .gmail_seed import load_oauth_credential
    enabled_seeds = 0
    for seed in seed_rows:
        try:load_oauth_credential(seed.credential_secret_ref);enabled_seeds += 1
        except RuntimeError:pass
    token_condition = [] if tenant_id is None else [TrackingToken.tenant_id == tenant_id]
    tracked_seen = _count(s, TrackingToken, *token_condition, TrackingToken.first_seen_at != None)
    expected_roles = len(verified_domains) * len(ROLE_ADDRESSES)
    expected_role_addresses = {local_part + "@" + domain.domain for domain in verified_domains for local_part in ROLE_ADDRESSES}
    configured_roles = _count(s, InboundRouteConfig, *route_condition, InboundRouteConfig.address.in_(expected_role_addresses)) if expected_role_addresses else 0
    active_roles = _count(s, InboundRouteConfig, *route_condition, InboundRouteConfig.address.in_(expected_role_addresses), InboundRouteConfig.verified == True, InboundRouteConfig.enabled == True) if expected_role_addresses else 0
    mailbox_condition = [] if tenant_id is None else [AgentMailbox.tenant_id == tenant_id]
    mailbox_active = _count(s, AgentMailbox, *mailbox_condition, AgentMailbox.mailbox_status == "ACTIVE", AgentMailbox.sending_enabled == True, AgentMailbox.receiving_enabled == True)
    mailbox_total = _count(s, AgentMailbox, *mailbox_condition)
    mailbox_route_condition = [] if tenant_id is None else [MailboxInboundRoute.tenant_id == tenant_id]
    mailbox_sender_condition = [] if tenant_id is None else [OutboundSenderAuthorization.tenant_id == tenant_id]
    active_mailbox_routes = _count(s, MailboxInboundRoute, *mailbox_route_condition, MailboxInboundRoute.enabled == True)
    active_mailbox_senders = _count(s, OutboundSenderAuthorization, *mailbox_sender_condition, OutboundSenderAuthorization.enabled == True)
    transports = {domain.domain: transport_status(domain.domain) for domain in verified_domains}
    transports_ready = bool(transports) and all(item["ready"] for item in transports.values())
    transport_webhooks_ready = bool(transports) and all(item["webhook_ready"] for item in transports.values())
    provider_gate = os.getenv("KLYROW_PROVIDER_LIVE_DELIVERY_ENABLED", "false").lower() == "true"
    deployment = {
        "release_sha": os.getenv("KLYROW_RELEASE_SHA") or None,
        "required_schema_version": os.getenv("KLYROW_REQUIRED_SCHEMA_VERSION") or None,
        "embedded_workers": os.getenv("KLYROW_EMBEDDED_WORKERS", "true").lower() == "true",
        "transport_registry": os.getenv("KLYROW_POSTAL_TRANSPORTS_FILE") or None,
    }
    checks = [
        _check(1, "Inbound routes and shared inboxes", routes_total > 0 and routes_active == routes_total, {"configured": routes_total, "active": routes_active}, "/v1/mail/role-addresses"),
        _check(2, "Delivery event pipeline", event_retry == 0 and event_dlq == 0 and transport_webhooks_ready, {"retry": event_retry, "dead_letter": event_dlq, "transport_signatures_ready": transport_webhooks_ready}, "/v1/admin/mail/events"),
        _check(3, "Machine authentication", machine_credentials > 0, {"active_credentials": machine_credentials}, "/v1/service-accounts"),
        _check(4, "Provider live worker and payload", provider_gate and provider_dead == 0 and transports_ready, {"live_gate": provider_gate, "queued": live_queued, "dead_letter": provider_dead, "transports": transports}, "/v1/internal/email/operations/health"),
        _check(5, "Outbound PTR", ptr["ready"], ptr, "https://console.hetzner.com/"),
        _check(6, "Campaign activation gates", campaign_total > 0 and campaign_active == campaign_total, {"configured": campaign_total, "active": campaign_active}, "/v1/agent-mailboxes"),
        _check(7, "Tracking and placement", tracking_policies > 0 and enabled_seeds > 0, {"tracking_policies": tracking_policies, "observed_tokens": tracked_seen, "enabled_seed_mailboxes": enabled_seeds}, "/v1/mail/tracking/summary"),
        _check(8, "Corporate role addresses", expected_roles > 0 and configured_roles == expected_roles and active_roles == expected_roles, {"domains": len(verified_domains), "expected": expected_roles, "configured": configured_roles, "active": active_roles}, "/v1/mail/role-addresses"),
        _check(9, "Agent mailboxes", mailbox_total > 0 and mailbox_active == mailbox_total and active_mailbox_routes == mailbox_total and active_mailbox_senders == mailbox_total, {"configured": mailbox_total, "active": mailbox_active, "active_routes": active_mailbox_routes, "active_senders": active_mailbox_senders}, "/v1/agent-mailboxes"),
        _check(10, "Canonical deployment", bool(deployment["release_sha"] and deployment["required_schema_version"] and deployment["transport_registry"] and not deployment["embedded_workers"]), deployment, "/version"),
    ]
    return {"status": "READY" if all(item["status"] == "PASS" for item in checks) else "BLOCKED", "tenant_id": tenant_id, "generated_at": now().isoformat(), "checks": checks}


@router.get("/mail/readiness")
def tenant_readiness(ctx=Depends(auth), s: Session = Depends(db)):
    return readiness_report(s, ctx["tenant"])


@router.get("/admin/mail/readiness")
def admin_readiness(tenant_id: Optional[str] = Query(default=None), ctx=Depends(require("platform_admin")), s: Session = Depends(db)):
    if tenant_id and not s.get(Tenant, tenant_id):
        raise HTTPException(404, "tenant_not_found")
    return readiness_report(s, tenant_id)


@router.get("/admin/mail/events")
def admin_mail_events(state: Optional[str] = None, limit: int = 100,
        ctx=Depends(require("platform_admin")), s: Session = Depends(db)):
    if state and state not in {"pending", "retry", "delivered", "dlq"}:
        raise HTTPException(422, "invalid_event_state")
    query = select(PostalEvent)
    if state:
        query = query.where(PostalEvent.state == state)
    rows = s.scalars(query.order_by(PostalEvent.updated_at.desc()).limit(max(1, min(limit, 500)))).all()
    return {"items": [{"id": item.id, "tenant_id": item.tenant_id, "event_type": item.event_type,
        "correlation_id": item.correlation_id, "message_id": item.message_id, "state": item.state,
        "attempts": item.attempts, "last_error": item.last_error, "updated_at": item.updated_at}
        for item in rows]}


@router.post("/admin/mail/events/{event_id}/retry")
def retry_mail_event(event_id: str, payload: EventRetryIn, ctx=Depends(require("platform_admin")), s: Session = Depends(db)):
    item = s.get(PostalEvent, event_id)
    if not item or item.state not in {"retry", "dlq"}:
        raise HTTPException(404, "recoverable_postal_event_not_found")
    item.state = "retry";item.attempts = 0;item.last_error = None;item.updated_at = now()
    audit(s, {**ctx, "tenant": item.tenant_id}, "postal_event.retry_requested:" + payload.reason)
    s.commit()
    return {"id": item.id, "state": item.state, "attempts": item.attempts}


@router.get("/mail/role-addresses")
def role_addresses(ctx=Depends(auth), s: Session = Depends(db)):
    domains = list(s.scalars(select(Domain).where(Domain.tenant_id == ctx["tenant"], Domain.verified == True).order_by(Domain.domain)).all())
    items = []
    for domain in domains:
        for definition in role_address_manifest():
            address = definition["local_part"] + "@" + domain.domain
            route = s.scalar(select(InboundRouteConfig).where(InboundRouteConfig.tenant_id == ctx["tenant"], InboundRouteConfig.address == address))
            sender = s.scalar(select(AllowedSender).where(AllowedSender.tenant_id == ctx["tenant"], AllowedSender.address == address))
            items.append({"address": address, **definition, "route_verified": bool(route and route.verified), "receiving_enabled": bool(route and route.enabled), "sending_enabled": bool(sender and sender.enabled)})
    return {"items": items, "domains": len(domains), "expected_per_domain": len(ROLE_ADDRESSES)}


@router.post("/admin/mail/role-addresses/provision")
def provision_role_addresses(payload: RoleProvisionIn, ctx=Depends(require("platform_admin")), s: Session = Depends(db)):
    if not s.get(Tenant, payload.tenant_id):
        raise HTTPException(404, "tenant_not_found")
    query = select(Domain).where(Domain.tenant_id == payload.tenant_id, Domain.verified == True)
    if payload.domains:
        normalized = {item.lower().rstrip(".") for item in payload.domains}
        query = query.where(Domain.domain.in_(normalized))
    domains = list(s.scalars(query.order_by(Domain.domain)).all())
    if not domains:
        raise HTTPException(409, "verified_domain_required")
    required_kinds = {definition["destination_kind"] for definition in ROLE_ADDRESSES.values()}
    if payload.activate and not required_kinds.issubset(payload.destination_refs):
        raise HTTPException(422, {"code": "destination_attestation_required", "missing": sorted(required_kinds - set(payload.destination_refs))})
    created_routes = 0
    created_senders = 0
    for domain in domains:
        for local_part, definition in ROLE_ADDRESSES.items():
            address = local_part + "@" + domain.domain
            destination_ref = payload.destination_refs.get(definition["destination_kind"])
            route = s.scalar(select(InboundRouteConfig).where(InboundRouteConfig.tenant_id == payload.tenant_id, InboundRouteConfig.address == address))
            if not route:
                route = InboundRouteConfig(id=str(uuid.uuid4()), tenant_id=payload.tenant_id, address=address, destination_kind=definition["destination_kind"], destination_ref=destination_ref, verified=bool(destination_ref), enabled=bool(payload.activate and destination_ref))
                s.add(route);created_routes += 1
            elif destination_ref:
                route.destination_kind = definition["destination_kind"];route.destination_ref = destination_ref;route.verified = True
                if payload.activate:route.enabled = True
            sender = s.scalar(select(AllowedSender).where(AllowedSender.tenant_id == payload.tenant_id, AllowedSender.address == address))
            if not sender:
                sender = AllowedSender(id=str(uuid.uuid4()), tenant_id=payload.tenant_id, address=address, role=local_part, enabled=bool(payload.activate and local_part in OUTBOUND_ROLE_ADDRESSES))
                s.add(sender);created_senders += 1
            elif payload.activate:
                sender.enabled = local_part in OUTBOUND_ROLE_ADDRESSES
    audit(s, {**ctx, "tenant": payload.tenant_id}, "mail.role_addresses.provisioned")
    s.commit()
    return {"domains": [item.domain for item in domains], "addresses": len(domains) * len(ROLE_ADDRESSES), "routes_created": created_routes, "senders_created": created_senders, "activated": payload.activate}


@router.post("/admin/mail/inbound-routes/{route_id}/activate")
def activate_inbound_route(route_id: str, payload: RouteActivationIn, ctx=Depends(require("platform_admin")), s: Session = Depends(db)):
    route = s.get(InboundRouteConfig, route_id)
    if not route:
        raise HTTPException(404, "inbound_route_not_found")
    if payload.attestation != "ACTIVATE " + route.address:
        raise HTTPException(409, "activation_attestation_mismatch")
    route.destination_ref = payload.destination_ref;route.verified = True;route.enabled = True
    audit(s, {**ctx, "tenant": route.tenant_id}, "mail.inbound_route.activated")
    s.commit()
    return {"id": route.id, "address": route.address, "verified": route.verified, "enabled": route.enabled}


@router.post("/admin/mail/inbound-routes/{route_id}/deactivate")
def deactivate_inbound_route(route_id: str, ctx=Depends(require("platform_admin")), s: Session = Depends(db)):
    route = s.get(InboundRouteConfig, route_id)
    if not route:
        raise HTTPException(404, "inbound_route_not_found")
    route.enabled = False
    audit(s, {**ctx, "tenant": route.tenant_id}, "mail.inbound_route.deactivated")
    s.commit()
    return {"id": route.id, "address": route.address, "enabled": False}


@router.post("/admin/mail/provider-domains/{domain_id}/activate")
def activate_provider_domain(domain_id: str, payload: DomainActivationIn, ctx=Depends(require("platform_admin")), s: Session = Depends(db)):
    domain = s.get(ProviderDomain, domain_id)
    if not domain:
        raise HTTPException(404, "provider_domain_not_found")
    if payload.attestation != "ACTIVATE " + domain.domain:
        raise HTTPException(409, "activation_attestation_mismatch")
    if not ptr_readiness()["ready"]:
        raise HTTPException(409, "outbound_ptr_not_ready")
    selected_transport = transport_status(domain.domain)
    if not selected_transport["ready"] or not selected_transport["webhook_ready"]:
        raise HTTPException(409, "postal_transport_not_ready")
    prior_inbound = domain.inbound_enabled
    domain.inbound_enabled = payload.enable_inbound
    active_key = s.scalar(select(DkimKey).where(DkimKey.domain_id == domain.id, DkimKey.status == "ACTIVE").order_by(DkimKey.version.desc()).limit(1))
    evidence = domain_dns_evidence(domain, active_key)
    if not evidence["verified"]:
        domain.inbound_enabled = prior_inbound
        raise HTTPException(409, {"code": "domain_dns_not_ready", "evidence": evidence})
    domain.sending_enabled = payload.enable_sending
    domain.inbound_enabled = payload.enable_inbound
    domain.status = "SENDING_ENABLED" if payload.enable_sending else "VERIFIED"
    s.add(Audit(id=str(uuid.uuid4()), tenant_id=domain.tenant_id, actor=ctx["sub"], action="provider_domain.activated"))
    s.commit()
    return {"id": domain.id, "domain": domain.domain, "status": domain.status, "sending_enabled": domain.sending_enabled, "inbound_enabled": domain.inbound_enabled, "dns": evidence}


@router.post("/admin/mail/campaign-domains/{mapping_id}/activate")
def activate_campaign_domain(mapping_id: str, payload: CampaignActivationIn, ctx=Depends(require("platform_admin")), s: Session = Depends(db)):
    mapping = s.get(CampaignEmailDomain, mapping_id)
    if not mapping:
        raise HTTPException(404, "campaign_domain_mapping_not_found")
    if payload.attestation != "ACTIVATE " + mapping.campaign_id:
        raise HTTPException(409, "activation_attestation_mismatch")
    provider_domain = s.scalar(select(ProviderDomain).where(ProviderDomain.tenant_id == mapping.tenant_id, ProviderDomain.domain == mapping.primary_domain))
    if not provider_domain or (payload.enable_sending and not provider_domain.sending_enabled) or (payload.enable_receiving and not provider_domain.inbound_enabled):
        raise HTTPException(409, "provider_domain_activation_required")
    if not mapping.sender_domain_verified or not mapping.inbound_domain_verified:
        raise HTTPException(409, "campaign_domain_verification_required")
    mapping.sending_enabled = payload.enable_sending;mapping.receiving_enabled = payload.enable_receiving
    mapping.status = "active";mapping.approved_by = ctx["sub"];mapping.approved_at = now();mapping.updated_at = now()
    audit(s, {**ctx, "tenant": mapping.tenant_id}, "campaign_domain.activated")
    s.commit()
    return {"id": mapping.id, "campaign_id": mapping.campaign_id, "domain": mapping.primary_domain, "status": mapping.status, "sending_enabled": mapping.sending_enabled, "receiving_enabled": mapping.receiving_enabled}


@router.get("/mail/tracking/summary")
def tracking_summary(ctx=Depends(auth), s: Session = Depends(db)):
    total = _count(s, TrackingToken, TrackingToken.tenant_id == ctx["tenant"])
    opens = _count(s, TrackingToken, TrackingToken.tenant_id == ctx["tenant"], TrackingToken.kind == "OPEN", TrackingToken.first_seen_at != None)
    clicks = _count(s, TrackingToken, TrackingToken.tenant_id == ctx["tenant"], TrackingToken.kind == "CLICK", TrackingToken.first_seen_at != None)
    placements = list(s.scalars(select(PlacementCheck).where(PlacementCheck.tenant_id == ctx["tenant"]).order_by(PlacementCheck.checked_at.desc()).limit(100)).all())
    folders: dict[str, int] = {}
    for item in placements:
        folders[item.folder] = folders.get(item.folder, 0) + 1
    postal_opens = _count(s, Event, Event.tenant_id == ctx["tenant"], Event.kind.in_(["message.opened", "klyrow.email.opened", "klyrow.message.opened"])) + _count(s, ProviderEvent, ProviderEvent.tenant_id == ctx["tenant"], ProviderEvent.kind == "message.opened")
    postal_clicks = _count(s, Event, Event.tenant_id == ctx["tenant"], Event.kind.in_(["message.clicked", "klyrow.email.clicked", "klyrow.message.clicked"])) + _count(s, ProviderEvent, ProviderEvent.tenant_id == ctx["tenant"], ProviderEvent.kind == "message.clicked")
    return {"tokens": total, "unique_opens": opens + postal_opens, "unique_clicks": clicks + postal_clicks, "placement_checks": len(placements), "folders": folders}


@router.post("/mail/seed-mailboxes", status_code=201)
def create_seed_mailbox(payload: SeedMailboxIn, ctx=Depends(auth), s: Session = Depends(db)):
    if ctx.get("role") not in {"platform_admin", "tenant_admin", "OWNER", "ADMIN"}:
        raise HTTPException(403, "tenant_management_denied")
    email = str(payload.email).lower()
    if payload.enabled:
        from .gmail_seed import load_oauth_credential
        try:
            load_oauth_credential(payload.credential_secret_ref)
        except RuntimeError as exc:
            raise HTTPException(409, "seed_oauth_credential_not_ready") from exc
    if s.scalar(select(SeedMailbox).where(SeedMailbox.tenant_id == ctx["tenant"], SeedMailbox.email == email)):
        raise HTTPException(409, "seed_mailbox_exists")
    item = SeedMailbox(id=str(uuid.uuid4()), tenant_id=ctx["tenant"], email=email, provider=payload.provider, credential_secret_ref=payload.credential_secret_ref, enabled=payload.enabled)
    s.add(item);audit(s, ctx, "mail.seed_mailbox.created");s.commit()
    return {"id": item.id, "email": item.email, "provider": item.provider, "enabled": item.enabled, "credential_configured": True}


@router.get("/mail/seed-mailboxes")
def seed_mailboxes(ctx=Depends(auth), s: Session = Depends(db)):
    rows = s.scalars(select(SeedMailbox).where(SeedMailbox.tenant_id == ctx["tenant"]).order_by(SeedMailbox.created_at)).all()
    from .gmail_seed import seed_secret_path
    result = []
    for item in rows:
        try:configured = seed_secret_path(item.credential_secret_ref).is_file() and seed_secret_path(item.credential_secret_ref).stat().st_size > 0
        except (OSError, RuntimeError):configured = False
        result.append({"id": item.id, "email": item.email, "provider": item.provider, "enabled": item.enabled,
            "credential_configured": configured, "created_at": item.created_at})
    return result


@router.post("/mail/placement-checks", status_code=201)
def record_placement(payload: PlacementCheckIn, ctx=Depends(auth), s: Session = Depends(db)):
    seed = s.scalar(select(SeedMailbox).where(SeedMailbox.id == payload.seed_mailbox_id, SeedMailbox.tenant_id == ctx["tenant"], SeedMailbox.enabled == True))
    if not seed:
        raise HTTPException(404, "enabled_seed_mailbox_not_found")
    item = s.scalar(select(PlacementCheck).where(PlacementCheck.seed_mailbox_id == seed.id, PlacementCheck.message_id == payload.message_id))
    if not item:
        item = PlacementCheck(id=str(uuid.uuid4()), tenant_id=ctx["tenant"], seed_mailbox_id=seed.id, message_id=payload.message_id, folder=payload.folder, opened=payload.opened, source=payload.source)
        s.add(item)
    else:
        item.folder = payload.folder;item.opened = payload.opened;item.source = payload.source;item.checked_at = now()
    audit(s, ctx, "mail.placement.recorded");s.commit()
    return {"id": item.id, "message_id": item.message_id, "folder": item.folder, "opened": item.opened, "source": item.source, "checked_at": item.checked_at}


@router.post("/mail/placement-checks/run", status_code=201)
async def run_gmail_placement(payload: PlacementRunIn, ctx=Depends(auth), s: Session = Depends(db)):
    if ctx.get("role") not in {"platform_admin", "tenant_admin", "OWNER", "ADMIN"} and not ctx.get("service"):
        raise HTTPException(403, "mail_placement_permission_denied")
    seed = s.scalar(select(SeedMailbox).where(SeedMailbox.id == payload.seed_mailbox_id,
        SeedMailbox.tenant_id == ctx["tenant"], SeedMailbox.enabled == True, SeedMailbox.provider == "GMAIL"))
    if not seed:
        raise HTTPException(404, "enabled_gmail_seed_mailbox_not_found")
    from .gmail_seed import check_gmail_placement
    try:
        result = await check_gmail_placement(seed.credential_secret_ref, payload.rfc_message_id)
    except Exception as exc:
        raise HTTPException(503, "gmail_placement_check_failed") from exc
    item = s.scalar(select(PlacementCheck).where(PlacementCheck.seed_mailbox_id == seed.id,
        PlacementCheck.message_id == payload.message_id))
    if not item:
        item = PlacementCheck(id=str(uuid.uuid4()), tenant_id=ctx["tenant"], seed_mailbox_id=seed.id,
            message_id=payload.message_id, folder=result["folder"], opened=result["opened"], source="GMAIL_API")
        s.add(item)
    else:
        item.folder = result["folder"];item.opened = result["opened"];item.source = "GMAIL_API";item.checked_at = now()
    audit(s, ctx, "mail.placement.gmail_checked");s.commit()
    return {"id": item.id, "message_id": item.message_id, "folder": item.folder,
        "opened": item.opened, "source": item.source, "provider_message_id": result["provider_message_id"],
        "checked_at": item.checked_at}
