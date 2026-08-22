BEGIN;
CREATE TABLE IF NOT EXISTS provider_domains (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL REFERENCES tenants(id), domain VARCHAR NOT NULL UNIQUE,
 status VARCHAR NOT NULL DEFAULT 'PENDING', ownership_token VARCHAR NOT NULL, verified_at TIMESTAMPTZ,
 dkim_selector VARCHAR, dkim_key_version INTEGER NOT NULL DEFAULT 1, sending_enabled BOOLEAN NOT NULL DEFAULT FALSE,
 inbound_enabled BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_provider_domains_tenant_id ON provider_domains(tenant_id);
CREATE TABLE IF NOT EXISTS sender_identities (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL REFERENCES tenants(id), domain_id VARCHAR NOT NULL REFERENCES provider_domains(id),
 email VARCHAR NOT NULL, display_name VARCHAR, reply_to VARCHAR, stream VARCHAR NOT NULL, status VARCHAR NOT NULL DEFAULT 'PENDING',
 CONSTRAINT uq_provider_sender_tenant_email UNIQUE(tenant_id,email)
);
CREATE INDEX IF NOT EXISTS ix_sender_identities_tenant_id ON sender_identities(tenant_id);
CREATE TABLE IF NOT EXISTS tenant_mail_policies (
 tenant_id VARCHAR PRIMARY KEY REFERENCES tenants(id), sending_disabled BOOLEAN NOT NULL DEFAULT TRUE,
 sandbox_mode BOOLEAN NOT NULL DEFAULT TRUE, daily_limit INTEGER NOT NULL DEFAULT 1000, hourly_limit INTEGER NOT NULL DEFAULT 100,
 max_message_bytes INTEGER NOT NULL DEFAULT 10000000, max_attachment_bytes INTEGER NOT NULL DEFAULT 5000000,
 allowed_test_recipients_json TEXT NOT NULL DEFAULT '[]', reputation_state VARCHAR NOT NULL DEFAULT 'GOOD',
 warmup_daily_limit INTEGER NOT NULL DEFAULT 100, warmup_hourly_limit INTEGER NOT NULL DEFAULT 20,
 warmup_growth_percent INTEGER NOT NULL DEFAULT 20, ip_pool VARCHAR NOT NULL DEFAULT 'SHARED',
 tracking_mode VARCHAR NOT NULL DEFAULT 'DISABLED'
);
CREATE TABLE IF NOT EXISTS provider_messages (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL REFERENCES tenants(id), correlation_id VARCHAR NOT NULL,
 idempotency_key VARCHAR NOT NULL, request_hash VARCHAR NOT NULL, sender VARCHAR NOT NULL, recipient VARCHAR NOT NULL,
 subject VARCHAR NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}', stream VARCHAR NOT NULL, status VARCHAR NOT NULL DEFAULT 'CREATED',
 sandbox BOOLEAN NOT NULL DEFAULT TRUE, provider_message_id VARCHAR, attempts INTEGER NOT NULL DEFAULT 0,
 available_at TIMESTAMPTZ NOT NULL DEFAULT now(), lease_expires_at TIMESTAMPTZ, last_error VARCHAR,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CONSTRAINT uq_provider_message_tenant_idempotency UNIQUE(tenant_id,idempotency_key),
 CONSTRAINT uq_provider_message_tenant_correlation UNIQUE(tenant_id,correlation_id)
);
CREATE INDEX IF NOT EXISTS ix_provider_messages_status ON provider_messages(status);
CREATE TABLE IF NOT EXISTS provider_usage_events (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL REFERENCES tenants(id), message_id VARCHAR NOT NULL UNIQUE REFERENCES provider_messages(id),
 stream VARCHAR NOT NULL, billable_units INTEGER NOT NULL DEFAULT 1, result_category VARCHAR NOT NULL,
 state VARCHAR NOT NULL DEFAULT 'PENDING', attempts INTEGER NOT NULL DEFAULT 0,
 available_at TIMESTAMPTZ NOT NULL DEFAULT now(), last_error VARCHAR, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS provider_events (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, message_id VARCHAR NOT NULL, kind VARCHAR NOT NULL,
 payload_json TEXT NOT NULL, state VARCHAR NOT NULL DEFAULT 'PENDING', attempts INTEGER NOT NULL DEFAULT 0,
 available_at TIMESTAMPTZ NOT NULL DEFAULT now(), last_error VARCHAR, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sandbox_captures (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, message_id VARCHAR NOT NULL UNIQUE REFERENCES provider_messages(id),
 envelope_from VARCHAR NOT NULL, envelope_to VARCHAR NOT NULL, content_json TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS provider_inbound (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, provider_event_id VARCHAR NOT NULL, route_id VARCHAR NOT NULL,
 message_id_header VARCHAR, sender VARCHAR NOT NULL, recipient VARCHAR NOT NULL, subject VARCHAR NOT NULL,
 text_body TEXT, html_body TEXT, attachments_json TEXT NOT NULL DEFAULT '[]', disposition VARCHAR NOT NULL DEFAULT 'ACCEPT',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), CONSTRAINT uq_inbound_tenant_provider_event UNIQUE(tenant_id,provider_event_id)
);
CREATE TABLE IF NOT EXISTS smtp_credentials (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, username VARCHAR NOT NULL UNIQUE, secret_hash VARCHAR NOT NULL,
 allowed_senders_json TEXT NOT NULL, allowed_streams_json TEXT NOT NULL, status VARCHAR NOT NULL DEFAULT 'ACTIVE',
 expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), rotated_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS provider_audit (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, actor VARCHAR NOT NULL, action VARCHAR NOT NULL,
 resource_id VARCHAR, outcome VARCHAR NOT NULL, correlation_id VARCHAR, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS dkim_keys (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, domain_id VARCHAR NOT NULL REFERENCES provider_domains(id),
 selector VARCHAR NOT NULL, version INTEGER NOT NULL, public_value TEXT NOT NULL, private_secret_ref VARCHAR NOT NULL,
 status VARCHAR NOT NULL DEFAULT 'PENDING_DNS', created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 activated_at TIMESTAMPTZ, retired_at TIMESTAMPTZ, CONSTRAINT uq_dkim_domain_selector UNIQUE(domain_id,selector)
);
CREATE INDEX IF NOT EXISTS ix_dkim_keys_domain_id ON dkim_keys(domain_id);
COMMIT;
