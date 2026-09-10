-- Tenant-scoped customer-data lifecycle contracts.
-- Rollback: stop lifecycle workers, retain completed audit rows, and only
-- remove these tables after every queued job has been reconciled/exported.
-- No table here authorizes an automatic deletion or external integration call.

CREATE TABLE IF NOT EXISTS profile_merge_audits (
    id VARCHAR NOT NULL PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    source_profile_id VARCHAR NOT NULL,
    target_profile_id VARCHAR NOT NULL,
    matched_identifiers_json TEXT NOT NULL,
    actor VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_profile_merge_audits_tenant_id ON profile_merge_audits (tenant_id);
CREATE INDEX IF NOT EXISTS ix_profile_merge_audits_source_profile_id ON profile_merge_audits (source_profile_id);
CREATE INDEX IF NOT EXISTS ix_profile_merge_audits_target_profile_id ON profile_merge_audits (target_profile_id);

CREATE TABLE IF NOT EXISTS customer_profile_import_jobs (
    id VARCHAR NOT NULL PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    requested_by VARCHAR NOT NULL,
    object_reference VARCHAR NOT NULL,
    object_sha256 VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR,
    state VARCHAR NOT NULL DEFAULT 'PENDING',
    row_count INTEGER NOT NULL DEFAULT 0,
    accepted_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    error_report_json TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_customer_profile_import_object UNIQUE (tenant_id, object_reference, object_sha256)
);
CREATE INDEX IF NOT EXISTS ix_customer_profile_import_jobs_tenant_id ON customer_profile_import_jobs (tenant_id);
CREATE INDEX IF NOT EXISTS ix_customer_profile_import_jobs_state ON customer_profile_import_jobs (state);
CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_profile_import_idempotency
    ON customer_profile_import_jobs (tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS customer_profile_export_jobs (
    id VARCHAR NOT NULL PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    requested_by VARCHAR NOT NULL,
    fields_json TEXT NOT NULL,
    filters_json TEXT NOT NULL DEFAULT '{}',
    format VARCHAR NOT NULL DEFAULT 'csv',
    idempotency_key VARCHAR,
    state VARCHAR NOT NULL DEFAULT 'PENDING',
    object_reference VARCHAR,
    expires_at TIMESTAMP WITH TIME ZONE,
    row_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_customer_profile_export_jobs_tenant_id ON customer_profile_export_jobs (tenant_id);
CREATE INDEX IF NOT EXISTS ix_customer_profile_export_jobs_state ON customer_profile_export_jobs (state);
CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_profile_export_idempotency
    ON customer_profile_export_jobs (tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS customer_data_retention (
    tenant_id VARCHAR NOT NULL PRIMARY KEY,
    profile_retention_days INTEGER NOT NULL DEFAULT 730,
    event_retention_days INTEGER NOT NULL DEFAULT 730,
    updated_by VARCHAR NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS customer_profile_deletion_jobs (
    id VARCHAR NOT NULL PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    profile_id VARCHAR NOT NULL,
    requested_by VARCHAR NOT NULL,
    reason VARCHAR NOT NULL,
    state VARCHAR NOT NULL DEFAULT 'SCHEDULED',
    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_customer_profile_deletion_jobs_tenant_id ON customer_profile_deletion_jobs (tenant_id);
CREATE INDEX IF NOT EXISTS ix_customer_profile_deletion_jobs_profile_id ON customer_profile_deletion_jobs (profile_id);
CREATE INDEX IF NOT EXISTS ix_customer_profile_deletion_jobs_state_scheduled_for
    ON customer_profile_deletion_jobs (state, scheduled_for);
