BEGIN;

CREATE TABLE IF NOT EXISTS postal_tenant_mappings (
    tenant_id VARCHAR PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    state VARCHAR NOT NULL DEFAULT 'PENDING'
        CHECK (state IN ('PENDING','RUNNING','READY','RETRYABLE_FAILURE','BLOCKED','DISABLED')),
    provider_organization_id VARCHAR,
    provider_organization_permalink VARCHAR,
    provider_server_id VARCHAR,
    provider_server_permalink VARCHAR,
    provider_mode VARCHAR NOT NULL DEFAULT 'Development'
        CHECK (provider_mode = 'Development'),
    api_key_ciphertext TEXT,
    api_key_fingerprint VARCHAR,
    last_error VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_postal_tenant_mappings_state
    ON postal_tenant_mappings (state, updated_at);

CREATE TABLE IF NOT EXISTS postal_provisioning_outbox (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key VARCHAR NOT NULL UNIQUE,
    state VARCHAR NOT NULL DEFAULT 'PENDING'
        CHECK (state IN ('PENDING','RUNNING','READY','RETRYABLE_FAILURE','BLOCKED','DISABLED')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    available_at TIMESTAMP WITH TIME ZONE NOT NULL,
    lease_owner VARCHAR,
    lease_expires_at TIMESTAMP WITH TIME ZONE,
    last_error VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_postal_provisioning_outbox_claim
    ON postal_provisioning_outbox (state, available_at, created_at);
CREATE INDEX IF NOT EXISTS ix_postal_provisioning_outbox_tenant
    ON postal_provisioning_outbox (tenant_id, created_at);

COMMIT;
