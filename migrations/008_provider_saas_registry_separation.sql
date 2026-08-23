BEGIN;

-- Restore the governed provider tables if the one-time legacy preflight ran,
-- then create separate customer-SaaS registries. The provider relay and the
-- tenant control plane intentionally do not share ORM table contracts.
DO $$
BEGIN
  IF to_regclass('sender_identities') IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='sender_identities' AND column_name='domain_claim_id')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='sender_identities' AND column_name='domain_id') THEN
      ALTER TABLE sender_identities RENAME COLUMN domain_claim_id TO domain_id;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='sender_identities' AND column_name='address')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='sender_identities' AND column_name='email') THEN
      ALTER TABLE sender_identities RENAME COLUMN address TO email;
    END IF;
  END IF;
  IF to_regclass('smtp_credentials') IS NOT NULL
     AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='smtp_credentials' AND column_name='verifier_hash')
     AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='smtp_credentials' AND column_name='secret_hash') THEN
    ALTER TABLE smtp_credentials RENAME COLUMN verifier_hash TO secret_hash;
  END IF;
END $$;

-- 000 creates the tenant credential table under this legacy name on fresh
-- installs, so 004 cannot add the provider relay columns with CREATE IF NOT
-- EXISTS. Complete the provider contract explicitly after the rename above.
ALTER TABLE smtp_credentials ADD COLUMN IF NOT EXISTS allowed_senders_json text NOT NULL DEFAULT '[]';
ALTER TABLE smtp_credentials ADD COLUMN IF NOT EXISTS allowed_streams_json text NOT NULL DEFAULT '["TRANSACTIONAL"]';
ALTER TABLE smtp_credentials ADD COLUMN IF NOT EXISTS status varchar NOT NULL DEFAULT 'ACTIVE';

CREATE TABLE IF NOT EXISTS saas_sender_identities (
  id varchar PRIMARY KEY, tenant_id varchar NOT NULL, domain_claim_id varchar NOT NULL,
  address varchar NOT NULL, display_name varchar NOT NULL, reply_to varchar,
  stream varchar NOT NULL, status varchar NOT NULL DEFAULT 'PENDING',
  verified boolean NOT NULL DEFAULT false,
  CONSTRAINT uq_saas_sender_identity UNIQUE (tenant_id,address)
);
CREATE INDEX IF NOT EXISTS ix_saas_sender_identities_tenant_id ON saas_sender_identities(tenant_id);
CREATE INDEX IF NOT EXISTS ix_saas_sender_identities_domain_claim_id ON saas_sender_identities(domain_claim_id);
CREATE INDEX IF NOT EXISTS ix_saas_sender_identities_address ON saas_sender_identities(address);

CREATE TABLE IF NOT EXISTS tenant_smtp_credentials (
  id varchar PRIMARY KEY, tenant_id varchar NOT NULL, username varchar NOT NULL UNIQUE,
  verifier_hash varchar NOT NULL, scopes_json text NOT NULL, created_by varchar NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz,
  revoked_at timestamptz, rotated_at timestamptz
);
CREATE INDEX IF NOT EXISTS ix_tenant_smtp_credentials_tenant_id ON tenant_smtp_credentials(tenant_id);

COMMIT;
