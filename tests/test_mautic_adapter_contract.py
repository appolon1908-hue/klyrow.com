import pytest

from apps.gateway.app.mautic_adapter import mautic_request


@pytest.mark.parametrize(
    ("command", "payload", "expected"),
    [
        ("contact.upsert.v1", {"email": "a@example.test"}, ("POST", "/api/v2/contacts")),
        ("contact.upsert.v1", {"provider_id": 42, "email": "a@example.test"}, ("PATCH", "/api/v2/contacts/42")),
        ("segment.delete.v1", {"provider_id": "7"}, ("DELETE", "/api/v2/segments/7")),
        ("campaign.publish.v1", {"provider_id": "8"}, ("PATCH", "/api/v2/campaigns/8")),
        ("campaign_membership.add.v1", {"campaign_id": "8", "contact_id": "42"}, ("POST", "/api/campaigns/8/contact/42/add")),
        ("email_campaign.state.v1", {"email_id": "3", "published": True}, ("PATCH", "/api/v2/emails/3")),
        ("event.record.v1", {"type": "page.hit"}, ("POST", "/api/v2/events")),
        ("webhook.register.v1", {"name": "Klyrow"}, ("POST", "/api/v2/webhooks")),
        ("sync.request.v1", {"resource": "contacts"}, ("GET", "/api/v2/contacts")),
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
        mautic_request("sync.request.v1", {"resource": "users"})
