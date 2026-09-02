BEGIN;

CREATE TABLE IF NOT EXISTS webmail_mailboxes (
    id varchar PRIMARY KEY,
    tenant_id varchar NOT NULL,
    domain_id varchar NOT NULL,
    address varchar NOT NULL,
    display_name varchar NOT NULL,
    status varchar NOT NULL DEFAULT 'ACTIVE',
    sending_enabled boolean NOT NULL DEFAULT true,
    receiving_enabled boolean NOT NULL DEFAULT false,
    storage_quota_bytes integer NOT NULL DEFAULT 1073741824,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_webmail_mailbox_tenant_address UNIQUE (tenant_id, address),
    CONSTRAINT webmail_mailbox_status_valid CHECK (status IN ('ACTIVE', 'SUSPENDED', 'REMOVED')),
    CONSTRAINT webmail_mailbox_quota_positive CHECK (storage_quota_bytes > 0)
);
CREATE INDEX IF NOT EXISTS ix_webmail_mailboxes_tenant_id ON webmail_mailboxes (tenant_id);
CREATE INDEX IF NOT EXISTS ix_webmail_mailboxes_domain_id ON webmail_mailboxes (domain_id);
CREATE INDEX IF NOT EXISTS ix_webmail_mailboxes_address ON webmail_mailboxes (address);
CREATE INDEX IF NOT EXISTS ix_webmail_mailboxes_status ON webmail_mailboxes (status);

CREATE TABLE IF NOT EXISTS webmail_access (
    id varchar PRIMARY KEY,
    tenant_id varchar NOT NULL,
    mailbox_id varchar NOT NULL REFERENCES webmail_mailboxes(id) ON DELETE CASCADE,
    user_id varchar NOT NULL,
    role varchar NOT NULL DEFAULT 'READER',
    created_by varchar NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_webmail_access_mailbox_user UNIQUE (mailbox_id, user_id),
    CONSTRAINT webmail_access_role_valid CHECK (role IN ('OWNER', 'SENDER', 'READER'))
);
CREATE INDEX IF NOT EXISTS ix_webmail_access_tenant_id ON webmail_access (tenant_id);
CREATE INDEX IF NOT EXISTS ix_webmail_access_mailbox_id ON webmail_access (mailbox_id);
CREATE INDEX IF NOT EXISTS ix_webmail_access_user_id ON webmail_access (user_id);

CREATE TABLE IF NOT EXISTS webmail_messages (
    id varchar PRIMARY KEY,
    tenant_id varchar NOT NULL,
    mailbox_id varchar NOT NULL REFERENCES webmail_mailboxes(id) ON DELETE CASCADE,
    thread_id varchar NOT NULL,
    provider_inbound_id varchar,
    outbound_message_id varchar,
    direction varchar NOT NULL,
    folder varchar NOT NULL,
    message_id_header varchar,
    in_reply_to varchar,
    reply_to_message_id varchar,
    references_json text NOT NULL DEFAULT '[]',
    from_address varchar NOT NULL,
    to_json text NOT NULL DEFAULT '[]',
    cc_json text NOT NULL DEFAULT '[]',
    bcc_json text NOT NULL DEFAULT '[]',
    reply_to varchar,
    subject varchar NOT NULL DEFAULT '',
    text_body text,
    html_body text,
    attachments_json text NOT NULL DEFAULT '[]',
    is_read boolean NOT NULL DEFAULT false,
    is_starred boolean NOT NULL DEFAULT false,
    delivery_status varchar,
    received_at timestamptz,
    sent_at timestamptz,
    deleted_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_webmail_message_provider_inbound UNIQUE (provider_inbound_id),
    CONSTRAINT uq_webmail_message_outbound UNIQUE (outbound_message_id),
    CONSTRAINT webmail_message_direction_valid CHECK (direction IN ('INBOUND', 'OUTBOUND', 'DRAFT')),
    CONSTRAINT webmail_message_folder_valid CHECK (folder IN ('INBOX', 'SENT', 'DRAFTS', 'ARCHIVE', 'SPAM', 'TRASH'))
);
CREATE INDEX IF NOT EXISTS ix_webmail_messages_tenant_id ON webmail_messages (tenant_id);
CREATE INDEX IF NOT EXISTS ix_webmail_messages_mailbox_id ON webmail_messages (mailbox_id);
CREATE INDEX IF NOT EXISTS ix_webmail_messages_thread_id ON webmail_messages (thread_id);
CREATE INDEX IF NOT EXISTS ix_webmail_messages_outbound_message_id ON webmail_messages (outbound_message_id);
CREATE INDEX IF NOT EXISTS ix_webmail_messages_direction ON webmail_messages (direction);
CREATE INDEX IF NOT EXISTS ix_webmail_messages_folder ON webmail_messages (folder);
CREATE INDEX IF NOT EXISTS ix_webmail_messages_message_id_header ON webmail_messages (message_id_header);
CREATE INDEX IF NOT EXISTS ix_webmail_messages_is_read ON webmail_messages (is_read);
CREATE INDEX IF NOT EXISTS ix_webmail_messages_is_starred ON webmail_messages (is_starred);
CREATE INDEX IF NOT EXISTS ix_webmail_messages_delivery_status ON webmail_messages (delivery_status);
CREATE INDEX IF NOT EXISTS ix_webmail_messages_folder_time
    ON webmail_messages (mailbox_id, folder, received_at DESC, sent_at DESC)
    WHERE deleted_at IS NULL;

COMMIT;
