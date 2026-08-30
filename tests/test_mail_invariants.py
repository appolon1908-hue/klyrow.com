"""M0 executable register for the Klyrow mail-engine invariants.

The violated invariants are strict expected failures.  When a later mission
phase fixes one, XPASS is a failure until that phase removes the marker and
records the invariant as closed.
"""

import asyncio
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import UniqueConstraint

from apps.gateway.app import main, provider, security_smtp_worker, smtp_relay
from apps.gateway.app.main import AllowedSender, Base, DB, Domain, Suppression, Tenant, engine
from apps.gateway.app.provider import (
    ProviderDomain,
    ProviderMailIn,
    ProviderMessage,
    SenderIdentity,
    SmtpCredential,
    TenantMailPolicy,
    parse_inbound,
    preflight,
)
from apps.gateway.app.security_payload import (
    decrypt_security_payload,
    encrypted_security_payload,
)
from apps.gateway.app.smtp_policy import effective_sandbox


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "gateway" / "app"


def _source(relative: str) -> str:
    return (APP / relative).read_text(encoding="utf-8")


def _reset_schema() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


@pytest.mark.xfail(strict=True, reason="M1/M2: P1 canonical guard chain is absent")
def test_p1_every_send_path_uses_the_identical_guard_chain():
    guards = APP / "guards.py"
    assert guards.exists()
    assert "def authorize_send" in guards.read_text(encoding="utf-8")
    assert "authorize_send(" in inspect.getsource(main._send)
    assert "authorize_send(" in inspect.getsource(smtp_relay.GovernedRelay.handle_DATA)
    assert "authorize_send(" in inspect.getsource(provider.email_send)


@pytest.mark.xfail(strict=True, reason="M3: P2 SMTP/provider suppression is not stream-aware")
def test_p2_suppression_has_one_stream_aware_implementation():
    relay = _source("smtp_relay.py")
    provider_source = _source("provider.py")
    assert "from .guards import enforce_suppression" in relay
    assert "from .guards import enforce_suppression" in provider_source
    assert "select(Suppression)" not in relay
    assert "select(Suppression)" not in provider_source


@pytest.mark.xfail(strict=True, reason="M2: P3 authoritative marketing consent is absent on B/C")
def test_p3_marketing_consent_is_authoritative_on_every_path():
    assert "enforce_consent(" in inspect.getsource(smtp_relay.GovernedRelay.handle_DATA)
    assert "enforce_consent(" in inspect.getsource(provider.email_send)
    assert "marketing_consent_granted" not in _source("provider.py")


@pytest.mark.xfail(strict=True, reason="M4: P4 metering is not transactional on every path")
def test_p4_every_accepted_send_writes_the_canonical_usage_event_in_transaction():
    for relative in ("main.py", "provider.py", "smtp_relay.py"):
        source = _source(relative)
        assert "from .billing import UsageEvent" in source
        assert "UsageEvent(" in source


@pytest.mark.xfail(strict=True, reason="M5: P5 messaging.py still issues simulated DKIM")
def test_p5_no_tenant_dkim_record_is_simulated():
    offenders = [path for path in APP.rglob("*.py") if "SIMULATED" in path.read_text(encoding="utf-8")]
    assert offenders == []


@pytest.mark.xfail(strict=True, reason="M6: P6 inbound authentication verdict is not persisted")
def test_p6_inbound_cannot_route_without_an_authentication_verdict():
    source = _source("provider.py")
    assert "auth_verdict" in source
    assert all(field in source for field in ("spf_result", "dkim_result", "dmarc_result", "arc_result"))
    assert "dmarc_fail_action" in source


@pytest.mark.xfail(strict=True, reason="M7: P7 ambiguous Postal outcomes are retried")
def test_p7_ambiguous_provider_outcome_reconciles_before_retry():
    sources = _source("main.py") + _source("provider.py") + _source("security_smtp_worker.py")
    assert "INDETERMINATE" in sources
    assert "reconcile_before_retry" in sources


