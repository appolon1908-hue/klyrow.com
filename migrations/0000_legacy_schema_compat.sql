BEGIN;

-- The production provider engine predates the customer SaaS schema. Preserve
-- those rows while normalizing the two table names/columns shared by both
-- generations before the consolidated baseline creates indexes.
DO $$
BEGIN
  IF to_regclass('sender_identities') IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='sender_identities' AND column_name='domain_id')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='sender_identities' AND column_name='domain_claim_id') THEN
      ALTER TABLE sender_identities RENAME COLUMN domain_id TO domain_claim_id;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='sender_identities' AND column_name='email')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='sender_identities' AND column_name='address') THEN
      ALTER TABLE sender_identities RENAME COLUMN email TO address;
    END IF;
    ALTER TABLE sender_identities ADD COLUMN IF NOT EXISTS verified boolean NOT NULL DEFAULT false;
    UPDATE sender_identities SET verified=true WHERE upper(status) IN ('ACTIVE','VERIFIED');
  END IF;

  IF to_regclass('smtp_credentials') IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='smtp_credentials' AND column_name='secret_hash')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='smtp_credentials' AND column_name='verifier_hash') THEN
      ALTER TABLE smtp_credentials RENAME COLUMN secret_hash TO verifier_hash;
    END IF;
    ALTER TABLE smtp_credentials
      ADD COLUMN IF NOT EXISTS scopes_json text NOT NULL DEFAULT '["smtp.send"]',
      ADD COLUMN IF NOT EXISTS created_by varchar NOT NULL DEFAULT 'legacy-migration',
      ADD COLUMN IF NOT EXISTS revoked_at timestamptz;
    ALTER TABLE smtp_credentials
      ALTER COLUMN allowed_senders_json SET DEFAULT '[]',
      ALTER COLUMN allowed_streams_json SET DEFAULT '[]',
      ALTER COLUMN status SET DEFAULT 'ACTIVE';
  END IF;
END $$;

COMMIT;
