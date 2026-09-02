BEGIN;

ALTER TABLE middleware_command_operations
  ADD COLUMN IF NOT EXISTS request_json text NOT NULL DEFAULT '{}';

-- A command is acknowledged only after the replayable request is durable.
-- Historical rows cannot be reconstructed safely and remain terminal/read-only.
UPDATE middleware_command_operations
SET state = 'failed',
    error = COALESCE(error, 'historical_command_request_unavailable'),
    updated_at = now()
WHERE state IN ('accepted', 'processing')
  AND request_json = '{}';

COMMIT;
