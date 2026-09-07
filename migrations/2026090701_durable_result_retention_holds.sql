BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_integration_outbox_tenant_id
    ON integration_outbox (tenant_id, id);
CREATE TABLE IF NOT EXISTS integration_result_holds (
    id text PRIMARY KEY,
    tenant_id text NOT NULL,
    outbox_id text NOT NULL,
    state text NOT NULL DEFAULT 'ACTIVE' CHECK (state IN ('ACTIVE', 'RELEASED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    released_at timestamptz,
    change_sha256 varchar(64) NOT NULL,
    release_sha256 varchar(64),
    FOREIGN KEY (tenant_id, outbox_id) REFERENCES integration_outbox (tenant_id, id)
);
CREATE INDEX IF NOT EXISTS ix_integration_result_holds_tenant_id ON integration_result_holds (tenant_id);
CREATE INDEX IF NOT EXISTS ix_integration_result_holds_outbox_id ON integration_result_holds (outbox_id);

COMMIT;
