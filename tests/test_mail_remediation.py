import hashlib
import hmac
import json
import os
import time
import uuid
import base64
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.update(
    KLYROW_DATABASE_URL="sqlite:///./test-mail-remediation.db",
    KLYROW_SESSION_SECRET="test-mail-remediation-secret-at-least-32-bytes",
    KLYROW_WEBHOOK_SECRET="mail-remediation-hook-secret",
    KLYROW_SAFE_MODE="true",
    KLYROW_AUTH_RATE_PER_MINUTE="1000",
    KLYROW_RATE_PER_MINUTE="1000",
)
os.environ.pop("KLYROW_TENANT_RESOLVER_URL", None)

from fastapi.testclient import TestClient
from sqlalchemy import select
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from apps.gateway.app.mail_roles import ROLE_ADDRESSES
from apps.gateway.app.gmail_seed import gmail_folder, seed_secret_path
from apps.gateway.app.main import (
    AllowedSender,
    Base,
    DB,
    Domain,
    InboundRouteConfig,
    PostalEvent,
    Tenant,
    User,
    app,
    engine,
    ph,
    rate_buckets,
    sha,
)
from apps.gateway.app.provider import ProviderInbound
from apps.gateway.app.postal_transport import postal_headers, resolve_postal_transport, transport_status
from apps.gateway.app.security_smtp_worker import postal_payload
from apps.gateway.app.tenancy import ScopedApiKey, ServiceAccount


client = TestClient(app)


def setup_module():
    rate_buckets.clear()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with DB() as session:
        session.add_all(
            [
                Tenant(id="tenant-a", name="Tenant A", quota=100),
                Tenant(id="root", name="Root", quota=100),
                User(id="tenant-user", tenant_id="tenant-a", email="tenant@example.com", password_hash=ph.hash("long-enough-password"), role="tenant_admin"),
                User(id="root-user", tenant_id="root", email="root@example.com", password_hash=ph.hash("long-enough-password"), role="platform_admin"),
                Domain(id="domain-a", tenant_id="tenant-a", domain="example.com", token="verified", verified=True),
                AllowedSender(id="sender-a", tenant_id="tenant-a", address="support@example.com", role="support", enabled=True),
            ]
        )
        session.commit()


def login(email: str) -> dict[str, str]:
    response = client.post("/v1/auth/login", json={"email": email, "password": "long-enough-password"})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_structured_provider_payload_no_longer_requires_raw_b64():
    payload = postal_payload(
        {
            "id": "provider-message-1",
            "sender": "support@example.test",
            "recipient": "person@example.net",
            "subject": "Structured",
            "correlation_id": "structured-correlation",
            "stream": "TRANSACTIONAL",
            "tracking_mode": "OPEN_CLICK",
            "payload": {"text": "plain", "html": "<p>html</p>", "reply_to": "help@example.test"},
        }
    )
    assert payload["plain_body"] == "plain"
    assert payload["html_body"] == "<p>html</p>"
    assert payload["headers"]["Reply-To"] == "help@example.test"
    assert payload["headers"]["Message-ID"].startswith("<")
    assert payload["track_opens"] is True and payload["track_clicks"] is True


def test_versioned_role_manifest_matches_runtime_contract():
    manifest = json.loads(Path("config/mail/role-addresses.json").read_text(encoding="utf-8"))
    configured = {item["local_part"]: item["destination_kind"] for item in manifest["addresses"]}
    assert manifest["version"] == 1
    assert configured == {name: value["destination_kind"] for name, value in ROLE_ADDRESSES.items()}


def test_gmail_seed_adapter_maps_folders_and_confines_secret_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("KLYROW_SEED_SECRET_DIR", str(tmp_path))
    assert seed_secret_path("secret://gmail/seed.json") == tmp_path / "gmail" / "seed.json"
    assert gmail_folder(["INBOX", "UNREAD"]) == "INBOX"
    assert gmail_folder(["SPAM"]) == "SPAM"
    try:
        seed_secret_path("secret://../outside")
    except RuntimeError:
        pass
    else:
        raise AssertionError("secret path escape was accepted")


