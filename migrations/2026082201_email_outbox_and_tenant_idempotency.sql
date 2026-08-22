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
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'idempotency_keys'::regclass
      AND conname = 'uq_idempotency_tenant_key'
  ) AND NOT EXISTS (
    SELECT 1 FROM pg_class
    WHERE relname = 'uq_idempotency_tenant_key'
      AND relnamespace = (SELECT relnamespace FROM pg_class WHERE oid = 'idempotency_keys'::regclass)
  ) THEN
    ALTER TABLE idempotency_keys
      ADD CONSTRAINT uq_idempotency_tenant_key UNIQUE (tenant_id, key);
  END IF;
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
  next_attempt_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT email_outbox_attempts_bounded CHECK (attempts BETWEEN 0 AND 5)
);
ALTER TABLE email_outbox ADD COLUMN IF NOT EXISTS next_attempt_at timestamptz;
CREATE INDEX IF NOT EXISTS email_outbox_claim
  ON email_outbox(state, next_attempt_at, created_at)
  WHERE state IN ('pending', 'retry');

CREATE TABLE IF NOT EXISTS production_canary_gate (
  gate_key text PRIMARY KEY,
  reserved_deliveries integer NOT NULL DEFAULT 0,
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT production_canary_gate_nonnegative CHECK (reserved_deliveries >= 0)
);
INSERT INTO production_canary_gate(gate_key, reserved_deliveries)
VALUES ('klyrow-single-domain', 0)
ON CONFLICT (gate_key) DO NOTHING;

COMMIT;
