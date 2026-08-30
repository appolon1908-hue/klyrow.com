"""M0 parity matrix for API, SMTP, and provider mail submission paths."""

import asyncio
import inspect
from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.gateway.app import main, provider, smtp_relay
from apps.gateway.app.billing import UsageEvent as BillingUsageEvent
from apps.gateway.app.main import (
    AllowedSender,
    Base,
    DB,
    Domain,
    Message,
    Suppression,
    Tenant,
    app,
    auth,
    engine,
    rate_buckets,
)
from apps.gateway.app.provider import (
    ProviderDomain,
    ProviderMessage,
    SenderIdentity,
    SmtpCredential,
    TenantMailPolicy,
)


TENANT_ID = "mail-parity"
CONTEXT = {
    "sub": "mail-parity-test",
    "tenant": TENANT_ID,
    "role": "platform_admin",
    "service": True,
}
SINK = "capture@example.net"
EXTERNAL = "recipient@example.org"
CLIENT = TestClient(app)


@dataclass(frozen=True)
class Submission:
    accepted: bool
    status: str
    resource_id: str | None = None


def _sender(stream: str) -> str:
    return ("marketing" if stream.upper() == "MARKETING" else "transactional") + "@m0.example"


def _credential_id(stream: str) -> str:
    return "m0-" + stream.lower() + "-credential"


def _seed_mail_paths() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with DB() as session:
        session.add(Tenant(id=TENANT_ID, name="Mail parity", quota=10, enabled=True))
        session.add(Domain(id="m0-api-domain", tenant_id=TENANT_ID, domain="m0.example", token="verified", verified=True))
        session.add_all(
            [
                AllowedSender(id="m0-api-transactional", tenant_id=TENANT_ID, address=_sender("TRANSACTIONAL"), role="mail", enabled=True),
                AllowedSender(id="m0-api-marketing", tenant_id=TENANT_ID, address=_sender("MARKETING"), role="mail", enabled=True),
            ]
        )
        domain = ProviderDomain(
            id="m0-provider-domain",
            tenant_id=TENANT_ID,
            domain="m0.example",
            status="VERIFIED",
            ownership_token="verified",
        )
        session.add(domain)
        for stream in ("TRANSACTIONAL", "MARKETING"):
            sender = _sender(stream)
            session.add(
                SenderIdentity(
                    id="m0-" + stream.lower() + "-sender",
                    tenant_id=TENANT_ID,
                    domain_id=domain.id,
                    email=sender,
                    stream=stream,
                    status="ACTIVE",
                )
            )
            session.add(
                SmtpCredential(
                    id=_credential_id(stream),
                    tenant_id=TENANT_ID,
                    username="m0-" + stream.lower() + "-user",
                    secret_hash="unused-by-handler-fixture",
                    allowed_senders_json='["' + sender + '"]',
                    allowed_streams_json='["' + stream + '"]',
                )
            )
        session.add(
            TenantMailPolicy(
                tenant_id=TENANT_ID,
                sending_disabled=True,
                sandbox_mode=True,
                daily_limit=10,
                hourly_limit=10,
                warmup_daily_limit=10,
                warmup_hourly_limit=10,
                allowed_test_recipients_json='["capture@example.net"]',
                reputation_state="GOOD",
            )
        )
        session.commit()


@pytest.fixture(autouse=True)
def isolated_mail_paths():
    rate_buckets.clear()
    _seed_mail_paths()
    app.dependency_overrides[auth] = lambda: CONTEXT
    yield
    app.dependency_overrides.pop(auth, None)


def _api_submit(
    *,
    stream: str = "TRANSACTIONAL",
    recipient: str = SINK,
    key: str = "parity-api-key",
    subject: str = "Parity",
    **_ignored,
) -> Submission:
    response = CLIENT.post(
        "/v1/email/send",
        headers={"Idempotency-Key": key},
        json={
            "to": recipient,
            "sender": _sender(stream),
            "subject": subject,
            "html": "<p>Parity</p>",
            "text": "Parity",
            "stream": stream.lower(),
        },
    )
    body = response.json()
    return Submission(
        response.status_code == 202,
        str(body.get("detail") or response.status_code),
        body.get("id"),
    )


