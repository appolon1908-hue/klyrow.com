from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from apps.gateway.app.production_authorization import (
    ProductionAuthorizationError,
    provider_payload_from_outbox,
    validate_production_authorization,
)


NOW = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)
TENANT = "tenant-a"
MESSAGE = "command-00000001"
CORRELATION = "email-correlation-0001"
IDEMPOTENCY = "email-command-key-0001"
SENDER = "sender@example.com"
RECIPIENTS = ["recipient@example.net"]
CATEGORY = "transactional"


def authorization(**updates):
    value = {
        "schemaVersion": "1.0",
        "tenantId": TENANT,
        "policyVersion": 2,
        "mode": "TRANSACTIONAL_PRODUCTION",
        "authorizationState": "ACTIVE",
        "killSwitchOpen": True,
        "changeId": "CHG-EMAIL-001",
        "category": CATEGORY,
        "validFrom": (NOW - timedelta(minutes=5)).isoformat(),
        "validUntil": (NOW + timedelta(hours=1)).isoformat(),
        "provider": "klyrow-postal",
        "environment": "production",
        "approvedReleaseSha": "a" * 40,
        "authorizationTimestamp": (NOW - timedelta(minutes=10)).isoformat(),
        "activationTimestamp": (NOW - timedelta(minutes=5)).isoformat(),
        "commandBinding": {
            "messageId": MESSAGE,
            "correlationId": CORRELATION,
            "idempotencyKeySha256": hashlib.sha256(IDEMPOTENCY.encode()).hexdigest(),
            "sender": SENDER,
            "recipientsSha256": hashlib.sha256(
                json.dumps(RECIPIENTS, separators=(",", ":")).encode()
            ).hexdigest(),
        },
    }
    value.update(updates)
    return value


def validate(value):
    return validate_production_authorization(
        value,
        tenant_id=TENANT,
        message_id=MESSAGE,
        correlation_id=CORRELATION,
        sender=SENDER,
        recipients=RECIPIENTS,
        category=CATEGORY,
        idempotency_key=IDEMPOTENCY,
        now=NOW,
    )


def test_active_transactional_authorization_is_command_bound():
    result = validate(authorization())
    assert result["mode"] == "TRANSACTIONAL_PRODUCTION"
    assert result["commandBinding"]["messageId"] == MESSAGE


@pytest.mark.parametrize(
    "changes",
    [
        {"authorizationState": "REVOKED"},
        {"killSwitchOpen": False},
        {"mode": "CAMPAIGN_PRODUCTION"},
        {"provider": "smtp"},
        {"environment": "staging"},
        {"validUntil": (NOW - timedelta(seconds=1)).isoformat()},
    ],
)
def test_inactive_campaign_expired_or_wrong_provider_authority_fails_closed(changes):
    with pytest.raises(ProductionAuthorizationError):
        validate(authorization(**changes))


def test_command_identity_mismatch_fails_closed():
    value = authorization()
    value["commandBinding"]["messageId"] = "different-command"
    with pytest.raises(ProductionAuthorizationError, match="binding_mismatch"):
        validate(value)


def test_idempotency_binding_mismatch_fails_closed():
    value = authorization()
    value["commandBinding"]["idempotencyKeySha256"] = "b" * 64
    with pytest.raises(ProductionAuthorizationError, match="idempotency_mismatch"):
        validate(value)


def test_outbox_revalidates_and_strips_control_data_before_provider():
    payload = {
        "to": RECIPIENTS,
        "from": SENDER,
        "subject": "test",
        "stream": "transactional",
        "_codestra_production_authorization": authorization(),
    }
    provider_payload, authorized = provider_payload_from_outbox(
        payload,
        tenant_id=TENANT,
        message_id=MESSAGE,
        correlation_id=CORRELATION,
        now=NOW,
    )
    assert authorized is True
    assert "_codestra_production_authorization" not in provider_payload
    assert "_codestra_production_authorization" in payload
