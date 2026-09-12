import json

from apps.gateway.app.delivery_safety import DISABLED_EMAIL_CONTROLS


ODOO_EVENT_PATH = "/api/v1/odoo/events"
ODOO_EVENT_TYPES = frozenset(
    {
        "codestra.odoo.agent.provisioning_requested",
        "codestra.odoo.agent.activation_email_requested",
    }
)


def test_agent_events_are_middleware_owned_before_klyrow_delivery():
    handoff = [
        "odoo-outbox",
        ODOO_EVENT_PATH,
        "durable-middleware-outbox",
        "email.message.send.v1",
        "klyrow-private-email-api",
    ]
    assert handoff[1] == ODOO_EVENT_PATH
    assert handoff.index("klyrow-private-email-api") > handoff.index(
        "durable-middleware-outbox"
    )
    assert ODOO_EVENT_TYPES == {
        "codestra.odoo.agent.provisioning_requested",
        "codestra.odoo.agent.activation_email_requested",
    }


def test_activation_handoff_contains_no_credentials_or_persisted_action_link():
    activation_payload = {
        "delivery": {
            "channel": "email",
            "provider": "klyrow",
            "mode": "keycloak_execute_actions_email",
            "template_key": "agent-welcome-v1",
        },
        "login": {
            "url": "https://login.example.test/activate",
            "required_actions": ["UPDATE_PASSWORD", "CONFIGURE_TOTP"],
        },
    }
    serialized = json.dumps(activation_payload, sort_keys=True)
    for forbidden in (
        "password",
        "token",
        "secret",
        "private_key",
        "recovery_code",
        "activation_link",
        "action_link",
        "reset_link",
    ):
        assert f'"{forbidden}"' not in serialized


def test_email_activation_defaults_remain_fail_closed():
    assert DISABLED_EMAIL_CONTROLS == {
        "KLYROW_SAFE_MODE": True,
        "KLYROW_PRODUCTION_GATE_APPROVED": False,
        "LIVE_EMAIL_DELIVERY": False,
        "EXTERNAL_EMAIL_DELIVERY": False,
        "PRODUCTION_PROVIDER_ROUTING": False,
    }
