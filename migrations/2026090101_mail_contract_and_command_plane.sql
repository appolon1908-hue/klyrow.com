BEGIN;

ALTER TABLE email_outbox
  ADD COLUMN IF NOT EXISTS priority integer NOT NULL DEFAULT 20;
ALTER TABLE email_outbox
  DROP CONSTRAINT IF EXISTS email_outbox_priority_bounded;
ALTER TABLE email_outbox
  ADD CONSTRAINT email_outbox_priority_bounded CHECK (priority BETWEEN 0 AND 1000);
CREATE INDEX IF NOT EXISTS email_outbox_priority_claim
  ON email_outbox (state, priority, next_attempt_at, created_at);

-- Existing inbound records predate authenticated SPF/DKIM/DMARC/ARC evidence.
-- Mark them explicitly unverified and quarantined; never infer a passing verdict.
ALTER TABLE provider_inbound ADD COLUMN IF NOT EXISTS auth_verdict varchar NOT NULL DEFAULT 'LEGACY_UNVERIFIED';
ALTER TABLE provider_inbound ADD COLUMN IF NOT EXISTS spf_result varchar NOT NULL DEFAULT 'NONE';
ALTER TABLE provider_inbound ADD COLUMN IF NOT EXISTS dkim_result varchar NOT NULL DEFAULT 'NONE';
ALTER TABLE provider_inbound ADD COLUMN IF NOT EXISTS dmarc_result varchar NOT NULL DEFAULT 'NONE';
ALTER TABLE provider_inbound ADD COLUMN IF NOT EXISTS arc_result varchar NOT NULL DEFAULT 'NONE';
ALTER TABLE provider_inbound ADD COLUMN IF NOT EXISTS dmarc_fail_action varchar NOT NULL DEFAULT 'QUARANTINE';
UPDATE provider_inbound
SET disposition = 'QUARANTINE'
WHERE auth_verdict = 'LEGACY_UNVERIFIED';
CREATE INDEX IF NOT EXISTS provider_inbound_auth_verdict
  ON provider_inbound (tenant_id, auth_verdict, created_at);

CREATE TABLE IF NOT EXISTS middleware_command_operations (
  command_id varchar PRIMARY KEY,
  tenant_id varchar NOT NULL,
  command varchar NOT NULL,
  idempotency_key varchar NOT NULL,
  correlation_id varchar NOT NULL,
  state varchar NOT NULL DEFAULT 'accepted',
  request_hash varchar NOT NULL,
  result_json text NOT NULL DEFAULT '{}',
  error varchar,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_middleware_command_tenant_idempotency UNIQUE (tenant_id, idempotency_key),
  CONSTRAINT middleware_command_state_known CHECK (
    state IN ('accepted', 'queued', 'completed', 'cancelled', 'failed')
  )
);
CREATE INDEX IF NOT EXISTS middleware_command_operations_tenant_state
  ON middleware_command_operations (tenant_id, state, created_at);
CREATE INDEX IF NOT EXISTS middleware_command_operations_command
  ON middleware_command_operations (command);
CREATE INDEX IF NOT EXISTS middleware_command_operations_correlation
  ON middleware_command_operations (correlation_id);

COMMIT;
