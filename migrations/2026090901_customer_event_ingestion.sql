-- Add tenant-scoped, replay-safe customer-event ingestion metadata.
-- Rollback boundary: consumers may ignore these columns; do not remove them until
-- all writers have stopped using source/idempotency_key and retention has elapsed.
ALTER TABLE customer_events ADD COLUMN IF NOT EXISTS source VARCHAR NOT NULL DEFAULT 'api';
ALTER TABLE customer_events ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR;
ALTER TABLE customer_events ADD COLUMN IF NOT EXISTS received_at TIMESTAMP WITH TIME ZONE;

UPDATE customer_events SET received_at = occurred_at WHERE received_at IS NULL;
ALTER TABLE customer_events ALTER COLUMN received_at SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_customer_events_source ON customer_events (source);
CREATE INDEX IF NOT EXISTS ix_customer_events_received_at ON customer_events (received_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_events_tenant_source_idempotency
    ON customer_events (tenant_id, source, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
