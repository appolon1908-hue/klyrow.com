import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.internal.klyrow_mail import receive_klyrow_mail
from app.core.config import settings
from app.klyrow_alert_adapter import KlyrowAlertAdapter, KlyrowAlertAdapterError
from app.workers.klyrow_mail_odoo import DeliveryFailure, RestrictedOdooTransport, process
from test_klyrow_alert_adapter import request as alert_request, settings as adapter_settings


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [[], None, True, 1, "event", {"event_type": []}, {"event_type": {}}])
async def test_non_object_or_invalid_event_type_is_422_without_database_work(monkeypatch, value):
    monkeypatch.setattr(settings, "klyrow_mail_ingress_enabled", True)
    async def receive():
        return {"type": "http.request", "body": json.dumps(value).encode(), "more_body": False}
    request = Request({"type": "http", "method": "POST", "path": "/internal/provider-events/klyrow",
        "headers": [(b"content-type", b"application/json")]}, receive)
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await receive_klyrow_mail(request, db)
    assert exc.value.status_code == 422
    db.execute.assert_not_called()


@pytest.mark.parametrize("field", ["fingerprint", "state", "severity", "service", "host", "environment", "labels"])
@pytest.mark.parametrize("value", [None, [], {}, 10, ""])
def test_alert_evidence_fields_are_validated_before_provider_mapping(field, value):
    command = alert_request()
    alert = {**command.payload["alert"], field: value}
    if field == "labels" and value == {}:
        return  # Empty label objects are valid.
    changed = replace(command, payload={**command.payload, "alert": alert})
    with pytest.raises(KlyrowAlertAdapterError):
        KlyrowAlertAdapter(adapter_settings(), env={})._validate_payload(changed)


@pytest.fixture
def odoo_transport(monkeypatch, tmp_path):
    path = tmp_path / "test-odoo-key"
    path.write_text("synthetic-odoo-test-key")
    monkeypatch.setattr(settings, "klyrow_mail_odoo_api_key_file", str(path))
    monkeypatch.setattr(settings, "klyrow_mail_odoo_url", "https://odoo.example.test")
    monkeypatch.setattr(settings, "klyrow_mail_odoo_database", "test")
    monkeypatch.setattr(settings, "klyrow_mail_odoo_username", "test")
    original = httpx.AsyncClient
    def install(auth, result):
        def handle(request):
            response = auth if json.loads(request.content)["params"]["service"] == "common" else result
            return httpx.Response(200, content=response, request=request)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs))
        return RestrictedOdooTransport()
    return install


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [b"not json", b"[]", b"null", b"false", b'"text"', b"123"])
@pytest.mark.parametrize("phase", ["auth", "ingest"])
async def test_malformed_odoo_responses_become_bounded_delivery_failures(odoo_transport, raw, phase):
    transport = odoo_transport(raw if phase == "auth" else b'{"result":1}', raw)
    with pytest.raises(DeliveryFailure, match="invalid_odoo_response"):
        await transport.deliver({}, "idempotency-test")


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{"error": "bad"}, {"error": {"data": []}}, {"result": True}, {"result": {"id": True}}])
async def test_odoo_nested_shapes_and_boolean_ids_are_rejected(odoo_transport, body):
    transport = odoo_transport(b'{"result":1}', json.dumps(body).encode())
    with pytest.raises(DeliveryFailure):
        await transport.deliver({}, "idempotency-test")


@pytest.mark.asyncio
async def test_poison_odoo_response_reaches_dead_letter_and_releases_lease(odoo_transport, monkeypatch):
    monkeypatch.setattr(settings, "klyrow_mail_worker_max_attempts", 3)
    transport = odoo_transport(b'{"result":1}', b"bad json")
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(first=lambda: ("event",))
    row = {"event_id": "event", "idempotency_key": "idempotency-test", "provider_event_id": "provider-event",
        "inbound_id": "inbound", "recipient": "support@example.com", "lease_token": "lease",
        "payload": {"sender": "sender@example.com"}}
    for attempt in range(3):
        result = await process(db, {**row, "attempts": attempt}, transport)
        params = db.execute.call_args.args[1]
        assert params["attempts"] == attempt + 1
        assert params["error"] == "invalid_odoo_response"
        assert params["token"] == "lease"
        assert result == ("dead_letter" if attempt == 2 else "retry_wait")
    assert db.commit.await_count == 3
