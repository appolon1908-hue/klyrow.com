import asyncio
import base64
import hashlib
import json
import os
import ssl
import uuid
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser

from aiosmtpd.smtp import AuthResult, LoginPassword, SMTP
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import func, select

from .main import DB, Suppression, Tenant
from .provider import (
    ProviderAudit,
    ProviderDomain,
    ProviderMessage,
    SenderIdentity,
    SmtpCredential,
    TenantMailPolicy,
    smtp_hasher,
)
from .security_payload import encrypted_security_payload
from .smtp_policy import SmtpPolicyError, effective_sandbox, select_credential_stream


def utcnow():
    return datetime.now(timezone.utc)


def _credential_policy(db, credential):
    if not credential or credential.status != "ACTIVE":
        raise SmtpPolicyError("credential revoked")
    tenant_policy = db.get(TenantMailPolicy, credential.tenant_id)
    stream = select_credential_stream(credential.allowed_streams_json)
    sandbox = effective_sandbox(
        stream=stream,
        tenant_sandbox_mode=True if tenant_policy is None else tenant_policy.sandbox_mode,
        tenant_sending_disabled=True
        if tenant_policy is None
        else tenant_policy.sending_disabled,
    )
    return stream, sandbox, tenant_policy


def authenticate(_server, _session, _envelope, _mechanism, auth_data):
    if not isinstance(auth_data, LoginPassword):
        return AuthResult(success=False, handled=False)
    username = auth_data.login.decode("utf-8", errors="ignore")
    password = auth_data.password.decode("utf-8", errors="ignore")
    with DB() as db:
        credential = db.scalar(
            select(SmtpCredential).where(
                SmtpCredential.username == username,
                SmtpCredential.status == "ACTIVE",
            )
        )
        if not credential:
            return AuthResult(success=False, handled=False)
        expiry = credential.expires_at
        if expiry and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry and expiry <= utcnow():
            return AuthResult(success=False, handled=False)
        try:
            smtp_hasher.verify(credential.secret_hash, password)
            _credential_policy(db, credential)
        except (VerifyMismatchError, SmtpPolicyError):
            return AuthResult(success=False, handled=False)
        return AuthResult(success=True, handled=True, auth_data=credential.id)


