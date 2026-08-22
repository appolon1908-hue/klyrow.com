ALTER TABLE tenant_mail_policies
  ADD COLUMN IF NOT EXISTS spam_quarantine_score INTEGER NOT NULL DEFAULT 5,
  ADD COLUMN IF NOT EXISTS spam_reject_score INTEGER NOT NULL DEFAULT 15;

CREATE TABLE IF NOT EXISTS tracking_tokens (
  id VARCHAR PRIMARY KEY,
  token_hash VARCHAR NOT NULL UNIQUE,
  tenant_id VARCHAR NOT NULL,
  message_id VARCHAR NOT NULL REFERENCES provider_messages(id),
  kind VARCHAR NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  first_seen_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_tracking_tokens_token_hash ON tracking_tokens(token_hash);
CREATE INDEX IF NOT EXISTS ix_tracking_tokens_tenant_id ON tracking_tokens(tenant_id);
CREATE INDEX IF NOT EXISTS ix_tracking_tokens_message_id ON tracking_tokens(message_id);
