BEGIN;
CREATE TABLE IF NOT EXISTS middleware_email_command_bindings (
    id text PRIMARY KEY,
    tenant_id text NOT NULL,
    command_id text NOT NULL,
    idempotency_identity text NOT NULL UNIQUE,
    request_hash text NOT NULL,
    correlation_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_middleware_email_command_bindings_tenant_id
    ON middleware_email_command_bindings(tenant_id);
GRANT SELECT, INSERT, UPDATE, DELETE ON middleware_email_command_bindings TO klyrow_runtime;
COMMIT;
