BEGIN;

ALTER TABLE middleware_command_operations
  DROP CONSTRAINT IF EXISTS middleware_command_state_known;

ALTER TABLE middleware_command_operations
  ADD CONSTRAINT middleware_command_state_known CHECK (
    state IN (
      'accepted', 'queued', 'processing', 'submitted', 'delivered',
      'deferred', 'bounced', 'complained', 'rejected', 'failed',
      'cancelled', 'unknown_outcome', 'completed'
    )
  );

COMMIT;
