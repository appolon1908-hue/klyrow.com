import hashlib
from types import SimpleNamespace

from sqlalchemy import select

from apps.gateway.app.main import Base, DB, InboundRouteConfig, Tenant, engine
from apps.gateway.app.webmail import capture_provider_inbound, get_attachment
from apps.gateway.app.webmail_models import (
    WebmailAttachment,
    WebmailMailbox,
    WebmailMessage,
)


def _mailbox() -> WebmailMailbox:
    return WebmailMailbox(
        id="mailbox-1",
        tenant_id="tenant-a",
        domain_id="domain-1",
        address="support@example.test",
        display_name="Support",
        receiving_enabled=True,
    )


def _parsed() -> dict:
    content = b"durable attachment content"
    return {
        "message_id": "<provider-message@example.test>",
        "from": "Sender <sender@example.net>",
        "to": "support@example.test",
        "subject": "Attachment",
        "text": "See attachment",
        "html": None,
        "in_reply_to": None,
        "references": None,
        "attachments": [
            {
                "filename": "evidence.txt",
                "content_type": "text/plain",
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        ],
        "attachment_contents": [content],
    }


def test_non_webmail_route_cannot_copy_provider_mail_into_a_mailbox():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with DB() as session:
        route = InboundRouteConfig(
            id="route-1",
            tenant_id="tenant-a",
            address="support@example.test",
            destination_kind="webhook",
            destination_ref="support:external",
            verified=True,
            enabled=True,
        )
        session.add_all([Tenant(id="tenant-a", name="Tenant A", quota=100), _mailbox(), route])
        session.commit()
        provider_item = SimpleNamespace(
            id="provider-inbound-1",
            tenant_id="tenant-a",
            recipient="support@example.test",
            disposition="ACCEPT",
        )
        assert capture_provider_inbound(session, route, provider_item, _parsed()) is None
        assert session.scalar(select(WebmailMessage)) is None


def test_owned_route_persists_and_authorizes_attachment_download():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with DB() as session:
        route = InboundRouteConfig(
            id="route-1",
            tenant_id="tenant-a",
            address="support@example.test",
            destination_kind="webmail",
            destination_ref="klyrow:webmail",
            verified=True,
            enabled=True,
        )
        session.add_all([Tenant(id="tenant-a", name="Tenant A", quota=100), _mailbox(), route])
        session.commit()
        provider_item = SimpleNamespace(
            id="provider-inbound-1",
            tenant_id="tenant-a",
            recipient="support@example.test",
            disposition="ACCEPT",
        )
        message = capture_provider_inbound(session, route, provider_item, _parsed())
        session.commit()
        assert message is not None
        attachment = session.scalar(select(WebmailAttachment))
        assert attachment is not None
        assert attachment.content == b"durable attachment content"
        assert attachment.sha256 == hashlib.sha256(attachment.content).hexdigest()
        response = get_attachment(
            "mailbox-1",
            message.id,
            attachment.id,
            {"sub": "owner", "tenant": "tenant-a", "role": "platform_admin"},
            session,
        )
        assert response.body == attachment.content
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "evidence.txt" in response.headers["content-disposition"]
