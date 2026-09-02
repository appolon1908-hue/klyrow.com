BEGIN;

CREATE TABLE IF NOT EXISTS postal_domain_credentials (
    id varchar PRIMARY KEY,
    tenant_id varchar NOT NULL,
    domain varchar NOT NULL,
    state varchar NOT NULL DEFAULT 'PENDING',
    provider_server_id varchar NOT NULL,
    provider_server_permalink varchar NOT NULL,
    provider_mode varchar NOT NULL,
    api_key_ciphertext text NOT NULL,
    api_key_fingerprint varchar NOT NULL,
    last_error varchar,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_postal_domain_credential_tenant_domain UNIQUE (tenant_id, domain),
    CONSTRAINT postal_domain_credential_state_valid CHECK (state IN ('PENDING', 'READY', 'BLOCKED')),
    CONSTRAINT postal_domain_credential_mode_live CHECK (provider_mode = 'Live')
);
CREATE INDEX IF NOT EXISTS ix_postal_domain_credentials_tenant_id
    ON postal_domain_credentials (tenant_id);
CREATE INDEX IF NOT EXISTS ix_postal_domain_credentials_domain
    ON postal_domain_credentials (domain);
CREATE INDEX IF NOT EXISTS ix_postal_domain_credentials_state
    ON postal_domain_credentials (state);

COMMIT;