def _provider_submit(
    *,
    stream: str = "TRANSACTIONAL",
    recipient: str = SINK,
    key: str = "parity-provider-key",
    subject: str = "Parity",
    marketing_consent_granted: bool = False,
    **_ignored,
) -> Submission:
    response = CLIENT.post(
        "/v1/internal/email/send",
        headers={
            "Idempotency-Key": key,
            "X-Correlation-Id": "correlation-" + key,
        },
        json={
            "sender": _sender(stream),
            "recipient": recipient,
            "subject": subject,
            "text": "Parity",
            "stream": stream.upper(),
            "sandbox": True,
            "marketing_consent_granted": marketing_consent_granted,
        },
    )
    body = response.json()
    return Submission(
        response.status_code == 202,
        str(body.get("detail") or response.status_code),
        body.get("message_id"),
    )


def _smtp_submit(
    *,
    stream: str = "TRANSACTIONAL",
    recipient: str = SINK,
    key: str = "parity-smtp-key",
    subject: str = "Parity",
    **_ignored,
) -> Submission:
    relay = smtp_relay.GovernedRelay()
    smtp_session = SimpleNamespace(auth_data=_credential_id(stream))
    message_id = "<" + key + "@m0.example>"
    raw = (
        f"From: {_sender(stream)}\r\n"
        f"To: {recipient}\r\n"
        f"Message-ID: {message_id}\r\n"
        f"Subject: {subject}\r\n\r\nParity"
    ).encode()
    envelope = SimpleNamespace(mail_from=None, rcpt_tos=[], original_content=raw)
    mail_status = asyncio.run(
        relay.handle_MAIL(None, smtp_session, envelope, _sender(stream), [])
    )
    if not mail_status.startswith("250"):
        return Submission(False, mail_status)
    recipient_status = asyncio.run(
        relay.handle_RCPT(None, smtp_session, envelope, recipient, [])
    )
    if not recipient_status.startswith("250"):
        return Submission(False, recipient_status)
    data_status = asyncio.run(relay.handle_DATA(None, smtp_session, envelope))
    with DB() as session:
        item = session.scalar(
            select(ProviderMessage)
            .where(ProviderMessage.tenant_id == TENANT_ID)
            .order_by(ProviderMessage.created_at.desc())
        )
    return Submission(data_status.startswith("250"), data_status, item.id if item else None)


SUBMITTERS = {
    "api": _api_submit,
    "smtp": _smtp_submit,
    "provider": _provider_submit,
}


def submit(path: str, **kwargs) -> Submission:
    return SUBMITTERS[path](**kwargs)


ALL_PATHS = ["api", "smtp", "provider"]


@pytest.mark.parametrize("path", ALL_PATHS)
def test_suppressed_recipient_rejected(path):
    with DB() as session:
        session.add(Suppression(id="parity-hard-bounce", tenant_id=TENANT_ID, email=SINK, reason="hard_bounce"))
        session.commit()
    assert submit(path).accepted is False


@pytest.mark.parametrize(
    "path",
    [
        "api",
        pytest.param("smtp", marks=pytest.mark.xfail(strict=True, reason="M3: SMTP blocks transactional mail after marketing unsubscribe")),
        pytest.param("provider", marks=pytest.mark.xfail(strict=True, reason="M3: provider path blocks transactional mail after marketing unsubscribe")),
    ],
)
def test_marketing_unsubscribe_does_not_block_transactional(path):
    with DB() as session:
        session.add(Suppression(id="parity-unsubscribe", tenant_id=TENANT_ID, email=SINK, reason="unsubscribe_marketing"))
        session.commit()
    assert submit(path).accepted is True


@pytest.mark.parametrize(
    "path",
    [
        "api",
        pytest.param("smtp", marks=pytest.mark.xfail(strict=True, reason="M2: SMTP trusts marketing submission without authoritative consent")),
        pytest.param("provider", marks=pytest.mark.xfail(strict=True, reason="M2: provider trusts a caller-supplied consent boolean")),
    ],
)
def test_marketing_requires_authoritative_consent(path):
    result = submit(
        path,
        stream="MARKETING",
        key="marketing-no-authoritative-consent",
        marketing_consent_granted=True,
    )
    assert result.accepted is False


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("api", marks=pytest.mark.xfail(strict=True, reason="M4: API writes UsageLedger, not canonical UsageEvent")),
        pytest.param("smtp", marks=pytest.mark.xfail(strict=True, reason="M4: SMTP acceptance writes no usage event")),
        pytest.param("provider", marks=pytest.mark.xfail(strict=True, reason="M4: provider meters on delivery, not acceptance")),
    ],
)
def test_exactly_one_canonical_usage_event_on_acceptance(path):
    assert submit(path, key="usage-" + path).accepted is True
    with DB() as session:
        assert session.query(BillingUsageEvent).filter_by(tenant_id=TENANT_ID).count() == 1