def test_postal_transport_registry_routes_beyvra_to_its_own_secret(tmp_path, monkeypatch):
    default_key = tmp_path / "default-key"
    beyvra_key = tmp_path / "beyvra-key"
    default_key.write_text("default-secret", encoding="utf-8")
    beyvra_key.write_text("beyvra-secret", encoding="utf-8")
    registry = tmp_path / "transports.json"
    registry.write_text(json.dumps({"version": 1, "default": {"api_url": "https://postal.example.com", "api_host": "postal.example.com", "api_key_file": str(default_key)}, "domains": {"beyvra.com": {"api_url": "https://postal.beyvra.com", "api_host": "postal.beyvra.com", "api_key_file": str(beyvra_key)}}}), encoding="utf-8")
    monkeypatch.setenv("KLYROW_POSTAL_TRANSPORTS_FILE", str(registry))
    selected = resolve_postal_transport("support@beyvra.com")
    assert selected.api_url == "https://postal.beyvra.com"
    assert postal_headers(selected, "idempotency")["X-Server-API-Key"] == "beyvra-secret"
    assert resolve_postal_transport("support@example.net").api_url == "https://postal.example.com"
    status = transport_status("beyvra.com")
    assert status["ready"] is True and "api_key" not in json.dumps(status)


def test_scoped_api_key_and_service_account_authenticate_with_enforced_scopes():
    api_secret = "kly_live_" + "a" * 40
    service_secret = "klys_" + "b" * 40
    with DB() as session:
        session.add(
            ScopedApiKey(
                id="scoped-key",
                tenant_id="tenant-a",
                name="sender",
                prefix=api_secret[:16],
                verifier_hash=sha(api_secret),
                scopes_json='["mail.send"]',
                environment="production",
                ip_allowlist_json="[]",
                created_by="tenant-user",
            )
        )
        session.add(
            ServiceAccount(
                id="service-account",
                tenant_id="tenant-a",
                name="reader",
                client_id="klyrow_machine_reader",
                secret_hash=ph.hash(service_secret),
                scopes_json='["mail.read"]',
                created_by="tenant-user",
            )
        )
        session.commit()
    send = client.post(
        "/v1/messages",
        headers={"Authorization": "Bearer " + api_secret, "Idempotency-Key": "machine-send-0001"},
        json={"to": "person@example.net", "sender": "support@example.com", "subject": "Machine", "html": "<p>Machine</p>"},
    )
    assert send.status_code == 202, send.text
    assert client.get("/v1/domains", headers={"Authorization": "Bearer " + api_secret}).status_code == 403
    read_headers = {"Authorization": "Bearer " + service_secret, "X-Klyrow-Client-Id": "klyrow_machine_reader"}
    assert client.get("/v1/messages", headers=read_headers).status_code == 200
    assert client.get("/v1/domains", headers=read_headers).status_code == 403


