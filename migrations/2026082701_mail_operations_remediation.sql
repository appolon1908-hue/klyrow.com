BEGIN;

CREATE TABLE IF NOT EXISTS seed_mailboxes (
    id varchar PRIMARY KEY,
    tenant_id varchar NOT NULL REFERENCES tenants(id),
    email varchar NOT NULL,
    provider varchar NOT NULL DEFAULT 'GMAIL',
    credential_secret_ref varchar NOT NULL,
    enabled boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_seed_mailbox_tenant_email UNIQUE (tenant_id, email)
);
CREATE INDEX IF NOT EXISTS ix_seed_mailboxes_tenant_id ON seed_mailboxes(tenant_id);
CREATE INDEX IF NOT EXISTS ix_seed_mailboxes_email ON seed_mailboxes(email);

CREATE TABLE IF NOT EXISTS placement_checks (
    id varchar PRIMARY KEY,
    tenant_id varchar NOT NULL REFERENCES tenants(id),
    seed_mailbox_id varchar NOT NULL REFERENCES seed_mailboxes(id),
    message_id varchar NOT NULL,
    folder varchar NOT NULL,
    opened boolean NOT NULL DEFAULT false,
    source varchar NOT NULL DEFAULT 'GMAIL_API',
    checked_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_placement_seed_message UNIQUE (seed_mailbox_id, message_id)
);
CREATE INDEX IF NOT EXISTS ix_placement_checks_tenant_id ON placement_checks(tenant_id);
CREATE INDEX IF NOT EXISTS ix_placement_checks_seed_mailbox_id ON placement_checks(seed_mailbox_id);
CREATE INDEX IF NOT EXISTS ix_placement_checks_message_id ON placement_checks(message_id);
CREATE INDEX IF NOT EXISTS ix_placement_checks_folder ON placement_checks(folder);

COMMIT;