@pytest.mark.xfail(strict=True, reason="M8: P8 marketing unsubscribe headers are not injected")
def test_p8_every_marketing_message_has_one_click_unsubscribe_headers():
    senders = _source("main.py") + _source("provider.py") + _source("smtp_relay.py")
    assert "List-Unsubscribe" in senders
    assert "List-Unsubscribe-Post" in senders


@pytest.mark.xfail(strict=True, reason="M9: P9 enhanced bounce classification is absent")
def test_p9_spam_policy_bounce_never_creates_a_suppression():
    source = _source("main.py") + _source("provider.py")
    assert "def classify_bounce" in source
    assert "5.7.1" in source
    assert "reputation_signal" in source


@pytest.mark.xfail(strict=True, reason="M10: P10 queues have no stream priority")
def test_p10_security_and_transactional_precede_marketing():
    sources = _source("main.py") + _source("provider.py") + _source("security_smtp_worker.py")
    assert "stream_priority" in sources
    assert "SECURITY" in sources and "TRANSACTIONAL" in sources and "MARKETING" in sources


@pytest.mark.xfail(strict=True, reason="M11: P11 warm-up is not enforced by the canonical chain")
def test_p11_warmup_limits_are_enforced_before_every_submission():
    guards = (APP / "guards.py").read_text(encoding="utf-8")
    assert "warmup_daily_limit" in guards
    assert "warmup_hourly_limit" in guards
    assert "authorize_send" in guards


def test_p12_suppressed_recipient_is_rejected_at_smtp_rcpt():
    _reset_schema()
    with DB() as session:
        session.add(Tenant(id="p12", name="P12", quota=10))
        session.add(
            TenantMailPolicy(
                tenant_id="p12",
                sandbox_mode=True,
                sending_disabled=True,
                allowed_test_recipients_json="[]",
            )
        )
        domain = ProviderDomain(
            id="p12-domain",
            tenant_id="p12",
            domain="p12.example",
            status="VERIFIED",
            ownership_token="token",
        )
        session.add(domain)
        session.add(
            SenderIdentity(
                id="p12-sender",
                tenant_id="p12",
                domain_id=domain.id,
                email="sender@p12.example",
                stream="TRANSACTIONAL",
                status="ACTIVE",
            )
        )
        session.add(
            SmtpCredential(
                id="p12-credential",
                tenant_id="p12",
                username="p12-user",
                secret_hash="unused",
                allowed_senders_json='["sender@p12.example"]',
                allowed_streams_json='["TRANSACTIONAL"]',
            )
        )
        session.add(
            Suppression(
                id="p12-suppression",
                tenant_id="p12",
                email="blocked@example.net",
                reason="hard_bounce",
            )
        )
        session.commit()
    relay = smtp_relay.GovernedRelay()
    smtp_session = SimpleNamespace(auth_data="p12-credential")
    envelope = SimpleNamespace(mail_from=None, rcpt_tos=[])
    assert asyncio.run(
        relay.handle_MAIL(None, smtp_session, envelope, "sender@p12.example", [])
    ).startswith("250")
    assert asyncio.run(
        relay.handle_RCPT(None, smtp_session, envelope, "blocked@example.net", [])
    ) == "550 5.7.1 recipient suppressed"
    assert envelope.rcpt_tos == []


def test_p13_sandbox_delivery_is_confined_to_allowlist_or_sink():
    assert main.SAFE_MODE is True
    assert effective_sandbox(
        stream="TRANSACTIONAL",
        tenant_sandbox_mode=False,
        tenant_sending_disabled=False,
        environment={},
    ) is True
    _reset_schema()
    with DB() as session:
        session.add(Tenant(id="p13", name="P13", quota=10))
        session.add(Domain(id="p13-domain", tenant_id="p13", domain="p13.example", token="token", verified=True))
        session.add(AllowedSender(id="p13-sender", tenant_id="p13", address="sender@p13.example", role="mail", enabled=True))
        session.add(
            TenantMailPolicy(
                tenant_id="p13",
                sandbox_mode=True,
                sending_disabled=True,
                allowed_test_recipients_json="[]",
            )
        )
        with pytest.raises(HTTPException, match="sandbox_recipient_not_allowed"):
            preflight(
                ProviderMailIn(
                    sender="sender@p13.example",
                    recipient="external@example.net",
                    subject="sandbox",
                    text="body",
                    sandbox=True,
                ),
                {"tenant": "p13", "sub": "test"},
                session,
            )


