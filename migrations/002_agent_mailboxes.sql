BEGIN;
CREATE TABLE IF NOT EXISTS campaign_email_domains (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL REFERENCES tenants(id), campaign_id VARCHAR NOT NULL,
 campaign_name VARCHAR NOT NULL, primary_domain VARCHAR NOT NULL, alias_domains TEXT NOT NULL DEFAULT '[]',
 sender_domain_verified BOOLEAN NOT NULL DEFAULT FALSE, inbound_domain_verified BOOLEAN NOT NULL DEFAULT FALSE,
 sending_enabled BOOLEAN NOT NULL DEFAULT FALSE, receiving_enabled BOOLEAN NOT NULL DEFAULT FALSE,
 human_mailbox_enabled BOOLEAN NOT NULL DEFAULT FALSE, domain_classification VARCHAR NOT NULL DEFAULT 'SYSTEM_OR_SERVICE',
 default_reply_to VARCHAR, support_address VARCHAR, billing_address VARCHAR, status VARCHAR NOT NULL DEFAULT 'pending',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), approved_by VARCHAR, approved_at TIMESTAMPTZ,
 CONSTRAINT uq_campaign_email_domain UNIQUE (tenant_id,campaign_id), CONSTRAINT uq_campaign_primary_domain_owner UNIQUE (tenant_id,primary_domain)
);
CREATE INDEX IF NOT EXISTS ix_campaign_email_domains_tenant_id ON campaign_email_domains(tenant_id);
CREATE TABLE IF NOT EXISTS agent_mailboxes (
 mailbox_id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL REFERENCES tenants(id), agent_id VARCHAR NOT NULL, employee_id VARCHAR,
 keycloak_user_id VARCHAR, odoo_user_id VARCHAR, vicidial_user_id VARCHAR, campaign_id VARCHAR NOT NULL, campaign_name VARCHAR NOT NULL,
 domain VARCHAR NOT NULL, local_part VARCHAR NOT NULL, primary_email VARCHAR NOT NULL, display_name VARCHAR NOT NULL,
 sending_enabled BOOLEAN NOT NULL DEFAULT FALSE, receiving_enabled BOOLEAN NOT NULL DEFAULT FALSE, mailbox_status VARCHAR NOT NULL DEFAULT 'PROVISIONING',
 quota INTEGER NOT NULL DEFAULT 500, rate_limit INTEGER NOT NULL DEFAULT 30, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), activated_at TIMESTAMPTZ,
 suspended_at TIMESTAMPTZ, deactivated_at TIMESTAMPTZ, last_send_at TIMESTAMPTZ, last_receive_at TIMESTAMPTZ,
 provisioning_correlation_id VARCHAR NOT NULL, provisioning_error VARCHAR, audit_version INTEGER NOT NULL DEFAULT 1,
 outbound_validated BOOLEAN NOT NULL DEFAULT FALSE, inbound_validated BOOLEAN NOT NULL DEFAULT FALSE,
 CONSTRAINT uq_agent_mailbox_address UNIQUE (tenant_id,domain,local_part),
 CONSTRAINT uq_agent_mailbox_assignment UNIQUE (tenant_id,agent_id,campaign_id)
);
CREATE INDEX IF NOT EXISTS ix_agent_mailboxes_tenant_campaign ON agent_mailboxes(tenant_id,campaign_id);
CREATE INDEX IF NOT EXISTS ix_agent_mailboxes_tenant_email ON agent_mailboxes(tenant_id,primary_email);
CREATE TABLE IF NOT EXISTS agent_mailbox_audit (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, mailbox_id VARCHAR, agent_id VARCHAR NOT NULL, campaign_id VARCHAR NOT NULL,
 action VARCHAR NOT NULL, correlation_id VARCHAR NOT NULL, detail TEXT NOT NULL DEFAULT '{}', created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_agent_mailbox_audit_tenant_mailbox ON agent_mailbox_audit(tenant_id,mailbox_id);
CREATE TABLE IF NOT EXISTS agent_mailbox_inbound_routes (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, campaign_id VARCHAR NOT NULL, mailbox_id VARCHAR NOT NULL,
 recipient VARCHAR NOT NULL, enabled BOOLEAN NOT NULL DEFAULT FALSE, provider_route_id VARCHAR, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CONSTRAINT uq_agent_inbound_recipient UNIQUE (tenant_id,recipient), CHECK (recipient NOT LIKE '@%' AND recipient NOT LIKE '%*%')
);
CREATE TABLE IF NOT EXISTS agent_outbound_sender_authorizations (
 id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, campaign_id VARCHAR NOT NULL, mailbox_id VARCHAR NOT NULL, agent_id VARCHAR NOT NULL,
 sender VARCHAR NOT NULL, enabled BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CONSTRAINT uq_agent_outbound_sender UNIQUE (tenant_id,sender)
);
COMMIT;

-- Rollback is evidence-preserving: disable mailboxes first. Destructive DROP
-- statements are intentionally omitted from automated rollback.
