import asyncio
from datetime import datetime, timezone

import httpx
import pytest
from fastapi import HTTPException

from apps.gateway.app.mautic_adapter import (
    MAUTIC_ORIGIN_HEADERS,
    SUPPORTED_MAUTIC_COMMANDS,
    _success,
    _oauth_access_token,
    mautic_request,
)
from apps.gateway.app.operations import IntegrationOutbox, IntegrationResult
from apps.gateway.app.production_api import (
    MauticCommand,
    _mautic_permission,
    _operation_json,
    _require_mautic_permission,
    mautic_command,
    operation_cancel,
)


@pytest.mark.parametrize(
    ("command", "payload", "expected"),
    [
        (
            "contact.upsert.v1",
            {"email": "a@example.test"},
            ("POST", "/api/contacts/new"),
        ),
        (
            "contact.upsert.v1",
            {"provider_id": 42, "email": "a@example.test"},
            ("PATCH", "/api/contacts/42/edit"),
        ),
        (
            "segment.delete.v1",
            {"provider_id": "7"},
            ("DELETE", "/api/segments/7/delete"),
        ),
        (
            "campaign.publish.v1",
            {"provider_id": "8"},
            ("PATCH", "/api/campaigns/8/edit"),
        ),
        (
            "campaign_membership.add.v1",
            {"campaign_id": "8", "contact_id": "42"},
            ("POST", "/api/campaigns/8/contact/42/add"),
        ),
        (
            "segment_membership.add.v1",
            {"segment_id": "7", "contact_id": "42"},
            ("POST", "/api/segments/7/contact/42/add"),
        ),
        (
            "email_campaign.state.v1",
            {"email_id": "3", "published": True},
            ("PATCH", "/api/emails/3/edit"),
        ),
        ("webhook.register.v1", {"name": "Klyrow"}, ("POST", "/api/hooks/new")),
        ("sync.request.v1", {"resource": "contacts"}, ("GET", "/api/contacts")),
        (
            "sync.request.v1",
            {"resource": "campaign_events"},
            ("GET", "/api/campaigns/events"),
        ),
        ("sync.request.v1", {"resource": "users_self"}, ("GET", "/api/users/self")),
        (
            "form_submissions.read.v1",
            {"form_id": "9"},
            ("GET", "/api/forms/9/submissions"),
        ),
    ],
)
def test_governed_commands_have_bounded_mautic_routes(command, payload, expected):
    method, path, _ = mautic_request(command, payload)
    assert (method, path) == expected


def test_provider_identifiers_cannot_escape_the_mautic_resource_path():
    with pytest.raises(ValueError, match="provider_id_invalid"):
        mautic_request("contact.delete.v1", {"provider_id": "../admin"})


def test_sync_resource_is_allowlisted():
    with pytest.raises(ValueError, match="sync_resource_invalid"):
        mautic_request("sync.request.v1", {"resource": "roles"})


def test_invented_event_write_route_is_rejected():
    with pytest.raises(ValueError, match="mautic_command_unsupported"):
        mautic_request("event.record.v1", {"type": "page.hit"})


def test_api_command_vocabulary_exactly_matches_the_dispatcher():
    samples = {
        "contact.upsert.v1": {"email": "a@example.test"},
        "contact.delete.v1": {"provider_id": "1"},
        "segment.upsert.v1": {"name": "A"},
        "segment.delete.v1": {"provider_id": "2"},
        "campaign.upsert.v1": {"name": "A"},
        "campaign.delete.v1": {"provider_id": "3"},
        "campaign.publish.v1": {"provider_id": "3"},
        "campaign.pause.v1": {"provider_id": "3"},
        "campaign_membership.add.v1": {"campaign_id": "3", "contact_id": "1"},
        "campaign_membership.remove.v1": {"campaign_id": "3", "contact_id": "1"},
        "segment_membership.add.v1": {"segment_id": "2", "contact_id": "1"},
        "segment_membership.remove.v1": {"segment_id": "2", "contact_id": "1"},
        "email_campaign.state.v1": {"email_id": "4", "published": True},
        "webhook.register.v1": {"name": "Klyrow"},
        "sync.request.v1": {"resource": "contacts"},
        "form_submissions.read.v1": {"form_id": "5"},
    }
    assert set(samples) == SUPPORTED_MAUTIC_COMMANDS
    for command, payload in samples.items():
        MauticCommand(
            command=command,
            aggregate_id="aggregate-1",
            payload=payload,
            request_id="request-1",
            timestamp=datetime.now(timezone.utc),
        )
        mautic_request(command, payload)
    with pytest.raises(ValueError, match="mautic_command_unsupported"):
        MauticCommand(
            command="event.record.v1",
            aggregate_id="aggregate-1",
            request_id="request-2",
            timestamp=datetime.now(timezone.utc),
        )


