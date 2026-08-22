import asyncio
import base64
import hashlib
import json
import os
import ssl
import uuid
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser

from aiosmtpd.smtp import AuthResult, LoginPassword, SMTP
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select

from .main import DB
from .provider import ProviderAudit, ProviderMessage, SenderIdentity, SmtpCredential, TenantMailPolicy, smtp_hasher


def utcnow():
    return datetime.now(timezone.utc)


def authenticate(_server, _session, _envelope, _mechanism, auth_data):
    if not isinstance(auth_data, LoginPassword):
        return AuthResult(success=False, handled=False)
    username = auth_data.login.decode("utf-8", errors="ignore")
    password = auth_data.password.decode("utf-8", errors="ignore")
    with DB() as db:
        credential = db.scalar(select(SmtpCredential).where(SmtpCredential.username == username,
            SmtpCredential.status == "ACTIVE"))
        if not credential:
            return AuthResult(success=False, handled=False)
        expiry = credential.expires_at
        if expiry and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry and expiry <= utcnow():
            return AuthResult(success=False, handled=False)
        try:
            smtp_hasher.verify(credential.secret_hash, password)
        except VerifyMismatchError:
            return AuthResult(success=False, handled=False)
        return AuthResult(success=True, handled=True, auth_data=credential.id)


class GovernedRelay:
    async def handle_MAIL(self, _server, session, envelope, address, _mail_options):
        credential_id = session.auth_data
        with DB() as db:
            credential = db.get(SmtpCredential, credential_id)
            allowed = set(json.loads(credential.allowed_senders_json)) if credential else set()
            identity = db.scalar(select(SenderIdentity).where(SenderIdentity.tenant_id == credential.tenant_id,
                SenderIdentity.email == address.lower(), SenderIdentity.status == "ACTIVE")) if credential else None
            if address.lower() not in allowed or not identity:
                return "550 5.7.1 sender not authorized"
        envelope.mail_from = address.lower()
        return "250 2.1.0 sender accepted"

    async def handle_RCPT(self, _server, session, envelope, address, _rcpt_options):
        sink_domain = os.getenv("KLYROW_SANDBOX_DOMAIN", "klyrow-sink.test").lower()
        with DB() as db:
            credential = db.get(SmtpCredential, session.auth_data)
            tenant_policy = db.get(TenantMailPolicy, credential.tenant_id) if credential else None
            allowed = set(json.loads(tenant_policy.allowed_test_recipients_json or "[]")) if tenant_policy else set()
            sandbox = not tenant_policy or tenant_policy.sandbox_mode
        if sandbox and address.lower() not in allowed and not address.lower().endswith("@" + sink_domain):
            return "550 5.7.1 sandbox recipient not authorized"
        envelope.rcpt_tos.append(address.lower())
        return "250 2.1.5 recipient accepted"

    async def handle_DATA(self, _server, session, envelope):
        raw = envelope.original_content
        parsed = BytesParser(policy=policy.default).parsebytes(raw)
        message_id = parsed.get("Message-ID") or "<" + uuid.uuid4().hex + "@mail.klyrow.com>"
        subject = str(parsed.get("Subject") or "")[:998]
        with DB() as db:
            credential = db.get(SmtpCredential, session.auth_data)
            if not credential or credential.status != "ACTIVE":
                return "550 5.7.1 credential revoked"
            tenant_policy = db.get(TenantMailPolicy, credential.tenant_id)
            if tenant_policy and len(raw) > tenant_policy.max_message_bytes:
                return "552 5.3.4 message too large"
            for recipient in envelope.rcpt_tos:
                digest = hashlib.sha256((credential.id + message_id + recipient).encode()).hexdigest()
                prior = db.scalar(select(ProviderMessage).where(ProviderMessage.tenant_id == credential.tenant_id,
                    ProviderMessage.idempotency_key == "smtp:" + digest))
                if prior:
                    continue
                item = ProviderMessage(id=str(uuid.uuid4()), tenant_id=credential.tenant_id,
                    correlation_id="smtp-" + uuid.uuid4().hex, idempotency_key="smtp:" + digest,
                    request_hash=hashlib.sha256(raw).hexdigest(), sender=envelope.mail_from, recipient=recipient,
                    subject=subject, payload_json=json.dumps({"raw_sha256": hashlib.sha256(raw).hexdigest(),
                        "raw_b64": base64.b64encode(raw).decode(), "message_id": message_id, "size": len(raw)}),
                    stream="TRANSACTIONAL", status="QUEUED", sandbox=True)
                db.add(item)
                db.add(ProviderAudit(id=str(uuid.uuid4()), tenant_id=credential.tenant_id, actor="smtp:" + credential.id,
                    action="smtp.message.queued", outcome="accepted", correlation_id=item.correlation_id, resource_id=item.id))
            db.commit()
        return "250 2.0.0 queued"


async def run():
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(os.environ["KLYROW_SMTP_TLS_CERT"], os.environ["KLYROW_SMTP_TLS_KEY"])
    loop = asyncio.get_running_loop()
    server = await loop.create_server(lambda: SMTP(GovernedRelay(), tls_context=context, require_starttls=True,
        authenticator=authenticate, auth_required=True, hostname=os.getenv("KLYROW_SMTP_HELO", "mail.klyrow.com"),
        data_size_limit=int(os.getenv("KLYROW_SMTP_MAX_BYTES", "26214400"))), host="0.0.0.0",
        port=int(os.getenv("KLYROW_SMTP_PORT", "8025")))
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(run())