@pytest.mark.parametrize(
    "path",
    [
        "api",
        pytest.param("smtp", marks=pytest.mark.xfail(strict=True, reason="M1: SMTP sandbox accepts an unverified provider domain")),
        pytest.param("provider", marks=pytest.mark.xfail(strict=True, reason="M1: provider sandbox accepts an unverified provider domain")),
    ],
)
def test_unverified_sender_domain_rejected(path):
    with DB() as session:
        session.get(Domain, "m0-api-domain").verified = False
        session.get(ProviderDomain, "m0-provider-domain").status = "PENDING"
        session.commit()
    assert submit(path, key="unverified-" + path).accepted is False


@pytest.mark.parametrize("path", ALL_PATHS)
def test_quota_exhaustion_rejected(path):
    with DB() as session:
        session.get(Tenant, TENANT_ID).quota = 0
        policy = session.get(TenantMailPolicy, TENANT_ID)
        policy.hourly_limit = 0
        policy.daily_limit = 0
        policy.warmup_hourly_limit = 0
        policy.warmup_daily_limit = 0
        session.commit()
    assert submit(path, key="quota-" + path).accepted is False


@pytest.mark.parametrize(
    "path",
    [
        "api",
        pytest.param("smtp", marks=pytest.mark.xfail(strict=True, reason="M1: SMTP does not call the production canary guard")),
        pytest.param("provider", marks=pytest.mark.xfail(strict=True, reason="M1: provider does not call the production canary guard")),
    ],
)
def test_production_canary_guard_is_present(path):
    functions = {
        "api": main._send,
        "smtp": smtp_relay.GovernedRelay.handle_DATA,
        "provider": provider.preflight,
    }
    source = inspect.getsource(functions[path])
    assert "enforce_production_canary" in source or "authorize_send(" in source


@pytest.mark.parametrize("path", ALL_PATHS)
def test_unauthorized_sender_rejected(path):
    with DB() as session:
        session.query(AllowedSender).delete()
        session.query(SenderIdentity).delete()
        session.commit()
    assert submit(path, key="sender-" + path).accepted is False


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("api", marks=pytest.mark.xfail(strict=True, reason="M1: API send relies on auth to recheck tenant state")),
        "smtp",
        "provider",
    ],
)
def test_disabled_tenant_rejected_inside_send_path(path):
    with DB() as session:
        session.get(Tenant, TENANT_ID).enabled = False
        session.commit()
    assert submit(path, key="disabled-" + path).accepted is False


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("api", marks=pytest.mark.xfail(strict=True, reason="M1: API accepts arbitrary recipients in global safe mode")),
        "smtp",
        "provider",
    ],
)
def test_sandbox_external_recipient_rejected(path):
    assert submit(path, recipient=EXTERNAL, key="sandbox-" + path).accepted is False


@pytest.mark.parametrize("path", ALL_PATHS)
def test_identical_replay_persists_one_message(path):
    first = submit(path, key="replay-" + path)
    second = submit(path, key="replay-" + path)
    assert first.accepted is True and second.accepted is True
    assert first.resource_id == second.resource_id
    with DB() as session:
        count = (
            session.query(Message).filter_by(tenant_id=TENANT_ID).count()
            if path == "api"
            else session.query(ProviderMessage).filter_by(tenant_id=TENANT_ID).count()
        )
        assert count == 1


@pytest.mark.parametrize(
    "path",
    [
        "api",
        pytest.param("smtp", marks=pytest.mark.xfail(strict=True, reason="M1: SMTP altered replay is silently accepted")),
        "provider",
    ],
)
def test_altered_replay_is_rejected(path):
    first = submit(path, key="altered-" + path, subject="Original")
    altered = submit(path, key="altered-" + path, subject="Changed")
    assert first.accepted is True
    assert altered.accepted is False
