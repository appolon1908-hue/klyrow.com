BEGIN;

-- Forward-only reconciliation for provider SMTP credential columns that were
-- previously added by editing already-published migration 008. Migration 008
-- is immutable; this migration carries the later schema additions instead.
ALTER TABLE smtp_credentials
  ADD COLUMN IF NOT EXISTS allowed_senders_json text NOT NULL DEFAULT '[]';

ALTER TABLE smtp_credentials
  ADD COLUMN IF NOT EXISTS allowed_streams_json text NOT NULL DEFAULT '["TRANSACTIONAL"]';

ALTER TABLE smtp_credentials
  ADD COLUMN IF NOT EXISTS status varchar NOT NULL DEFAULT 'ACTIVE';

COMMIT;