def test_postal_webhook_is_acknowledged_after_durable_persist_when_middleware_is_down(monkeypatch):
    monkeypatch.setenv("KLYROW_WEBHOOK_SECRET", "mail-remediation-hook-secret")
    body = json.dumps({"event": "email.delivered", "message_id": "provider-event-message", "tenant_id": "tenant-a"}, separators=(",", ":"))
    timestamp = str(int(time.time()))
    event_id = str(uuid.uuid4())
    signature = hmac.new(
        b"mail-remediation-hook-secret",
        f"{timestamp}.{event_id}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()
    headers = {"X-Klyrow-Timestamp": timestamp, "X-Klyrow-Event-Id": event_id, "X-Klyrow-Signature": signature, "Content-Type": "application/json"}
    with patch("apps.gateway.app.main.emit_middleware", new=AsyncMock(return_value=False)):
        response = client.post("/v1/webhooks/postal", headers=headers, content=body)
    assert response.status_code == 202
    assert response.json()["middleware_delivery"] == "retry"
    with DB() as session:
        stored = session.get(PostalEvent, event_id)
        assert stored.state == "retry" and stored.attempts == 1


def test_role_addresses_are_idempotently_provisioned_and_visible_to_tenant():
    destinations = {definition["destination_kind"]: "attested:" + definition["destination_kind"] for definition in ROLE_ADDRESSES.values()}
    response = client.post(
        "/v1/admin/mail/role-addresses/provision",
        headers=login("root@example.com"),
        json={"tenant_id": "tenant-a", "domains": ["example.com"], "destination_refs": destinations, "activate": True},
    )
    assert response.status_code == 200, response.text
    assert response.json()["addresses"] == 16
    replay = client.post(
        "/v1/admin/mail/role-addresses/provision",
        headers=login("root@example.com"),
        json={"tenant_id": "tenant-a", "domains": ["example.com"], "destination_refs": destinations, "activate": True},
    )
    assert replay.json()["routes_created"] == 0 and replay.json()["senders_created"] == 0
    listed = client.get("/v1/mail/role-addresses", headers=login("tenant@example.com")).json()
    assert len(listed["items"]) == 16
    assert all(item["receiving_enabled"] for item in listed["items"])


def test_provider_inbox_is_tenant_scoped_and_does_not_list_body_content():
    with DB() as session:
        route = session.scalar(select(InboundRouteConfig).where(InboundRouteConfig.tenant_id == "tenant-a"))
        session.add(
            ProviderInbound(
                id="inbound-a",
                tenant_id="tenant-a",
                provider_event_id="provider-inbound-a",
                route_id=route.id,
                message_id_header="<message@example.net>",
                sender="person@example.net",
                recipient=route.address,
                subject="Reply",
                text_body="private body",
                html_body="<p>private body</p>",
                attachments_json="[]",
                disposition="ACCEPT",
            )
        )
        session.commit()
    listed = client.get("/v1/internal/email/inbound/messages", headers=login("tenant@example.com"))
    assert listed.status_code == 200
    assert listed.json()["items"][0]["inbound_id"] == "inbound-a"
    assert "text" not in listed.json()["items"][0]
    detail = client.get("/v1/internal/email/inbound/messages/inbound-a", headers=login("tenant@example.com"))
    assert detail.json()["text"] == "private body"


def test_signed_postal_raw_http_endpoint_persists_reply(tmp_path, monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key_path = tmp_path / "postal-inbound-public.pem"
    public_key_path.write_bytes(private_key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    monkeypatch.setenv("KLYROW_POSTAL_WEBHOOK_PUBLIC_KEY", str(public_key_path))
    with DB() as session:
        route = session.scalar(select(InboundRouteConfig).where(InboundRouteConfig.tenant_id == "tenant-a", InboundRouteConfig.address == "support@example.com"))
        if not route:
            route = InboundRouteConfig(id="postal-route", tenant_id="tenant-a", address="support@example.com", destination_kind="odoo_helpdesk", destination_ref="attested:helpdesk", verified=True, enabled=True)
            session.add(route)
        else:
            route.verified = True;route.enabled = True
        session.commit()
    raw = b"From: person@example.net\r\nTo: support@example.com\r\nSubject: Postal reply\r\nMessage-ID: <postal-reply@example.net>\r\nX-Postal-Spam-Score: 0.2\r\n\r\nReply body"
    body = json.dumps({"id": 42, "rcpt_to": "support@example.com", "mail_from": "person@example.net", "message": base64.encodebytes(raw).decode(), "base64": True, "size": len(raw)}, separators=(",", ":")).encode()
    signature = base64.b64encode(private_key.sign(body, padding.PKCS1v15(), hashes.SHA256())).decode()
    response = client.post("/v1/webhooks/postal-inbound", headers={"X-Postal-Signature-256": signature, "Content-Type": "application/json"}, content=body)
    assert response.status_code == 202, response.text
    assert response.json()["duplicate"] is False
    duplicate = client.post("/v1/webhooks/postal-inbound", headers={"X-Postal-Signature-256": signature, "Content-Type": "application/json"}, content=body)
    assert duplicate.status_code == 202 and duplicate.json()["duplicate"] is True


def test_seed_mailbox_reference_is_never_returned(tmp_path, monkeypatch):
    monkeypatch.setenv("KLYROW_SEED_SECRET_DIR", str(tmp_path))
    credential_path = tmp_path / "gmail" / "seed"
    credential_path.parent.mkdir()
    credential_path.write_text(json.dumps({"client_id": "test-client", "client_secret": "test-secret", "refresh_token": "test-refresh"}), encoding="utf-8")
    headers = login("tenant@example.com")
    created = client.post(
        "/v1/mail/seed-mailboxes",
        headers=headers,
        json={"email": "seed@gmail.com", "provider": "GMAIL", "credential_secret_ref": "secret://gmail/seed", "enabled": True},
    )
    assert created.status_code == 201
    assert "credential_secret_ref" not in created.json()
    listed = client.get("/v1/mail/seed-mailboxes", headers=headers)
    assert "credential_secret_ref" not in listed.text
