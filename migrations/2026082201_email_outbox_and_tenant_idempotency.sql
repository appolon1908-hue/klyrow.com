BEGIN;

CREATE TABLE IF NOT EXISTS idempotency_keys (
  id text PRIMARY KEY,
  key text NOT NULL,
  tenant_id text NOT NULL,
  request_hash text NOT NULL,
  resource_id text NOT NULL,
  response_json text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_idempotency_tenant_key UNIQUE (tenant_id, key)
);
ALTER TABLE idempotency_keys ADD COLUMN IF NOT EXISTS id text;
UPDATE idempotency_keys
SET id = md5(tenant_id || ':' || key || ':' || created_at::text)
WHERE id IS NULL;
ALTER TABLE idempotency_keys ALTER COLUMN id SET NOT NULL;
ALTER TABLE idempotency_keys DROP CONSTRAINT IF EXISTS idempotency_keys_pkey;
ALTER TABLE idempotency_keys ADD CONSTRAINT idempotency_keys_pkey PRIMARY KEY (id);
DO $$ BEGIN
  ALTER TABLE idempotency_keys
    ADD CONSTRAINT uq_idempotency_tenant_key UNIQUE (tenant_id, key);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS email_outbox (
  id text PRIMARY KEY,
  tenant_id text NOT NULL,
  message_id text NOT NULL UNIQUE,
  payload text NOT NULL,
  state text NOT NULL DEFAULT 'pending',
  attempts integer NOT NULL DEFAULT 0,
  provider_message_id text,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT email_outbox_attempts_bounded CHECK (attempts BETWEEN 0 AND 5)
);
CREATE INDEX IF NOT EXISTS email_outbox_claim
  ON email_outbox(state, created_at)
  WHERE state IN ('pending', 'retry');

COMMIT;
