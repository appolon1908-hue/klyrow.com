BEGIN;

CREATE TABLE IF NOT EXISTS durable_command_operations (
  id varchar PRIMARY KEY,
  tenant_id varchar NOT NULL,
  caller_identity varchar NOT NULL,
  resource varchar NOT NULL,
  action varchar NOT NULL,
  api_version varchar NOT NULL DEFAULT 'v1',
  idempotency_key varchar NOT NULL,
  semantic_sha256 varchar(64) NOT NULL,
  correlation_id varchar NOT NULL,
  state varchar NOT NULL DEFAULT 'CLAIMED',
  status_code integer,
  resource_id varchar,
  response_ciphertext text,
  error varchar,
  attempts integer NOT NULL DEFAULT 1 CHECK (attempts > 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_durable_command_identity UNIQUE (
    tenant_id,
    caller_identity,
    resource,
    action,
    api_version,
    idempotency_key
  ),
  CONSTRAINT durable_command_state_known CHECK (
    state IN ('CLAIMED', 'COMPLETED', 'RECONCILIATION_REQUIRED', 'CANCELLED')
  ),
  CONSTRAINT durable_command_completed_result CHECK (
    state <> 'COMPLETED'
    OR (status_code IS NOT NULL AND response_ciphertext IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS ix_durable_command_tenant_created
  ON durable_command_operations (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_durable_command_correlation
  ON durable_command_operations (tenant_id, correlation_id);
CREATE INDEX IF NOT EXISTS ix_durable_command_reconciliation
  ON durable_command_operations (state, updated_at)
  WHERE state IN ('CLAIMED', 'RECONCILIATION_REQUIRED');

ALTER TABLE durable_command_operations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS durable_command_tenant_isolation ON durable_command_operations;
CREATE POLICY durable_command_tenant_isolation ON durable_command_operations
  USING (tenant_id = nullif(current_setting('app.tenant_id', true), ''))
  WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), ''));

COMMIT;