def test_completed_operation_returns_its_tenant_scoped_persisted_result():
    timestamp = datetime.now(timezone.utc)
    outbox = IntegrationOutbox(
        id="operation-1",
        tenant_id="tenant-a",
        target="MAUTIC",
        event_type="sync.request.v1",
        aggregate_id="contacts",
        payload_json="{}",
        idempotency_key="request-1",
        state="COMPLETED",
        attempts=1,
        created_at=timestamp,
        updated_at=timestamp,
    )
    persisted = IntegrationResult(
        id="result-1",
        tenant_id="tenant-a",
        outbox_id="operation-1",
        source="MAUTIC",
        result_key="mautic:operation-1",
        payload_json='{"contacts":{"total":1}}',
        created_at=timestamp,
    )

    class ResultSession:
        def scalar(self, _statement):
            return persisted

    response = _operation_json(outbox, ResultSession())
    assert response["status"] == "SUCCEEDED"
    assert response["result"] == {"contacts": {"total": 1}}


def test_oauth_client_credentials_token_is_strictly_validated():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/oauth/v2/token"
        assert request.headers["content-type"].startswith(
            "application/x-www-form-urlencoded"
        )
        return httpx.Response(
            200,
            json={"access_token": "t" * 64, "token_type": "bearer", "expires_in": 900},
        )

    async def exercise() -> str:
        async with httpx.AsyncClient(
            base_url="http://mautic", transport=httpx.MockTransport(handler)
        ) as client:
            return await _oauth_access_token(client, "client-id", "client-secret")

    assert asyncio.run(exercise()) == "t" * 64


def test_private_mautic_adapter_preserves_the_canonical_origin():
    assert MAUTIC_ORIGIN_HEADERS == {
        "Host": "app.klyrow.com",
        "X-Forwarded-Proto": "https",
        "X-Forwarded-Prefix": "/mautic",
    }


def test_mautic_mutations_require_the_command_specific_workspace_permission():
    command = MauticCommand(
        command="contact.delete.v1",
        aggregate_id="contact-1",
        payload={"provider_id": "1"},
        request_id="request-1",
        timestamp=datetime.now(timezone.utc),
    )
    with pytest.raises(HTTPException, match="mautic_command_permission_denied") as denied:
        mautic_command(
            command,
            {"sub": "reader", "tenant": "tenant-a", "role": "READ_ONLY"},
            None,
            "idempotency-1",
            "correlation-1",
        )
    assert denied.value.status_code == 403
    _require_mautic_permission(
        {"sub": "analyst", "tenant": "tenant-a", "role": "ANALYST"},
        "sync.request.v1",
    )
    assert {_mautic_permission(command) for command in SUPPORTED_MAUTIC_COMMANDS} == {
        "analytics.read",
        "campaign.manage",
        "contact.manage",
        "webhook.manage",
    }


def test_processing_mautic_operation_cannot_report_successful_cancellation():
    item = IntegrationOutbox(
        id="operation-processing",
        tenant_id="tenant-a",
        target="MAUTIC",
        event_type="campaign.publish.v1",
        aggregate_id="campaign-1",
        payload_json="{}",
        idempotency_key="request-1",
        state="PROCESSING",
        attempts=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    class ProcessingSession:
        def scalar(self, _statement):
            return item

    with pytest.raises(HTTPException, match="operation_processing_not_cancellable") as denied:
        operation_cancel(
            item.id,
            {"sub": "marketer", "tenant": "tenant-a", "role": "MARKETING"},
            ProcessingSession(),
        )
    assert denied.value.status_code == 409


def test_provider_completion_after_state_change_requires_reconciliation():
    item = IntegrationOutbox(
        id="operation-raced",
        tenant_id="tenant-a",
        target="MAUTIC",
        event_type="campaign.publish.v1",
        aggregate_id="campaign-1",
        payload_json="{}",
        idempotency_key="request-1",
        state="CANCELLED",
        attempts=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    class ChangedSession:
        committed = False

        def scalar(self, _statement):
            return item

        def commit(self):
            self.committed = True

    session = ChangedSession()
    _success(session, item.id, {"id": "provider-result"})
    assert session.committed is True
    assert item.state == "DEAD_LETTER"
    assert item.last_error == "provider_completed_after_operation_state_changed"
