import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.gateway.app import auth_bff
from apps.gateway.app.auth_bff import BrowserSession
from apps.gateway.app.main import AUTH_WEB_DIST, Base, DB, Message, Tenant, User, engine, sha
from apps.gateway.app.platform import app
from apps.gateway.app.saas import Onboarding
from apps.gateway.app.tenancy import OidcIdentity, Organization, TenantMember
from apps.gateway.app.tenancy_onboarding import IdentityProfileRecord, resolve_identity_context

issuer="https://auth.codestra.co/realms/codestra"
client=TestClient(app,base_url="https://app.klyrow.test")


def setup_module():
    os.environ["KLYROW_OIDC_ISSUER"]=issuer
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)


def test_first_login_creates_canonical_identity_workspace_and_profile():
    with DB() as s:
        identity,user,membership=resolve_identity_context(s,{"sub":"new-subject","email":"new@example.com","email_verified":True,"name":"New Company"})
        assert identity.subject=="new-subject" and identity.issuer==issuer
        assert membership.role=="OWNER" and identity.default_tenant_id==membership.tenant_id
        assert s.scalar(select(Organization).where(Organization.tenant_id==membership.tenant_id)) is not None
        assert s.get(Onboarding,membership.tenant_id) is not None
        profile=s.get(IdentityProfileRecord,identity.id);assert profile.email=="new@example.com" and profile.email_verified is True


def test_email_cannot_silently_link_a_different_oidc_subject():
    with DB() as s:
        user=s.scalar(select(User).where(User.email=="new@example.com"));assert user is not None
        try:resolve_identity_context(s,{"sub":"attacker-subject","email":"new@example.com","email_verified":True})
        except Exception as exc:assert getattr(exc,"status_code",None)==409 and getattr(exc,"detail","")=="identity_link_review_required"
        else:raise AssertionError("email-based identity takeover was allowed")


def _browser_login_cookie():
    raw="browser-session-fixture"
    with DB() as s:
        identity=s.scalar(select(OidcIdentity).where(OidcIdentity.subject=="new-subject"));member=s.scalar(select(TenantMember).where(TenantMember.user_id==identity.user_id));
        s.add(BrowserSession(id="browser-a",token_hash=sha(raw),csrf_hash=sha("csrf-a"),identity_id=identity.id,user_id=identity.user_id,tenant_id=member.tenant_id,role=member.role,created_at=datetime.now(timezone.utc),last_seen_at=datetime.now(timezone.utc),expires_at=datetime(2099,1,1,tzinfo=timezone.utc)));s.commit();return raw,member.tenant_id


def test_dashboard_is_tenant_scoped_and_mutations_require_csrf():
    raw,tenant_id=_browser_login_cookie();client.cookies.set(auth_bff.SESSION_COOKIE,raw,path="/")
    with DB() as s:
        other=Tenant(id="other",name="Other",quota=10);s.add(other);s.add(Message(id="other-message",tenant_id="other",recipient="x@example.com",sender="a@example.com",subject="secret-other-tenant",status="queued"));s.add(Message(id="own-message",tenant_id=tenant_id,recipient="owner@example.com",sender="sender@example.com",subject="own",status="queued"));s.commit()
    response=client.get("/app/api/dashboard");assert response.status_code==200,response.text
    body=response.json();assert body["metrics"]["messages_total"]==1 and body["recent_messages"][0]["subject"]=="own"
    assert client.patch("/app/api/onboarding",json={"step":2,"checklist":{"profile":True}}).status_code==403
    session=client.get("/auth/session").json();updated=client.patch("/app/api/onboarding",headers={"X-Klyrow-CSRF":session["csrf_token"]},json={"step":2,"use_case":"transactional","checklist":{"profile":True}});assert updated.status_code==200,updated.text;assert updated.json()["checklist"]["profile"] is True


def test_read_only_browser_member_cannot_send_mail():
    raw = "browser-read-only-session"
    tenant_id = "tenant-read-only"
    user_id = "user-read-only"
    identity_id = "identity-read-only"
    with DB() as s:
        s.add(Tenant(id=tenant_id, name="Read Only Tenant", quota=10))
        s.add(User(id=user_id, tenant_id=tenant_id, email="readonly@example.com", password_hash=sha("unused"), role="tenant_admin"))
        s.add(OidcIdentity(id=identity_id, issuer=issuer, subject="subject-read-only", user_id=user_id, default_tenant_id=tenant_id, identity_type="KLYROW_ONLY"))
        s.add(TenantMember(id="member-read-only", tenant_id=tenant_id, user_id=user_id, role="READ_ONLY"))
        s.add(BrowserSession(id="session-read-only", token_hash=sha(raw), csrf_hash=sha("csrf-read-only"), identity_id=identity_id, user_id=user_id, tenant_id=tenant_id, role="READ_ONLY", created_at=datetime.now(timezone.utc), last_seen_at=datetime.now(timezone.utc), expires_at=datetime(2099,1,1,tzinfo=timezone.utc)))
        s.commit()
    client.cookies.set(auth_bff.SESSION_COOKIE, raw, path="/")
    with patch("apps.gateway.app.tenancy_onboarding._send", new=AsyncMock()) as send:
        response = client.post("/app/api/email/send", headers={"X-Klyrow-CSRF": "csrf-read-only", "Idempotency-Key": "readonly-send"}, json={"to":"person@example.net","sender":"sender@example.com","subject":"blocked","html":"<p>blocked</p>"})
    assert response.status_code == 403
    assert response.json()["detail"] == "mail_send_permission_required"
    assert send.await_count == 0


def test_owner_cannot_access_platform_admin_dashboard():
    response=client.get("/app/api/admin/dashboard");assert response.status_code==403,response.text


def test_product_routes_use_built_spa_contract():
    assert any(getattr(route,"path",None)=="/app" for route in app.routes)
    assert any(getattr(route,"path",None)=="/onboarding" for route in app.routes)
    asset_mount=next(route for route in app.routes if getattr(route,"path",None)=="/auth-assets")
    assert Path(asset_mount.app.directory)==AUTH_WEB_DIST
