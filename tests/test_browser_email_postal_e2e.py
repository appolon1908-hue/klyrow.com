import asyncio
import os
from urllib.parse import parse_qs, urlparse
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.gateway.app import agent_mailboxes, auth_bff, messaging, postal_provisioning as provisioning
from apps.gateway.app.main import Base, DB, EmailOutbox, Message, ProductionCanaryGate, engine
from apps.gateway.app import main as gateway
from apps.gateway.app.platform import app


ISSUER = "https://auth.codestra.co/realms/codestra"


def test_login_dashboard_domain_sender_compose_outbox_postal(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("KLYROW_ENV", "development")
    monkeypatch.setenv("KLYROW_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("KLYROW_OIDC_CLIENT_ID", "klyrow-portal")
    monkeypatch.setenv("KLYROW_ALLOW_LEGACY_GLOBAL_POSTAL_KEY", "false")
    monkeypatch.setenv("KLYROW_POSTAL_API_URL", "https://postal.test")
    monkeypatch.setenv("KLYROW_POSTAL_API_HOST_HEADER", "app.klyrow.com")
    monkeypatch.setenv("KLYROW_CANARY_ALLOWED_DOMAIN", "e2e.example")
    monkeypatch.setenv("KLYROW_CANARY_ALLOWED_SENDER", "send@e2e.example")
    monkeypatch.setenv("KLYROW_CANARY_ALLOWED_RECIPIENT", "sink@example.net")
    monkeypatch.setenv("KLYROW_CANARY_ALLOWED_CAMPAIGN", "E2E-CANARY")
    monkeypatch.setenv("KLYROW_CANARY_MAX_DELIVERIES", "1")
    monkeypatch.setattr(gateway, "SAFE_MODE", False)
    monkeypatch.setattr(provisioning, "SAFE_MODE", False)
    monkeypatch.setattr(agent_mailboxes, "authorize_agent_sender", lambda *_args, **_kwargs: None)

    async def middleware_ok(*_args, **_kwargs):
        return True

    async def fake_provisioner(_tenant):
        return {
            "organization_id": "postal-org-e2e",
            "organization_permalink": "postal-org-e2e",
            "server_id": "postal-server-e2e",
            "server_permalink": "postal-server-e2e",
            "mode": "Development",
            "api_key": "tenant-postal-e2e-api-key-value-123456",
        }

    monkeypatch.setattr(gateway, "emit_middleware", middleware_ok)
    monkeypatch.setattr(provisioning, "_call_bridge", fake_provisioner)

    client = TestClient(app, base_url="https://app.klyrow.test")

    # 1. Login: execute the real PKCE state transaction and callback path while
    # replacing only the external Keycloak token/JWKS exchange.
    login = client.get("/auth/login?return_to=/app", follow_redirects=False)
    assert login.status_code == 302
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
    monkeypatch.setattr(auth_bff, "_exchange_code", lambda *_args, **_kwargs: {"id_token": "e2e-id-token", "refresh_token": "e2e-refresh-token"})
    monkeypatch.setattr(
        auth_bff,
        "_validate_id_token",
        lambda *_args, **_kwargs: {
            "iss": ISSUER,
            "sub": "e2e-subject",
            "aud": "klyrow-portal",
            "email": "owner@e2e.example",
            "email_verified": True,
            "name": "E2E Owner",
        },
    )
    callback = client.get(f"/auth/callback?code=e2e-code&state={state}", follow_redirects=False)
    assert callback.status_code == 303 and callback.headers["location"] == "/app"

    # 2. Dashboard: session and workspace are established through the browser BFF.
    session = client.get("/auth/session")
    assert session.status_code == 200 and session.json()["authenticated"] is True
    csrf = session.json()["csrf_token"]
    tenant_id = session.json()["tenant_id"]
    dashboard = client.get("/app/api/dashboard")
    assert dashboard.status_code == 200

    # First login queued per-tenant Postal provisioning; complete it through the
    # same durable worker tick used by the provisioning service.
    assert client.get("/app/api/provisioning/postal").json()["state"] == "PENDING"
    assert asyncio.run(provisioning.provisioning_tick()) == 1
    ready = client.get("/app/api/provisioning/postal")
    assert ready.status_code == 200
    assert ready.json()["state"] == "READY"
    assert ready.json()["credential_fingerprint"].startswith("sha256:")

    # 3. Domain + sender setup through same-origin browser endpoints that reuse
    # the public tenant-safe messaging primitives.
    domain = client.post(
        "/app/api/domains",
        headers={"X-Klyrow-CSRF": csrf},
        json={"domain": "e2e.example"},
    )
    assert domain.status_code == 201, domain.text
    claim_id = domain.json()["id"]
    ownership = domain.json()["dns"]["ownership"]["value"]
    monkeypatch.setattr(messaging, "resolve_txt", lambda _name: [ownership])
    verified = client.post(
        f"/app/api/domains/{claim_id}/verify",
        headers={"X-Klyrow-CSRF": csrf},
        json={},
    )
    assert verified.status_code == 200 and verified.json()["state"] == "VERIFIED"
    sender = client.post(
        "/app/api/senders",
        headers={"X-Klyrow-CSRF": csrf},
        json={
            "domain_claim_id": claim_id,
            "email": "send@e2e.example",
            "display_name": "Klyrow E2E",
            "stream": "TRANSACTIONAL",
        },
    )
    assert sender.status_code == 201 and sender.json()["verified"] is True

    with DB() as s:
        s.add(
            ProductionCanaryGate(
                gate_key=gateway.canary_gate_key(),
                reserved_deliveries=0,
                claimed_deliveries=0,
            )
        )
        s.commit()

    # 4. Compose -> backend -> tenant outbox.
    composed = client.post(
        "/app/api/email/send",
        headers={"X-Klyrow-CSRF": csrf, "Idempotency-Key": "browser-e2e-compose-1"},
        json={
            "to": "sink@example.net",
            "sender": "send@e2e.example",
            "subject": "Klyrow browser E2E",
            "html": "<p>Browser to Postal</p>",
            "text": "Browser to Postal",
            "stream": "transactional",
            "campaign_id": "E2E-CANARY",
        },
    )
    assert composed.status_code == 202, composed.text
    message_id = composed.json()["id"]
    with DB() as s:
        outbox = s.scalar(select(EmailOutbox).where(EmailOutbox.message_id == message_id))
        assert outbox is not None and outbox.tenant_id == tenant_id and outbox.state == "pending"

    # 5. Outbox -> Postal HTTP API. The network boundary is mocked, but the real
    # worker selects and decrypts the tenant credential and constructs the Postal
    # request. This proves the global Postal key cannot be inherited here.
    captured = {}

    class PostalResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"message_id": "postal-provider-e2e"}}

    class PostalClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, url, headers=None, json=None):
            captured.update(url=url, headers=headers or {}, payload=json)
            return PostalResponse()

    with patch.object(provisioning.asyncio, "sleep", new=AsyncMock(side_effect=[None, asyncio.CancelledError()])), patch.object(
        provisioning.httpx, "AsyncClient", return_value=PostalClient()
    ):
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(provisioning.tenant_email_outbox_loop())

    assert captured["url"] == "https://postal.test/api/v1/send/message"
    assert captured["headers"]["X-Server-API-Key"] == "tenant-postal-e2e-api-key-value-123456"
    assert captured["headers"]["Idempotency-Key"] == "klyrow:" + message_id
    assert captured["payload"]["from"] == "send@e2e.example"
    assert captured["payload"]["to"] == ["sink@example.net"]

    with DB() as s:
        outbox = s.scalar(select(EmailOutbox).where(EmailOutbox.message_id == message_id))
        message = s.get(Message, message_id)
        gate = s.get(ProductionCanaryGate, gateway.canary_gate_key())
        assert outbox.state == "delivered" and outbox.provider_message_id == "postal-provider-e2e"
        assert message.status == "accepted"
        assert gate.reserved_deliveries == 1 and gate.claimed_deliveries == 1