class GovernedRelay:
    async def handle_MAIL(self, _server, session, envelope, address, _mail_options):
        credential_id = session.auth_data
        with DB() as db:
            credential = db.get(SmtpCredential, credential_id)
            try:
                stream, _sandbox, tenant_policy = _credential_policy(db, credential)
            except SmtpPolicyError:
                return "550 5.7.1 credential policy denied"
            try:
                allowed = set(json.loads(credential.allowed_senders_json))
            except (TypeError, ValueError):
                return "550 5.7.1 sender not authorized"
            normalized_address = address.lower()
            identity = db.scalar(
                select(SenderIdentity).where(
                    SenderIdentity.tenant_id == credential.tenant_id,
                    SenderIdentity.email == normalized_address,
                    SenderIdentity.status == "ACTIVE",
                )
            )
            domain = (
                db.scalar(
                    select(ProviderDomain).where(
                        ProviderDomain.id == identity.domain_id,
                        ProviderDomain.tenant_id == credential.tenant_id,
                    )
                )
                if identity
                else None
            )
            tenant = db.get(Tenant, credential.tenant_id)
            if (
                normalized_address not in allowed
                or not identity
                or identity.stream.upper() != stream
                or not domain
                or domain.status in {"SUSPENDED", "REMOVED"}
                or not tenant
                or not tenant.enabled
                or (
                    tenant_policy
                    and tenant_policy.reputation_state == "SUSPENDED"
                )
            ):
                return "550 5.7.1 sender not authorized"
        envelope.mail_from = normalized_address
        return "250 2.1.0 sender accepted"

    async def handle_RCPT(self, _server, session, envelope, address, _rcpt_options):
        sink_domain = os.getenv("KLYROW_SANDBOX_DOMAIN", "klyrow-sink.test").lower()
        with DB() as db:
            credential = db.get(SmtpCredential, session.auth_data)
            try:
                _stream, sandbox, tenant_policy = _credential_policy(db, credential)
            except SmtpPolicyError:
                return "550 5.7.1 credential policy denied"
            allowed = (
                set(json.loads(tenant_policy.allowed_test_recipients_json or "[]"))
                if tenant_policy
                else set()
            )
            suppressed = db.scalar(
                select(Suppression).where(
                    Suppression.tenant_id == credential.tenant_id,
                    Suppression.email == address.lower(),
                )
            )
        if suppressed:
            return "550 5.7.1 recipient suppressed"
        if (
            sandbox
            and address.lower() not in allowed
            and not address.lower().endswith("@" + sink_domain)
        ):
            return "550 5.7.1 sandbox recipient not authorized"
        envelope.rcpt_tos.append(address.lower())
        return "250 2.1.5 recipient accepted"

    async def handle_DATA(self, _server, session, envelope):
        raw = envelope.original_content
        parsed = BytesParser(policy=policy.default).parsebytes(raw)
        message_id = (
            parsed.get("Message-ID")
            or "<" + uuid.uuid4().hex + "@mail.klyrow.com>"
        )
        subject = str(parsed.get("Subject") or "")[:998]
        with DB() as db:
            credential = db.get(SmtpCredential, session.auth_data)
            try:
                stream, sandbox, tenant_policy = _credential_policy(db, credential)
            except SmtpPolicyError:
                return "550 5.7.1 credential policy denied"
            if tenant_policy and len(raw) > tenant_policy.max_message_bytes:
                return "552 5.3.4 message too large"
            if tenant_policy:
                hour_ago = utcnow() - timedelta(hours=1)
                day_ago = utcnow() - timedelta(days=1)
                hourly = (
                    db.scalar(
                        select(func.count(ProviderMessage.id)).where(
                            ProviderMessage.tenant_id == credential.tenant_id,
                            ProviderMessage.created_at >= hour_ago,
                        )
                    )
                    or 0
                )
                daily = (
                    db.scalar(
                        select(func.count(ProviderMessage.id)).where(
                            ProviderMessage.tenant_id == credential.tenant_id,
                            ProviderMessage.created_at >= day_ago,
                        )
                    )
                    or 0
                )
                if (
                    hourly >= tenant_policy.hourly_limit
                    or daily >= tenant_policy.daily_limit
                ):
                    return "452 4.7.0 tenant quota exceeded"

            identity = db.scalar(
                select(SenderIdentity).where(
                    SenderIdentity.tenant_id == credential.tenant_id,
                    SenderIdentity.email == envelope.mail_from,
                    SenderIdentity.status == "ACTIVE",
                )
            )
            domain = (
                db.scalar(
                    select(ProviderDomain).where(
                        ProviderDomain.id == identity.domain_id,
                        ProviderDomain.tenant_id == credential.tenant_id,
                    )
                )
                if identity
                else None
            )
            if not identity or not domain:
                return "550 5.7.1 sender not authorized"
            if identity.stream.upper() != stream:
                return "550 5.7.1 stream not authorized"
            if not sandbox and (
                stream != "SECURITY"
                or domain.status != "SENDING_ENABLED"
                or not domain.sending_enabled
            ):
                return "550 5.7.1 live security delivery not authorized"

            raw_digest = hashlib.sha256(raw).hexdigest()
            if stream == "SECURITY":
                payload = encrypted_security_payload(
                    raw,
                    raw_sha256=raw_digest,
                    message_id=message_id,
                    stream=stream,
                )
            else:
                payload = {
                    "raw_sha256": raw_digest,
                    "raw_b64": base64.b64encode(raw).decode(),
                    "message_id": message_id,
                    "size": len(raw),
                    "stream": stream,
                }

            for recipient in envelope.rcpt_tos:
                digest = hashlib.sha256(
                    (credential.id + message_id + recipient).encode()
                ).hexdigest()
                prior = db.scalar(
                    select(ProviderMessage).where(
                        ProviderMessage.tenant_id == credential.tenant_id,
                        ProviderMessage.idempotency_key == "smtp:" + digest,
                    )
                )
                if prior:
                    continue
                item = ProviderMessage(
                    id=str(uuid.uuid4()),
                    tenant_id=credential.tenant_id,
                    correlation_id="smtp-" + uuid.uuid4().hex,
                    idempotency_key="smtp:" + digest,
                    request_hash=raw_digest,
                    sender=envelope.mail_from,
                    recipient=recipient,
                    subject=subject,
                    payload_json=json.dumps(
                        payload,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    stream=stream,
                    status="QUEUED",
                    sandbox=sandbox,
                )
                db.add(item)
                db.add(
                    ProviderAudit(
                        id=str(uuid.uuid4()),
                        tenant_id=credential.tenant_id,
                        actor="smtp:" + credential.id,
                        action="smtp." + stream.lower() + ".message.queued",
                        outcome="accepted",
                        correlation_id=item.correlation_id,
                        resource_id=item.id,
                    )
                )
            db.commit()
        return "250 2.0.0 queued"


async def run():
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(
        os.environ["KLYROW_SMTP_TLS_CERT"], os.environ["KLYROW_SMTP_TLS_KEY"]
    )
    loop = asyncio.get_running_loop()
    server = await loop.create_server(
        lambda: SMTP(
            GovernedRelay(),
            tls_context=context,
            require_starttls=True,
            authenticator=authenticate,
            auth_required=True,
            hostname=os.getenv("KLYROW_SMTP_HELO", "mail.klyrow.com"),
            data_size_limit=int(os.getenv("KLYROW_SMTP_MAX_BYTES", "26214400")),
        ),
        host="0.0.0.0",
        port=int(os.getenv("KLYROW_SMTP_PORT", "8025")),
    )
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(run())
