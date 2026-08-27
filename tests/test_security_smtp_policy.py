import pytest

from apps.gateway.app.smtp_policy import (
    SmtpPolicyError,
    effective_sandbox,
    parse_allowed_streams,
    security_live_delivery_enabled,
    select_credential_stream,
)


def test_dedicated_security_credential_is_selected():
    assert parse_allowed_streams('["SECURITY"]') == frozenset({"SECURITY"})
    assert select_credential_stream('["security"]') == "SECURITY"


@pytest.mark.parametrize(
    "raw",
    [
        "not-json",
        "{}",
        "[]",
        '["SECURITY", "TRANSACTIONAL"]',
        '["SECURITY", "security"]',
        '["UNKNOWN"]',
    ],
)
def test_invalid_or_multi_stream_credentials_fail_closed(raw):
    with pytest.raises(SmtpPolicyError):
        select_credential_stream(raw)


def test_security_stream_is_disabled_by_default():
    with pytest.raises(SmtpPolicyError, match="disabled"):
        effective_sandbox(
            stream="SECURITY",
            tenant_sandbox_mode=True,
            tenant_sending_disabled=True,
            environment={},
        )


def test_enabled_security_stream_remains_sandboxed_without_live_gate():
    environment = {
        "KLYROW_SECURITY_SMTP_ENABLED": "true",
        "KLYROW_SECURITY_SMTP_LIVE_ENABLED": "false",
    }
    assert security_live_delivery_enabled(environment) is False
    assert (
        effective_sandbox(
            stream="SECURITY",
            tenant_sandbox_mode=True,
            tenant_sending_disabled=True,
            environment=environment,
        )
        is True
    )


def test_live_security_gate_requires_enabled_tenant_policy():
    environment = {
        "KLYROW_SECURITY_SMTP_ENABLED": "true",
        "KLYROW_SECURITY_SMTP_LIVE_ENABLED": "true",
    }
    with pytest.raises(SmtpPolicyError, match="tenant policy"):
        effective_sandbox(
            stream="SECURITY",
            tenant_sandbox_mode=True,
            tenant_sending_disabled=False,
            environment=environment,
        )
    with pytest.raises(SmtpPolicyError, match="tenant policy"):
        effective_sandbox(
            stream="SECURITY",
            tenant_sandbox_mode=False,
            tenant_sending_disabled=True,
            environment=environment,
        )


def test_live_security_gate_opens_only_after_all_controls_pass():
    environment = {
        "KLYROW_SECURITY_SMTP_ENABLED": "true",
        "KLYROW_SECURITY_SMTP_LIVE_ENABLED": "true",
    }
    assert security_live_delivery_enabled(environment) is True
    assert (
        effective_sandbox(
            stream="SECURITY",
            tenant_sandbox_mode=False,
            tenant_sending_disabled=False,
            environment=environment,
        )
        is False
    )


def test_non_security_smtp_streams_remain_sandbox_only():
    environment = {
        "KLYROW_SECURITY_SMTP_ENABLED": "true",
        "KLYROW_SECURITY_SMTP_LIVE_ENABLED": "true",
    }
    assert (
        effective_sandbox(
            stream="TRANSACTIONAL",
            tenant_sandbox_mode=False,
            tenant_sending_disabled=False,
            environment=environment,
        )
        is True
    )
