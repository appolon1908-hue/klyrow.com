BEGIN;
CREATE TABLE IF NOT EXISTS klyrow_checkout_sessions (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, plan_id VARCHAR NOT NULL,
 price_id VARCHAR NOT NULL, provider VARCHAR NOT NULL, state VARCHAR NOT NULL,
 provider_reference VARCHAR NOT NULL UNIQUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_klyrow_checkout_sessions_tenant_id ON klyrow_checkout_sessions(tenant_id);
CREATE TABLE IF NOT EXISTS klyrow_credit_notes (
 id VARCHAR PRIMARY KEY, number VARCHAR NOT NULL UNIQUE, tenant_id VARCHAR NOT NULL,
 invoice_id VARCHAR NOT NULL, amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
 currency VARCHAR NOT NULL, reason VARCHAR NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_klyrow_credit_notes_tenant_id ON klyrow_credit_notes(tenant_id);
CREATE INDEX IF NOT EXISTS ix_klyrow_credit_notes_invoice_id ON klyrow_credit_notes(invoice_id);
COMMIT;
