import asyncio
import importlib
from unittest.mock import AsyncMock, MagicMock, patch

def test_event_delivery_denies_plaintext(monkeypatch):
    main=importlib.import_module("apps.gateway.app.main")
    monkeypatch.setenv("KLYROW_MIDDLEWARE_URL","http://10.40.0.1:18080")
    monkeypatch.setenv("KLYROW_MIDDLEWARE_API_KEY","test-key")
    monkeypatch.setenv("KLYROW_WEBHOOK_SECRET","test-secret")
    with patch("apps.gateway.app.main.httpx.AsyncClient") as client:
        assert asyncio.run(main.emit_middleware("klyrow.test",{"message_id":"test-message"})) is False
        client.assert_not_called()


def test_event_delivery_requires_mtls_material(monkeypatch):
    main=importlib.import_module("apps.gateway.app.main")
    monkeypatch.setenv("KLYROW_MIDDLEWARE_URL","https://server-a.internal")
    monkeypatch.setenv("KLYROW_MIDDLEWARE_API_KEY","test-key")
    monkeypatch.setenv("KLYROW_WEBHOOK_SECRET","test-secret")
    monkeypatch.delenv("KLYROW_SERVER_A_CA_FILE",raising=False)
    monkeypatch.delenv("KLYROW_SERVER_A_CLIENT_CERT_FILE",raising=False)
    monkeypatch.delenv("KLYROW_SERVER_A_CLIENT_KEY_FILE",raising=False)
    with patch("apps.gateway.app.main.httpx.AsyncClient") as client:
        assert asyncio.run(main.emit_middleware("klyrow.test",{"message_id":"test-message"})) is False
        client.assert_not_called()


def test_event_delivery_uses_verified_client_certificate(monkeypatch,tmp_path):
    main=importlib.import_module("apps.gateway.app.main")
    ca=tmp_path/"ca.pem";cert=tmp_path/"client.pem";key=tmp_path/"client.key"
    for value in (ca,cert,key):value.write_text("fixture")
    monkeypatch.setenv("KLYROW_MIDDLEWARE_URL","https://server-a.internal")
    monkeypatch.setenv("KLYROW_MIDDLEWARE_API_KEY","test-key")
    monkeypatch.setenv("KLYROW_WEBHOOK_SECRET","test-secret")
    monkeypatch.setenv("KLYROW_SERVER_A_CA_FILE",str(ca))
    monkeypatch.setenv("KLYROW_SERVER_A_CLIENT_CERT_FILE",str(cert))
    monkeypatch.setenv("KLYROW_SERVER_A_CLIENT_KEY_FILE",str(key))
    context=MagicMock()
    response=MagicMock();response.raise_for_status.return_value=None
    client=AsyncMock();client.__aenter__.return_value=client;client.post.return_value=response
    with patch("apps.gateway.app.main.ssl.create_default_context",return_value=context) as create_context, \
         patch("apps.gateway.app.main.httpx.AsyncClient",return_value=client) as client_factory:
        assert asyncio.run(main.emit_middleware("klyrow.test",{"message_id":"test-message"})) is True
        create_context.assert_called_once_with(cafile=str(ca))
        assert client_factory.call_args.kwargs["verify"] is context


def test_email_event_uses_dedicated_callback_not_legacy_plaintext(monkeypatch,tmp_path):
    main=importlib.import_module("apps.gateway.app.main")
    ca=tmp_path/"ca.pem";cert=tmp_path/"client.pem";key=tmp_path/"client.key"
    for value in (ca,cert,key):value.write_text("fixture")
    monkeypatch.setenv("KLYROW_MIDDLEWARE_URL","http://10.40.0.1:8095")
    monkeypatch.setenv("KLYROW_EMAIL_EVENT_URL","https://email-events.internal/callback")
    monkeypatch.setenv("KLYROW_MIDDLEWARE_API_KEY","test-key")
    monkeypatch.setenv("KLYROW_WEBHOOK_SECRET","test-secret")
    monkeypatch.setenv("KLYROW_SERVER_A_CA_FILE",str(ca))
    monkeypatch.setenv("KLYROW_SERVER_A_CLIENT_CERT_FILE",str(cert))
    monkeypatch.setenv("KLYROW_SERVER_A_CLIENT_KEY_FILE",str(key))
    response=MagicMock();response.raise_for_status.return_value=None
    client=AsyncMock();client.__aenter__.return_value=client;client.post.return_value=response
    with patch("apps.gateway.app.main.ssl.create_default_context",return_value=MagicMock()), \
         patch("apps.gateway.app.main.httpx.AsyncClient",return_value=client):
        assert asyncio.run(main.emit_middleware("klyrow.email.delivered",{"message_id":"test-message"})) is True
        assert client.post.await_count == 1
        assert client.post.await_args.args[0] == "https://email-events.internal/callback"
