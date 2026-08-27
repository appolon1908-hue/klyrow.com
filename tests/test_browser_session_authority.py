import os
import uuid
from datetime import timedelta

from fastapi.testclient import TestClient

from apps.gateway.app import auth_bff
from apps.gateway.app.auth_bff import BrowserSession, SESSION_COOKIE
from apps.gateway.app.browser_auth_actions import stable_csrf_token
from apps.gateway.app.main import Base, DB, Tenant, User, engine, ph, sha
from apps.gateway.app.platform import app
from apps.gateway.app.tenancy import OidcIdentity, TenantMember

ISSUER = "https://auth.codestra.co/realms/codestra"


def _seed_session():
    os.environ["KLYROW_OIDC_ISSUER"] = ISSUER
    os.environ["KLYROW_OIDC_CLIENT_ID"] = "klyrow-portal"
    Base.metadata.create_all(engine)
    suffix = uuid.uuid4().hex
    tenant_id = f"tenant-authority-{suffix}"
    user_id = f"user-authority-{suffix}"
    identity_id = f"identity-authority-{suffix}"
    member_id = f"member-authority-{suffix}"
    session_id = f"session-authority-{suffix}"
    raw = "browser_" + uuid.uuid4().hex
    with DB() as session:
        session.add(Tenant(id=tenant_id, name="Authority Tenant", quota=10))
        session.add(
            User(
                id=user_id,
                tenant_id=tenant_id,
                email=f"authority-{suffix}@example.com",
                password_hash=ph.hash("not-used"),
                role="tenant_admin",
            )
        )
        session.add(
            TenantMember(
                id=member_id,
                tenant_id=tenant_id,
                user_id=user_id,
                role="OWNER",
            )
        )
        session.add(
            OidcIdentity(
                id=identity_id,
                issuer=ISSUER,
                subject=f"subject-{suffix}",
                user_id=user_id,
                default_tenant_id=tenant_id,
                identity_type="KLYROW_ONLY",
            )
        )
        session.add(
            BrowserSession(
                id=session_id,
                token_hash=sha(raw),
                csrf_hash=sha(stable_csrf_token(session_id)),
                identity_id=identity_id,
                user_id=user_id,
                tenant_id=tenant_id,
                role="OWNER",
                refresh_ciphertext="not-reached",
                expires_at=auth_bff.now() + timedelta(hours=1),
            )
        )
        session.commit()
    client = TestClient(app, base_url="https://app.klyrow.test")
    client.cookies.set(SESSION_COOKIE, raw)
    return client, tenant_id, user_id, identity_id, member_id, session_id


def _assert_revoked(session_id: str):
    with DB() as session:
        assert session.get(BrowserSession, session_id).revoked_at is not None


def test_disabled_user_is_revoked_on_next_browser_request():
    client, _tenant_id, user_id, _identity_id, _member_id, session_id = _seed_session()
    with DB() as session:
        user = session.get(User, user_id)
        user.enabled = False
        session.commit()

    response = client.get("/auth/session")
    assert response.status_code == 401
    assert response.json()["detail"] == "principal_disabled"
    _assert_revoked(session_id)


def test_disabled_identity_cannot_refresh_or_rotate_session():
    client, _tenant_id, _user_id, identity_id, _member_id, session_id = _seed_session()
    with DB() as session:
        identity = session.get(OidcIdentity, identity_id)
        identity.enabled = False
        session.commit()

    response = client.post(
        "/auth/refresh",
        headers={"X-Klyrow-CSRF": stable_csrf_token(session_id)},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "principal_disabled"
    _assert_revoked(session_id)


def test_membership_role_changes_are_reloaded_for_existing_sessions():
    client, _tenant_id, _user_id, _identity_id, member_id, _session_id = _seed_session()
    with DB() as session:
        member = session.get(TenantMember, member_id)
        member.role = "READ_ONLY"
        session.commit()

    response = client.get("/auth/session")
    assert response.status_code == 200
    assert response.json()["role"] == "READ_ONLY"
