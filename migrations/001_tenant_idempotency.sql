BEGIN;
ALTER TABLE idempotency_keys ADD COLUMN IF NOT EXISTS id VARCHAR;
UPDATE idempotency_keys SET id = md5(tenant_id || ':' || key) WHERE id IS NULL;
ALTER TABLE idempotency_keys ALTER COLUMN id SET NOT NULL;
ALTER TABLE idempotency_keys DROP CONSTRAINT IF EXISTS idempotency_keys_pkey;
ALTER TABLE idempotency_keys ADD CONSTRAINT idempotency_keys_pkey PRIMARY KEY (id);
DO $$
BEGIN
 IF NOT EXISTS (
   SELECT 1 FROM pg_constraint
   WHERE conrelid = 'idempotency_keys'::regclass
     AND conname = 'uq_idempotency_tenant_key'
 ) THEN
   ALTER TABLE idempotency_keys
     ADD CONSTRAINT uq_idempotency_tenant_key UNIQUE (tenant_id, key);
 END IF;
END $$;
COMMIT;

-- Rollback is intentionally refused after two tenants use the same key; validate
-- uniqueness of key alone before restoring the legacy primary key.
