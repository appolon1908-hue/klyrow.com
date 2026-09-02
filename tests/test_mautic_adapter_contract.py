import asyncio

import httpx
import pytest

from apps.gateway.app.mautic_adapter import _oauth_access_token, mautic_request


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
