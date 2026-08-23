BEGIN;
CREATE TABLE IF NOT EXISTS scoped_suppressions (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, email VARCHAR NOT NULL,
 scope VARCHAR NOT NULL, scope_id VARCHAR NOT NULL, reason VARCHAR NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CONSTRAINT uq_scoped_suppression UNIQUE(tenant_id,email,scope,scope_id)
);
CREATE INDEX IF NOT EXISTS ix_scoped_suppressions_tenant_id ON scoped_suppressions(tenant_id);
CREATE INDEX IF NOT EXISTS ix_scoped_suppressions_email ON scoped_suppressions(email);
COMMIT;