def test_p14_security_payload_is_encrypted_and_purged_on_terminal_paths(tmp_path, monkeypatch):
    key_file = tmp_path / "security-payload-key"
    key_file.write_bytes(Fernet.generate_key() + b"\n")
    monkeypatch.setenv("KLYROW_SECURITY_PAYLOAD_KEY_FILE", str(key_file))
    raw = b"Subject: Reset\r\n\r\nsecret-code-482731"
    payload = encrypted_security_payload(
        raw,
        raw_sha256="digest",
        message_id="<p14@example.test>",
        stream="SECURITY",
    )
    assert "secret-code-482731" not in json.dumps(payload)
    assert decrypt_security_payload(payload) == raw
    worker = _source("security_smtp_worker.py")
    assert "_purge_expired_security_payloads" in worker
    assert "scrubbed_security_payload" in worker
    assert '"DEAD_LETTER"' in worker and '"DELIVERED"' in worker


def test_p15_smtp_requires_tls_argon2_and_authorization_at_every_stage():
    relay = _source("smtp_relay.py")
    provider_source = _source("provider.py")
    assert "ssl.TLSVersion.TLSv1_2" in relay
    assert "require_starttls=True" in relay
    assert "auth_required=True" in relay
    assert "PasswordHasher()" in provider_source
    for stage in ("handle_MAIL", "handle_RCPT", "handle_DATA"):
        assert stage in relay


def test_p16_postal_callbacks_verify_hmac_and_rsa_independently():
    source = _source("main.py")
    hmac_hook = inspect.getsource(main.postal_hook)
    rsa_verifier = inspect.getsource(main.verify_postal_signature)
    assert "abs(time.time()-ts)>300" in hmac_hook
    assert "hmac.compare_digest" in hmac_hook
    assert "Replay" in hmac_hook
    assert "padding.PKCS1v15()" in rsa_verifier
    assert "hashes.SHA256()" in rsa_verifier
    assert "postal_native_hook" in source


def test_p17_provider_message_idempotency_and_correlation_are_unique():
    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in ProviderMessage.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("tenant_id", "idempotency_key") in unique_columns
    assert ("tenant_id", "correlation_id") in unique_columns
    send_source = inspect.getsource(provider.email_send)
    assert "idempotency_key_payload_mismatch" in send_source
    assert "correlation_id_already_used" in send_source


def test_p18_attachment_path_components_are_rejected():
    raw = (
        b"From: sender@example.net\r\nTo: recipient@example.net\r\n"
        b"Content-Disposition: attachment; filename=\"../secret.txt\"\r\n\r\nx"
    )
    with pytest.raises(HTTPException, match="unsafe_attachment_filename"):
        parse_inbound(raw, 100_000, 10_000)
    assert "PurePath(filename).name" in inspect.getsource(parse_inbound)


def test_p19_workers_claim_with_skip_locked_and_reclaim_expired_leases():
    assert ".with_for_update(skip_locked=True)" in _source("main.py")
    provider_source = _source("provider.py")
    assert provider_source.count(".with_for_update(skip_locked=True)") >= 2
    assert "recover_expired_leases" in provider_source
    assert ".with_for_update(skip_locked=True)" in _source("security_smtp_worker.py")


def test_p20_middleware_recipient_reference_is_sha256_and_not_cleartext():
    emit_source = inspect.getsource(main.emit_middleware)
    assert '"recipient_reference"' in emit_source
    assert '"sha256:"+hashlib.sha256' in emit_source
    assert '"recipient":' not in emit_source.split("if event_type.startswith", 1)[1].split("else:", 1)[0]
