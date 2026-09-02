BEGIN;

ALTER TABLE email_outbox
  ADD COLUMN IF NOT EXISTS operation_id varchar;

ALTER TABLE email_outbox
  ADD COLUMN IF NOT EXISTS correlation_id varchar;

CREATE INDEX IF NOT EXISTS ix_email_outbox_operation_id
  ON email_outbox (operation_id);

CREATE INDEX IF NOT EXISTS ix_email_outbox_correlation_id
  ON email_outbox (correlation_id);

-- Recover linkage for reviewed command rows that predate these columns. JSON
-- parsing is guarded so malformed historical results remain visibly unlinked.
UPDATE email_outbox AS outbox
SET operation_id = operation.command_id,
    correlation_id = operation.correlation_id
FROM middleware_command_operations AS operation
WHERE operation.command = 'email.message.send.v1'
  AND CASE
    WHEN pg_input_is_valid(operation.result_json, 'jsonb')
      THEN (operation.result_json::jsonb ->> 'id') = outbox.message_id
    ELSE false
  END
  AND outbox.tenant_id = operation.tenant_id
  AND outbox.operation_id IS NULL;

COMMIT;
