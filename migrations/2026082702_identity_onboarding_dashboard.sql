BEGIN;

CREATE TABLE IF NOT EXISTS identity_profiles (
    identity_id VARCHAR PRIMARY KEY,
    email VARCHAR,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    display_name VARCHAR,
    locale VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_identity_profiles_email ON identity_profiles (email);

CREATE TABLE IF NOT EXISTS onboarding_events (
    id VARCHAR PRIMARY KEY,
    identity_id VARCHAR NOT NULL,
    tenant_id VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_onboarding_events_identity ON onboarding_events (identity_id, created_at);
CREATE INDEX IF NOT EXISTS ix_onboarding_events_tenant ON onboarding_events (tenant_id, created_at);

COMMIT;
