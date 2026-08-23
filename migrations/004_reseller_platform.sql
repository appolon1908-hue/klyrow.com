BEGIN;
CREATE TABLE IF NOT EXISTS resellers (
 id VARCHAR PRIMARY KEY,
 tenant_id VARCHAR NOT NULL UNIQUE REFERENCES tenants(id),
 name VARCHAR NOT NULL,
 currency VARCHAR NOT NULL,
 wholesale_rate NUMERIC(18,8) NOT NULL,
 credit_limit NUMERIC(18,2) NOT NULL,
 active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_resellers_tenant_id ON resellers(tenant_id);
CREATE TABLE IF NOT EXISTS reseller_customers (
 id VARCHAR PRIMARY KEY,
 reseller_id VARCHAR NOT NULL REFERENCES resellers(id),
 customer_tenant_id VARCHAR NOT NULL UNIQUE REFERENCES tenants(id),
 retail_rate NUMERIC(18,8) NOT NULL,
 quota INTEGER NOT NULL CHECK (quota > 0),
 active BOOLEAN NOT NULL DEFAULT TRUE,
 CONSTRAINT uq_reseller_customer UNIQUE(reseller_id,customer_tenant_id)
);
CREATE INDEX IF NOT EXISTS ix_reseller_customers_reseller_id ON reseller_customers(reseller_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_reseller_customers_customer_tenant_id ON reseller_customers(customer_tenant_id);
COMMIT;
