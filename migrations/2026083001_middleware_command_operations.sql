BEGIN;

CREATE TABLE IF NOT EXISTS middleware_command_operations (
  command_id text PRIMARY KEY,
  tenant_id text NOT NULL,
  command text NOT NULL,
  idempotency_key text NOT NULL,
  correlation_id text NOT NULL,
  state text NOT NULL DEFAULT 'accepted',
  request_hash text NOT NULL,
  result_json text NOT NULL DEFAULT '{}',
  error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_middleware_command_tenant_idempotency UNIQUE (tenant_id, idempotency_key),
  CONSTRAINT middleware_command_state_known CHECK (
    state IN ('accepted', 'queued', 'completed', 'cancelled', 'failed')
  )
);

CREATE INDEX IF NOT EXISTS middleware_command_operations_tenant_state
  ON middleware_command_operations(tenant_id, state, created_at);

CREATE INDEX IF NOT EXISTS middleware_command_operations_command
  ON middleware_command_operations(command);

CREATE INDEX IF NOT EXISTS middleware_command_operations_correlation
  ON middleware_command_operations(correlation_id);

COMMIT;
