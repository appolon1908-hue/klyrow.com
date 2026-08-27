BEGIN;

CREATE TABLE IF NOT EXISTS oidc_login_transactions (
    id VARCHAR PRIMARY KEY,
    state_hash VARCHAR NOT NULL UNIQUE,
    verifier_ciphertext TEXT NOT NULL,
    nonce_ciphertext TEXT NOT NULL,
    return_url TEXT NOT NULL,
    mode VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_oidc_login_transactions_expires_at
    ON oidc_login_transactions (expires_at);

CREATE TABLE IF NOT EXISTS browser_sessions (
    id VARCHAR PRIMARY KEY,
    token_hash VARCHAR NOT NULL UNIQUE,
    csrf_hash VARCHAR NOT NULL,
    identity_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    tenant_id VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    refresh_ciphertext TEXT,
    id_token_ciphertext TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    rotated_from_id VARCHAR,
    revoked_at TIMESTAMP WITH TIME ZONE,
    user_agent_hash VARCHAR,
    ip_hash VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_browser_sessions_identity_id
    ON browser_sessions (identity_id);
CREATE INDEX IF NOT EXISTS ix_browser_sessions_user_id
    ON browser_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_browser_sessions_tenant_id
    ON browser_sessions (tenant_id);
CREATE INDEX IF NOT EXISTS ix_browser_sessions_expires_at
    ON browser_sessions (expires_at);
CREATE INDEX IF NOT EXISTS ix_browser_sessions_active_identity
    ON browser_sessions (identity_id, revoked_at, expires_at);

COMMIT;
