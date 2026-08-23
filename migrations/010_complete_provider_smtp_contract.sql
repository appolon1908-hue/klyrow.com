BEGIN;

-- Migration 000 creates the tenant credential table under the legacy
-- smtp_credentials name on fresh installs, so 004 cannot add these provider
-- relay columns with CREATE TABLE IF NOT EXISTS. Keep the already-released 008
-- checksum immutable and complete the provider contract in a new migration.
ALTER TABLE smtp_credentials ADD COLUMN IF NOT EXISTS allowed_senders_json text NOT NULL DEFAULT '[]';
ALTER TABLE smtp_credentials ADD COLUMN IF NOT EXISTS allowed_streams_json text NOT NULL DEFAULT '["TRANSACTIONAL"]';
ALTER TABLE smtp_credentials ADD COLUMN IF NOT EXISTS status varchar NOT NULL DEFAULT 'ACTIVE';

COMMIT;
