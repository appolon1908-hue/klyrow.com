BEGIN;

CREATE TABLE IF NOT EXISTS webmail_attachments (
    id varchar PRIMARY KEY,
    tenant_id varchar NOT NULL,
    mailbox_id varchar NOT NULL REFERENCES webmail_mailboxes(id) ON DELETE CASCADE,
    message_id varchar NOT NULL REFERENCES webmail_messages(id) ON DELETE CASCADE,
    filename varchar NOT NULL,
    content_type varchar NOT NULL,
    size integer NOT NULL CHECK (size >= 0 AND size <= 25000000),
    sha256 varchar NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    content bytea NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_webmail_attachment_message_digest_name
      UNIQUE (message_id, sha256, filename),
    CONSTRAINT webmail_attachment_content_size_matches
      CHECK (octet_length(content) = size)
);

CREATE INDEX IF NOT EXISTS ix_webmail_attachments_tenant_id
  ON webmail_attachments (tenant_id);
CREATE INDEX IF NOT EXISTS ix_webmail_attachments_mailbox_id
  ON webmail_attachments (mailbox_id);
CREATE INDEX IF NOT EXISTS ix_webmail_attachments_message_id
  ON webmail_attachments (message_id);

COMMIT;
