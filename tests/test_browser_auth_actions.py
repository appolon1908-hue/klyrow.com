import os
import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.gateway.app import auth_bff
from apps.gateway.app.auth_bff import BrowserSession, OidcLoginTransaction, SESSION_COOKIE
from apps.gateway.app.browser_auth_actions import stable_csrf_token
from apps.gateway.app.main import Base, DB, Tenant, User, engine, ph, sha
from apps.gateway.app.platform import app
from apps.gateway.app.tenancy import OidcIdentity, TenantInvitation, TenantMember

ISSUER = "https://auth.codestra.co/realms/codestra"


def _client():
    os.environ["KLYROW_OIDC_ISSUER"] = ISSUER
    os.environ["KLYROW_OIDC_CLIENT_ID"] = "klyrow-portal"
    Base.metadata.create_all(engine)
    return TestClient(app, base_url="https://app.klyrow.test")


def test_session_reads_keep_one_csrf_token_until_session_rotation():
    client = _client()
    suffix = uuid.uuid4().hex
    tenant_id = f"tenant-csrf-{suffix}"
    user_id = f"user-csrf-{suffix}"
    identity_id = f"identity-csrf-{suffix}"
    session_id = f"session-csrf-{suffix}"
    raw = "browser_" + uuid.uuid4().hex
    with DB() as session:
        session.add(Tenant(id=tenant_id, name="CSRF Tenant", quota=10))
        session.add(
            User(
                id=user_id,
                tenant_id=tenant_id,
                email=f"csrf-{suffix}@example.com",
                password_hash=ph.hash("not-used"),
                role="tenant_admin",
            )
        )
        session.add(
            TenantMember(
                id=f"member-{suffix}",
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
                csrf_hash=sha("obsolete-token"),
                identity_id=identity_id,
                user_id=user_id,
                tenant_id=tenant_id,
                role="OWNER",
                expires_at=auth_bff.now() + timedelta(hours=1),
            )
        )
        session.commit()
    client.cookies.set(SESSION_COOKIE, raw)
    first = client.get("/auth/session")
    second = client.get("/auth/session")
    assert first.status_code == second.status_code == 200
    assert first.json()["csrf_token"] == second.json()["csrf_token"]
    assert first.json()["csrf_token"] == stable_csrf_token(session_id)
    logout = client.post(
        "/auth/logout", headers={"X-Klyrow-CSRF": first.json()["csrf_token"]}
    )
    assert logout.status_code == 200


def test_recovery_uses_supported_keycloak_forgot_credentials_flow_without_lookup():
    client = _client()
    response = client.post(
        "/auth/actions/recover", json={"email": "unknown@example.com"}
    )
    assert response.status_code == 202
    location = response.json()["redirect_to"]
    parsed = urlparse(location)
    assert parsed.scheme == "https" and parsed.netloc == "auth.codestra.co"
    assert parsed.path.endswith("/protocol/openid-connect/forgot-credentials")
    assert "unknown@example.com" not in location
    query = parse_qs(parsed.query)
    assert query["code_challenge_method"] == ["S256"]
    with DB() as session:
        transaction = session.scalar(
            select(OidcLoginTransaction).where(
                OidcLoginTransaction.state_hash == sha(query["state"][0])
            )
        )
        assert transaction and transaction.return_url == "/reset-success"


def test_password_and_verification_actions_use_keycloak_aia():
    client = _client()
    password = client.post("/auth/actions/update-password")
    verification = client.post("/auth/actions/verify-email")
    assert password.status_code == verification.status_code == 202
    assert parse_qs(urlparse(password.json()["redirect_to"]).query)["kc_action"] == [
        "UPDATE_PASSWORD"
    ]
    assert parse_qs(urlparse(verification.json()["redirect_to"]).query)[
        "kc_action"
    ] == ["VERIFY_EMAIL"]



def test_cancelled_application_action_never_reaches_success_page():
    client = _client()
    start = client.post("/auth/actions/update-password")
    query = parse_qs(urlparse(start.json()["redirect_to"]).query)
    response = client.get(
        f"/auth/callback?state={query['state'][0]}&code=unused&kc_action_status=cancelled",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/service-error"


def test_invitation_is_validated_against_durable_token_state():
    client = _client()
    suffix = uuid.uuid4().hex
    raw = "invite_" + uuid.uuid4().hex
    with DB() as session:
        session.add(
            TenantInvitation(
                id=f"invite-{suffix}",
                tenant_id=f"tenant-{suffix}",
                email=f"invitee-{suffix}@example.com",
                role="READ_ONLY",
                token_hash=sha(raw),
                expires_at=auth_bff.now() + timedelta(hours=1),
                created_by="test",
            )
        )
        session.commit()
    valid = client.post("/auth/actions/invitation", json={"token": raw})
    invalid = client.post(
        "/auth/actions/invitation", json={"token": "x" * 32}
    )
    assert valid.status_code == invalid.status_code == 200
    assert valid.json() == {
        "valid": True,
        "redirect_to": "/auth/signup?return_to=%2Fonboarding",
    }
    assert invalid.json() == {"valid": False, "redirect_to": None}
