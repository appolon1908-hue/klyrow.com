BEGIN;
CREATE TABLE IF NOT EXISTS ip_pools (
 id VARCHAR PRIMARY KEY, name VARCHAR NOT NULL UNIQUE, kind VARCHAR NOT NULL,
 postal_pool_ref VARCHAR, enabled BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS ip_pool_assignments (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL REFERENCES tenants(id),
 domain VARCHAR NOT NULL, stream VARCHAR NOT NULL, pool_id VARCHAR NOT NULL REFERENCES ip_pools(id),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), CONSTRAINT uq_ip_pool_assignment UNIQUE(tenant_id,domain,stream)
);
CREATE INDEX IF NOT EXISTS ix_ip_pool_assignments_tenant_id ON ip_pool_assignments(tenant_id);
CREATE TABLE IF NOT EXISTS warmup_schedules (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL REFERENCES tenants(id), domain VARCHAR NOT NULL,
 stream VARCHAR NOT NULL, starts_at TIMESTAMPTZ NOT NULL, daily_limits_json TEXT NOT NULL,
 active BOOLEAN NOT NULL DEFAULT TRUE, CONSTRAINT uq_warmup_schedule UNIQUE(tenant_id,domain,stream)
);
CREATE INDEX IF NOT EXISTS ix_warmup_schedules_tenant_id ON warmup_schedules(tenant_id);
CREATE TABLE IF NOT EXISTS delivery_resource_suspensions (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL REFERENCES tenants(id), resource_type VARCHAR NOT NULL,
 resource_id VARCHAR NOT NULL, reason VARCHAR NOT NULL, active BOOLEAN NOT NULL DEFAULT TRUE,
 created_by VARCHAR NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CONSTRAINT uq_delivery_resource_suspension UNIQUE(tenant_id,resource_type,resource_id)
);
CREATE INDEX IF NOT EXISTS ix_delivery_resource_suspensions_tenant_id ON delivery_resource_suspensions(tenant_id);
CREATE TABLE IF NOT EXISTS abuse_alerts (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL REFERENCES tenants(id), kind VARCHAR NOT NULL,
 severity VARCHAR NOT NULL, metrics_json TEXT NOT NULL, state VARCHAR NOT NULL DEFAULT 'OPEN',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_abuse_alerts_tenant_id ON abuse_alerts(tenant_id);
COMMIT;
