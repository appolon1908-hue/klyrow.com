BEGIN;

CREATE TABLE IF NOT EXISTS contact_lists (
  id varchar PRIMARY KEY,
  tenant_id varchar NOT NULL REFERENCES tenants(id),
  name varchar NOT NULL,
  description text,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_contact_list_tenant_name UNIQUE (tenant_id, name)
);

CREATE INDEX IF NOT EXISTS ix_contact_lists_tenant_id
  ON contact_lists (tenant_id, created_at DESC);

ALTER TABLE campaigns
  ADD COLUMN IF NOT EXISTS scheduled_at timestamptz;

CREATE INDEX IF NOT EXISTS ix_campaigns_tenant_schedule
  ON campaigns (tenant_id, scheduled_at)
  WHERE status = 'scheduled';

ALTER TABLE integration_outbox
  DROP CONSTRAINT IF EXISTS integration_outbox_state_known;
ALTER TABLE integration_outbox
  ADD COLUMN IF NOT EXISTS lease_expires_at timestamptz;
ALTER TABLE integration_outbox
  ADD CONSTRAINT integration_outbox_state_known CHECK (
    state IN ('PENDING', 'PROCESSING', 'COMPLETED', 'RETRY', 'DEAD_LETTER', 'CANCELLED')
  );

CREATE INDEX IF NOT EXISTS integration_outbox_operations
  ON integration_outbox (tenant_id, target, state, created_at DESC);

CREATE TABLE IF NOT EXISTS mautic_adapter_state (
  state_key varchar PRIMARY KEY,
  failure_streak integer NOT NULL DEFAULT 0 CHECK (failure_streak >= 0),
  circuit_open_until timestamptz,
  last_success_at timestamptz,
  last_failure_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMIT;
