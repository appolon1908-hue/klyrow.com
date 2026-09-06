"""Run the imported adapters against Klyrow's real HTTP and database boundary."""

from dataclasses import replace

import httpx
import pytest
from sqlalchemy import func, select

from apps.gateway.app import main as core
from app.klyrow_alert_adapter import KlyrowAlertAdapter
from app.klyrow_email_adapter import KlyrowEmailAdapter
from test_klyrow_alert_adapter import request as alert_request, settings
from test_klyrow_email_adapter import execution_request
from test_middleware_email_contract import gateway


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["email", "alert"])
@pytest.mark.parametrize("interrupted", [False, True])
async def test_real_gateway_acceptance_replay_and_interrupted_write(gateway, monkeypatch, kind, interrupted):
    client, sessions, _ = gateway
    if kind == "email":
        command = execution_request(tenant_id="tenant-a", payload_overrides={"from": "sender@example.com"})
        adapter = KlyrowEmailAdapter(type("Settings", (), {"email_delivery_enabled": True})(), env={})
    else:
        command = replace(alert_request(), tenant_id="tenant-a")
        adapter = KlyrowAlertAdapter(settings(), env={
            "OBSERVABILITY_ALERT_EMAIL_DELIVERY": "true",
            "OBSERVABILITY_ALERT_ACTIVATION_ID": "test-alert-activation",
        })
        with sessions() as session:
            session.add(core.Domain(id="alert-domain", tenant_id="tenant-a", domain="codestra.co", token="test", verified=True))
            session.add(core.AllowedSender(id="alert-sender", tenant_id="tenant-a", address="alerts@codestra.co", role="support"))
            session.commit()
    monkeypatch.setattr(adapter, "_base_url", lambda: "https://klyrow-email-api:18000")
    monkeypatch.setattr(adapter, "_tls_context", lambda: True)
    async def token(): return "synthetic-token"
    monkeypatch.setattr(adapter, "_access_token", token)
    calls = []
    original = httpx.AsyncClient
    def handle(request):
        calls.append(request.method)
        response = client.request(request.method, request.url.path, content=request.content, headers=dict(request.headers))
        assert response.status_code in {200, 202}, response.text
        if interrupted and request.method == "POST":
            raise httpx.ReadTimeout("response lost after database commit", request=request)
        return httpx.Response(response.status_code, content=response.content, headers=response.headers)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs))
    result = await adapter.execute(command)
    assert result.status == "accepted"
    assert result.provider_operation_id != command.command_id
    assert calls == (["POST", "GET"] if interrupted else ["POST"])
    assert (await adapter.readback(command)).status == "matched"
    changed_payload = {**command.payload, "content": {**command.payload["content"], "text": "Changed body"}}
    assert (await adapter.readback(replace(command, payload=changed_payload))).status == "mismatch"
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(core.Message)) == 1
        assert session.scalar(select(func.count()).select_from(core.EmailOutbox)) == 0
