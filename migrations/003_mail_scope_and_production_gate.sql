BEGIN;
DO $$
BEGIN
 IF NOT EXISTS (
   SELECT 1 FROM pg_constraint
   WHERE conrelid = 'domains'::regclass
     AND conname = 'uq_domain_tenant_name'
 ) AND NOT EXISTS (
   SELECT 1 FROM pg_class
   WHERE relname = 'uq_domain_tenant_name'
     AND relnamespace = (SELECT relnamespace FROM pg_class WHERE oid = 'domains'::regclass)
 ) THEN
   ALTER TABLE domains
     ADD CONSTRAINT uq_domain_tenant_name UNIQUE (tenant_id,domain);
 END IF;
END $$;
CREATE TABLE IF NOT EXISTS allowed_senders (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL REFERENCES tenants(id), address VARCHAR NOT NULL,
 role VARCHAR NOT NULL, enabled BOOLEAN NOT NULL DEFAULT TRUE,
 CONSTRAINT uq_allowed_sender_tenant_address UNIQUE (tenant_id,address),
 CONSTRAINT ck_allowed_sender_local_part CHECK (split_part(address,'@',1) IN ('support','billing','appolon'))
);
CREATE TABLE IF NOT EXISTS inbound_route_configs (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL REFERENCES tenants(id), address VARCHAR NOT NULL,
 destination_kind VARCHAR NOT NULL, destination_ref VARCHAR, verified BOOLEAN NOT NULL DEFAULT FALSE,
 enabled BOOLEAN NOT NULL DEFAULT FALSE,
 CONSTRAINT uq_inbound_route_tenant_address UNIQUE (tenant_id,address),
 CONSTRAINT ck_inbound_route_no_catch_all CHECK (address NOT LIKE '%*%' AND address NOT LIKE '@%')
);
CREATE TABLE IF NOT EXISTS domain_campaign_mappings (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL REFERENCES tenants(id), domain VARCHAR NOT NULL,
 campaign_id VARCHAR NOT NULL, environment VARCHAR NOT NULL DEFAULT 'test', approved BOOLEAN NOT NULL DEFAULT FALSE,
 sending_enabled BOOLEAN NOT NULL DEFAULT FALSE, receiving_enabled BOOLEAN NOT NULL DEFAULT FALSE,
 first_promotion_candidate BOOLEAN NOT NULL DEFAULT FALSE, approved_by VARCHAR, approved_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CONSTRAINT uq_domain_campaign_mapping UNIQUE (tenant_id,domain,campaign_id),
 CONSTRAINT ck_domain_campaign_production_approval CHECK (environment <> 'production' OR approved)
);
CREATE INDEX IF NOT EXISTS ix_domain_campaign_mappings_tenant_campaign ON domain_campaign_mappings(tenant_id,campaign_id);
COMMIT;
