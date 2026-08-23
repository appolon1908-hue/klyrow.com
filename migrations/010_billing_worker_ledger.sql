BEGIN;
CREATE TABLE IF NOT EXISTS klyrow_billing_work_items (
 id VARCHAR PRIMARY KEY,
 billing_event_id VARCHAR NOT NULL UNIQUE,
 tenant_id VARCHAR NOT NULL,
 kind VARCHAR NOT NULL,
 state VARCHAR NOT NULL DEFAULT 'PENDING',
 attempts INTEGER NOT NULL DEFAULT 0,
 available_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
 lease_expires_at TIMESTAMPTZ NULL,
 last_error VARCHAR NULL,
 completed_at TIMESTAMPTZ NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_klyrow_billing_work_state_available ON klyrow_billing_work_items(state,available_at);
CREATE INDEX IF NOT EXISTS ix_klyrow_billing_work_tenant ON klyrow_billing_work_items(tenant_id);
COMMIT;
