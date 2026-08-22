BEGIN;

CREATE TABLE IF NOT EXISTS tenants (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	quota INTEGER NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS webhook_replays (
	id VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS postal_events (
	id VARCHAR NOT NULL, 
	event_type VARCHAR NOT NULL, 
	correlation_id VARCHAR NOT NULL, 
	message_id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	payload TEXT NOT NULL, 
	state VARCHAR NOT NULL, 
	attempts INTEGER NOT NULL, 
	last_error VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_postal_events_state ON postal_events (state);

CREATE INDEX IF NOT EXISTS ix_postal_events_correlation_id ON postal_events (correlation_id);

CREATE INDEX IF NOT EXISTS ix_postal_events_event_type ON postal_events (event_type);

CREATE INDEX IF NOT EXISTS ix_postal_events_message_id ON postal_events (message_id);

CREATE INDEX IF NOT EXISTS ix_postal_events_tenant_id ON postal_events (tenant_id);

CREATE TABLE IF NOT EXISTS audit_log (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	actor VARCHAR NOT NULL, 
	action VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_audit_log_tenant_id ON audit_log (tenant_id);

CREATE TABLE IF NOT EXISTS idempotency_keys (
	id VARCHAR NOT NULL, 
	key VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	request_hash VARCHAR NOT NULL, 
	resource_id VARCHAR NOT NULL, 
	response_json TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_idempotency_tenant_key UNIQUE (tenant_id, key)
);

CREATE INDEX IF NOT EXISTS ix_idempotency_keys_tenant_id ON idempotency_keys (tenant_id);

CREATE TABLE IF NOT EXISTS email_outbox (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	message_id VARCHAR NOT NULL, 
	payload TEXT NOT NULL, 
	state VARCHAR NOT NULL, 
	attempts INTEGER NOT NULL, 
	provider_message_id VARCHAR, 
	last_error VARCHAR, 
	next_attempt_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_email_outbox_message_id ON email_outbox (message_id);

CREATE INDEX IF NOT EXISTS ix_email_outbox_state ON email_outbox (state);

CREATE INDEX IF NOT EXISTS ix_email_outbox_tenant_id ON email_outbox (tenant_id);

CREATE TABLE IF NOT EXISTS production_canary_gate (
	gate_key VARCHAR NOT NULL, 
	reserved_deliveries INTEGER NOT NULL, 
	claimed_deliveries INTEGER NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (gate_key)
);

CREATE TABLE IF NOT EXISTS segment_audit (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	segment_id VARCHAR NOT NULL, 
	revision INTEGER NOT NULL, 
	rules_json TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_segment_audit_segment_id ON segment_audit (segment_id);

CREATE INDEX IF NOT EXISTS ix_segment_audit_tenant_id ON segment_audit (tenant_id);

CREATE TABLE IF NOT EXISTS journey_versions (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	journey_id VARCHAR NOT NULL, 
	version INTEGER NOT NULL, 
	graph_json TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_journey_versions_tenant_id ON journey_versions (tenant_id);

CREATE INDEX IF NOT EXISTS ix_journey_versions_journey_id ON journey_versions (journey_id);

CREATE TABLE IF NOT EXISTS journey_runs (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	journey_id VARCHAR NOT NULL, 
	profile_id VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	current_node VARCHAR, 
	history_json TEXT NOT NULL, 
	converted BOOLEAN NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_journey_runs_journey_id ON journey_runs (journey_id);

CREATE INDEX IF NOT EXISTS ix_journey_runs_tenant_id ON journey_runs (tenant_id);

CREATE INDEX IF NOT EXISTS ix_journey_runs_profile_id ON journey_runs (profile_id);

CREATE TABLE IF NOT EXISTS sessions (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	revoked BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_sessions_user_id ON sessions (user_id);

CREATE INDEX IF NOT EXISTS ix_sessions_tenant_id ON sessions (tenant_id);

CREATE TABLE IF NOT EXISTS deliverability_snapshots (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	domain_id VARCHAR NOT NULL, 
	spf BOOLEAN NOT NULL, 
	dkim BOOLEAN NOT NULL, 
	dmarc BOOLEAN NOT NULL, 
	mx BOOLEAN NOT NULL, 
	ptr BOOLEAN NOT NULL, 
	tls BOOLEAN NOT NULL, 
	details_json TEXT NOT NULL, 
	checked_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_deliverability_snapshots_domain_id ON deliverability_snapshots (domain_id);

CREATE INDEX IF NOT EXISTS ix_deliverability_snapshots_tenant_id ON deliverability_snapshots (tenant_id);

CREATE TABLE IF NOT EXISTS experiments (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	variants_json TEXT NOT NULL, 
	metric VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_experiments_tenant_id ON experiments (tenant_id);

CREATE TABLE IF NOT EXISTS experiment_assignments (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	experiment_id VARCHAR NOT NULL, 
	profile_id VARCHAR NOT NULL, 
	variant VARCHAR NOT NULL, 
	converted BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_experiment_assignments_profile_id ON experiment_assignments (profile_id);

CREATE INDEX IF NOT EXISTS ix_experiment_assignments_tenant_id ON experiment_assignments (tenant_id);

CREATE INDEX IF NOT EXISTS ix_experiment_assignments_experiment_id ON experiment_assignments (experiment_id);

CREATE TABLE IF NOT EXISTS integrations (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	kind VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	config_json TEXT NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_integrations_tenant_id ON integrations (tenant_id);

CREATE TABLE IF NOT EXISTS plans (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	messages INTEGER NOT NULL, 
	profiles INTEGER NOT NULL, 
	seats INTEGER NOT NULL, 
	api_per_minute INTEGER NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
	tenant_id VARCHAR NOT NULL, 
	plan_id VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	provider VARCHAR, 
	external_ref VARCHAR, 
	PRIMARY KEY (tenant_id)
);

CREATE TABLE IF NOT EXISTS usage_ledger (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	kind VARCHAR NOT NULL, 
	quantity INTEGER NOT NULL, 
	reference VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_usage_ledger_tenant_id ON usage_ledger (tenant_id);

CREATE TABLE IF NOT EXISTS agent_mailbox_audit (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	mailbox_id VARCHAR, 
	agent_id VARCHAR NOT NULL, 
	campaign_id VARCHAR NOT NULL, 
	action VARCHAR NOT NULL, 
	correlation_id VARCHAR NOT NULL, 
	detail TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_agent_mailbox_audit_tenant_id ON agent_mailbox_audit (tenant_id);

CREATE INDEX IF NOT EXISTS ix_agent_mailbox_audit_mailbox_id ON agent_mailbox_audit (mailbox_id);

CREATE INDEX IF NOT EXISTS ix_agent_mailbox_audit_agent_id ON agent_mailbox_audit (agent_id);

CREATE INDEX IF NOT EXISTS ix_agent_mailbox_audit_correlation_id ON agent_mailbox_audit (correlation_id);

CREATE INDEX IF NOT EXISTS ix_agent_mailbox_audit_campaign_id ON agent_mailbox_audit (campaign_id);

CREATE TABLE IF NOT EXISTS agent_mailbox_inbound_routes (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	campaign_id VARCHAR NOT NULL, 
	mailbox_id VARCHAR NOT NULL, 
	recipient VARCHAR NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	provider_route_id VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_agent_inbound_recipient UNIQUE (tenant_id, recipient)
);

CREATE INDEX IF NOT EXISTS ix_agent_mailbox_inbound_routes_tenant_id ON agent_mailbox_inbound_routes (tenant_id);

CREATE INDEX IF NOT EXISTS ix_agent_mailbox_inbound_routes_campaign_id ON agent_mailbox_inbound_routes (campaign_id);

CREATE INDEX IF NOT EXISTS ix_agent_mailbox_inbound_routes_mailbox_id ON agent_mailbox_inbound_routes (mailbox_id);

CREATE TABLE IF NOT EXISTS agent_outbound_sender_authorizations (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	campaign_id VARCHAR NOT NULL, 
	mailbox_id VARCHAR NOT NULL, 
	agent_id VARCHAR NOT NULL, 
	sender VARCHAR NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_agent_outbound_sender UNIQUE (tenant_id, sender)
);

CREATE INDEX IF NOT EXISTS ix_agent_outbound_sender_authorizations_mailbox_id ON agent_outbound_sender_authorizations (mailbox_id);

CREATE INDEX IF NOT EXISTS ix_agent_outbound_sender_authorizations_agent_id ON agent_outbound_sender_authorizations (agent_id);

CREATE INDEX IF NOT EXISTS ix_agent_outbound_sender_authorizations_campaign_id ON agent_outbound_sender_authorizations (campaign_id);

CREATE INDEX IF NOT EXISTS ix_agent_outbound_sender_authorizations_tenant_id ON agent_outbound_sender_authorizations (tenant_id);

CREATE TABLE IF NOT EXISTS klyrow_products (
	id VARCHAR NOT NULL, 
	code VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE IF NOT EXISTS klyrow_usage_events (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	subscription_id VARCHAR NOT NULL, 
	message_id VARCHAR, 
	event_key VARCHAR NOT NULL, 
	unit VARCHAR NOT NULL, 
	quantity INTEGER NOT NULL, 
	price_id VARCHAR NOT NULL, 
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_klyrow_usage_event UNIQUE (tenant_id, event_key)
);

CREATE INDEX IF NOT EXISTS ix_klyrow_usage_events_subscription_id ON klyrow_usage_events (subscription_id);

CREATE INDEX IF NOT EXISTS ix_klyrow_usage_events_tenant_id ON klyrow_usage_events (tenant_id);

CREATE TABLE IF NOT EXISTS klyrow_invoices (
	id VARCHAR NOT NULL, 
	number VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	subscription_id VARCHAR NOT NULL, 
	currency VARCHAR NOT NULL, 
	subtotal NUMERIC(18, 2) NOT NULL, 
	tax NUMERIC(18, 2) NOT NULL, 
	discount NUMERIC(18, 2) NOT NULL, 
	credits NUMERIC(18, 2) NOT NULL, 
	total NUMERIC(18, 2) NOT NULL, 
	status VARCHAR NOT NULL, 
	due_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	evidence_json TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (number)
);

CREATE INDEX IF NOT EXISTS ix_klyrow_invoices_tenant_id ON klyrow_invoices (tenant_id);

CREATE TABLE IF NOT EXISTS klyrow_invoice_lines (
	id VARCHAR NOT NULL, 
	invoice_id VARCHAR NOT NULL, 
	kind VARCHAR NOT NULL, 
	description VARCHAR NOT NULL, 
	quantity INTEGER NOT NULL, 
	unit_amount NUMERIC(18, 8) NOT NULL, 
	amount NUMERIC(18, 2) NOT NULL, 
	reference VARCHAR, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_klyrow_invoice_line_reference UNIQUE (invoice_id, kind, reference)
);

CREATE INDEX IF NOT EXISTS ix_klyrow_invoice_lines_invoice_id ON klyrow_invoice_lines (invoice_id);

CREATE TABLE IF NOT EXISTS klyrow_payment_method_references (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	provider VARCHAR NOT NULL, 
	provider_reference VARCHAR NOT NULL, 
	label VARCHAR NOT NULL, 
	is_default BOOLEAN NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_klyrow_payment_method_references_tenant_id ON klyrow_payment_method_references (tenant_id);

CREATE TABLE IF NOT EXISTS klyrow_payments (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	invoice_id VARCHAR NOT NULL, 
	provider VARCHAR NOT NULL, 
	provider_reference VARCHAR NOT NULL, 
	amount NUMERIC(18, 2) NOT NULL, 
	currency VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	confirmed_by VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_klyrow_payment_provider_ref UNIQUE (provider, provider_reference)
);

CREATE INDEX IF NOT EXISTS ix_klyrow_payments_invoice_id ON klyrow_payments (invoice_id);

CREATE INDEX IF NOT EXISTS ix_klyrow_payments_tenant_id ON klyrow_payments (tenant_id);

CREATE TABLE IF NOT EXISTS klyrow_credits (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	invoice_id VARCHAR, 
	amount NUMERIC(18, 2) NOT NULL, 
	currency VARCHAR NOT NULL, 
	reason VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_klyrow_credits_tenant_id ON klyrow_credits (tenant_id);

CREATE TABLE IF NOT EXISTS klyrow_refunds (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	payment_id VARCHAR NOT NULL, 
	amount NUMERIC(18, 2) NOT NULL, 
	status VARCHAR NOT NULL, 
	provider_reference VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (provider_reference)
);

CREATE INDEX IF NOT EXISTS ix_klyrow_refunds_tenant_id ON klyrow_refunds (tenant_id);

CREATE INDEX IF NOT EXISTS ix_klyrow_refunds_payment_id ON klyrow_refunds (payment_id);

CREATE TABLE IF NOT EXISTS klyrow_wallets (
	tenant_id VARCHAR NOT NULL, 
	currency VARCHAR NOT NULL, 
	balance NUMERIC(18, 2) NOT NULL, 
	version INTEGER NOT NULL, 
	PRIMARY KEY (tenant_id)
);

CREATE TABLE IF NOT EXISTS klyrow_wallet_transactions (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	kind VARCHAR NOT NULL, 
	amount NUMERIC(18, 2) NOT NULL, 
	currency VARCHAR NOT NULL, 
	reference VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_klyrow_wallet_reference UNIQUE (tenant_id, reference)
);

CREATE INDEX IF NOT EXISTS ix_klyrow_wallet_transactions_tenant_id ON klyrow_wallet_transactions (tenant_id);

CREATE TABLE IF NOT EXISTS klyrow_tax_rules (
	id VARCHAR NOT NULL, 
	jurisdiction VARCHAR NOT NULL, 
	mode VARCHAR NOT NULL, 
	rate NUMERIC(8, 6) NOT NULL, 
	evidence_label VARCHAR NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS klyrow_billing_events (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	kind VARCHAR NOT NULL, 
	reference VARCHAR NOT NULL, 
	payload_json TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_klyrow_billing_events_reference ON klyrow_billing_events (reference);

CREATE INDEX IF NOT EXISTS ix_klyrow_billing_events_tenant_id ON klyrow_billing_events (tenant_id);

CREATE TABLE IF NOT EXISTS tenant_members (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_tenant_member UNIQUE (tenant_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_tenant_members_tenant_id ON tenant_members (tenant_id);

CREATE INDEX IF NOT EXISTS ix_tenant_members_user_id ON tenant_members (user_id);

CREATE TABLE IF NOT EXISTS tenant_invitations (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	token_hash VARCHAR NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	accepted_at TIMESTAMP WITH TIME ZONE, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	created_by VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (token_hash)
);

CREATE INDEX IF NOT EXISTS ix_tenant_invitations_email ON tenant_invitations (email);

CREATE INDEX IF NOT EXISTS ix_tenant_invitations_tenant_id ON tenant_invitations (tenant_id);

CREATE TABLE IF NOT EXISTS tenant_settings (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	key VARCHAR NOT NULL, 
	value_json TEXT NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_tenant_setting UNIQUE (tenant_id, key)
);

CREATE INDEX IF NOT EXISTS ix_tenant_settings_tenant_id ON tenant_settings (tenant_id);

CREATE TABLE IF NOT EXISTS tenant_features (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	key VARCHAR NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	source VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_tenant_feature UNIQUE (tenant_id, key)
);

CREATE INDEX IF NOT EXISTS ix_tenant_features_tenant_id ON tenant_features (tenant_id);

CREATE TABLE IF NOT EXISTS tenant_limits (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	key VARCHAR NOT NULL, 
	value INTEGER NOT NULL, 
	source VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_tenant_limit UNIQUE (tenant_id, key)
);

CREATE INDEX IF NOT EXISTS ix_tenant_limits_tenant_id ON tenant_limits (tenant_id);

CREATE TABLE IF NOT EXISTS service_accounts (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	client_id VARCHAR NOT NULL, 
	secret_hash VARCHAR NOT NULL, 
	scopes_json TEXT NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	rotated_at TIMESTAMP WITH TIME ZONE, 
	created_by VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (client_id)
);

CREATE INDEX IF NOT EXISTS ix_service_accounts_tenant_id ON service_accounts (tenant_id);

CREATE TABLE IF NOT EXISTS scoped_api_keys (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	prefix VARCHAR NOT NULL, 
	verifier_hash VARCHAR NOT NULL, 
	scopes_json TEXT NOT NULL, 
	environment VARCHAR NOT NULL, 
	ip_allowlist_json TEXT NOT NULL, 
	created_by VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_used_at TIMESTAMP WITH TIME ZONE, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (verifier_hash)
);

CREATE INDEX IF NOT EXISTS ix_scoped_api_keys_prefix ON scoped_api_keys (prefix);

CREATE INDEX IF NOT EXISTS ix_scoped_api_keys_tenant_id ON scoped_api_keys (tenant_id);

CREATE TABLE IF NOT EXISTS smtp_credentials (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	username VARCHAR NOT NULL, 
	verifier_hash VARCHAR NOT NULL, 
	scopes_json TEXT NOT NULL, 
	created_by VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	rotated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (username)
);

CREATE INDEX IF NOT EXISTS ix_smtp_credentials_tenant_id ON smtp_credentials (tenant_id);

CREATE TABLE IF NOT EXISTS oidc_identities (
	id VARCHAR NOT NULL, 
	issuer VARCHAR NOT NULL, 
	subject VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	default_tenant_id VARCHAR, 
	identity_type VARCHAR NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_oidc_issuer_subject UNIQUE (issuer, subject)
);

CREATE INDEX IF NOT EXISTS ix_oidc_identities_issuer ON oidc_identities (issuer);

CREATE INDEX IF NOT EXISTS ix_oidc_identities_subject ON oidc_identities (subject);

CREATE INDEX IF NOT EXISTS ix_oidc_identities_user_id ON oidc_identities (user_id);

CREATE TABLE IF NOT EXISTS domain_claims (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	domain VARCHAR NOT NULL, 
	state VARCHAR NOT NULL, 
	challenge_hash VARCHAR NOT NULL, 
	dkim_selector VARCHAR NOT NULL, 
	dkim_version INTEGER NOT NULL, 
	return_path VARCHAR NOT NULL, 
	tracking_domain VARCHAR NOT NULL, 
	verified_at TIMESTAMP WITH TIME ZONE, 
	suspended_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_domain_claims_domain ON domain_claims (domain);

CREATE INDEX IF NOT EXISTS ix_domain_claims_tenant_id ON domain_claims (tenant_id);

CREATE TABLE IF NOT EXISTS dkim_key_versions (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	domain_claim_id VARCHAR NOT NULL, 
	selector VARCHAR NOT NULL, 
	version INTEGER NOT NULL, 
	public_key TEXT NOT NULL, 
	private_key_reference VARCHAR NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	retired_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_dkim_domain_version UNIQUE (domain_claim_id, version)
);

CREATE INDEX IF NOT EXISTS ix_dkim_key_versions_tenant_id ON dkim_key_versions (tenant_id);

CREATE INDEX IF NOT EXISTS ix_dkim_key_versions_domain_claim_id ON dkim_key_versions (domain_claim_id);

CREATE TABLE IF NOT EXISTS sender_identities (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	domain_claim_id VARCHAR NOT NULL, 
	address VARCHAR NOT NULL, 
	display_name VARCHAR NOT NULL, 
	reply_to VARCHAR, 
	stream VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	verified BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_sender_identity UNIQUE (tenant_id, address)
);

CREATE INDEX IF NOT EXISTS ix_sender_identities_tenant_id ON sender_identities (tenant_id);

CREATE INDEX IF NOT EXISTS ix_sender_identities_domain_claim_id ON sender_identities (domain_claim_id);

CREATE INDEX IF NOT EXISTS ix_sender_identities_address ON sender_identities (address);

CREATE TABLE IF NOT EXISTS message_streams (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	kind VARCHAR NOT NULL, 
	rate_limit INTEGER NOT NULL, 
	retention_days INTEGER NOT NULL, 
	tracking_enabled BOOLEAN NOT NULL, 
	suppression_policy VARCHAR NOT NULL, 
	reputation_state VARCHAR NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_message_stream UNIQUE (tenant_id, name)
);

CREATE INDEX IF NOT EXISTS ix_message_streams_tenant_id ON message_streams (tenant_id);

CREATE TABLE IF NOT EXISTS templates (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	slug VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	current_version INTEGER NOT NULL, 
	locale VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_template_slug UNIQUE (tenant_id, slug)
);

CREATE INDEX IF NOT EXISTS ix_templates_tenant_id ON templates (tenant_id);

CREATE TABLE IF NOT EXISTS template_versions (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	template_id VARCHAR NOT NULL, 
	version INTEGER NOT NULL, 
	subject VARCHAR NOT NULL, 
	html_body TEXT NOT NULL, 
	text_body TEXT NOT NULL, 
	variables_json TEXT NOT NULL, 
	created_by VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_template_version UNIQUE (template_id, version)
);

CREATE INDEX IF NOT EXISTS ix_template_versions_tenant_id ON template_versions (tenant_id);

CREATE INDEX IF NOT EXISTS ix_template_versions_template_id ON template_versions (template_id);

CREATE TABLE IF NOT EXISTS campaign_definitions (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	sender_id VARCHAR NOT NULL, 
	template_id VARCHAR NOT NULL, 
	segment_id VARCHAR, 
	status VARCHAR NOT NULL, 
	timezone VARCHAR NOT NULL, 
	scheduled_at TIMESTAMP WITH TIME ZONE, 
	frequency_cap INTEGER NOT NULL, 
	tracking_json TEXT NOT NULL, 
	test_sent_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_campaign_definitions_tenant_id ON campaign_definitions (tenant_id);

CREATE TABLE IF NOT EXISTS inbound_routes (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	domain_claim_id VARCHAR NOT NULL, 
	recipient VARCHAR NOT NULL, 
	wildcard BOOLEAN NOT NULL, 
	destination_kind VARCHAR NOT NULL, 
	destination_ref VARCHAR NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	max_bytes INTEGER NOT NULL, 
	malware_scan_required BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_inbound_route_recipient UNIQUE (domain_claim_id, recipient)
);

CREATE INDEX IF NOT EXISTS ix_inbound_routes_recipient ON inbound_routes (recipient);

CREATE INDEX IF NOT EXISTS ix_inbound_routes_domain_claim_id ON inbound_routes (domain_claim_id);

CREATE INDEX IF NOT EXISTS ix_inbound_routes_tenant_id ON inbound_routes (tenant_id);

CREATE TABLE IF NOT EXISTS inbound_messages (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	route_id VARCHAR NOT NULL, 
	message_id VARCHAR NOT NULL, 
	sender VARCHAR NOT NULL, 
	recipient VARCHAR NOT NULL, 
	in_reply_to VARCHAR, 
	references_json TEXT NOT NULL, 
	headers_json TEXT NOT NULL, 
	attachment_manifest_json TEXT NOT NULL, 
	spam_score INTEGER NOT NULL, 
	malware_status VARCHAR NOT NULL, 
	state VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_inbound_message_id UNIQUE (tenant_id, message_id)
);

CREATE INDEX IF NOT EXISTS ix_inbound_messages_tenant_id ON inbound_messages (tenant_id);

CREATE INDEX IF NOT EXISTS ix_inbound_messages_route_id ON inbound_messages (route_id);

CREATE TABLE IF NOT EXISTS webhook_subscriptions (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	url VARCHAR NOT NULL, 
	events_json TEXT NOT NULL, 
	secret_hash VARCHAR NOT NULL, 
	encrypted_secret_ref VARCHAR NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	rotated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_webhook_subscriptions_tenant_id ON webhook_subscriptions (tenant_id);

CREATE TABLE IF NOT EXISTS webhook_attempts (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	subscription_id VARCHAR NOT NULL, 
	event_id VARCHAR NOT NULL, 
	event_type VARCHAR NOT NULL, 
	state VARCHAR NOT NULL, 
	attempts INTEGER NOT NULL, 
	next_attempt_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_status INTEGER, 
	last_error VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_webhook_attempt_event UNIQUE (subscription_id, event_id)
);

CREATE INDEX IF NOT EXISTS ix_webhook_attempts_tenant_id ON webhook_attempts (tenant_id);

CREATE INDEX IF NOT EXISTS ix_webhook_attempts_event_id ON webhook_attempts (event_id);

CREATE INDEX IF NOT EXISTS ix_webhook_attempts_subscription_id ON webhook_attempts (subscription_id);

CREATE TABLE IF NOT EXISTS delivery_jobs (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	message_id VARCHAR NOT NULL, 
	state VARCHAR NOT NULL, 
	attempts INTEGER NOT NULL, 
	lease_owner VARCHAR, 
	lease_expires_at TIMESTAMP WITH TIME ZONE, 
	next_attempt_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	error_class VARCHAR, 
	dead_lettered_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_delivery_jobs_message_id ON delivery_jobs (message_id);

CREATE INDEX IF NOT EXISTS ix_delivery_jobs_tenant_id ON delivery_jobs (tenant_id);

CREATE TABLE IF NOT EXISTS reputation_snapshots (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	domain_claim_id VARCHAR, 
	stream_id VARCHAR, 
	sent INTEGER NOT NULL, 
	delivered INTEGER NOT NULL, 
	hard_bounces INTEGER NOT NULL, 
	complaints INTEGER NOT NULL, 
	invalid INTEGER NOT NULL, 
	state VARCHAR NOT NULL, 
	measured_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_reputation_snapshots_tenant_id ON reputation_snapshots (tenant_id);

CREATE TABLE IF NOT EXISTS integration_outbox (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	target VARCHAR NOT NULL, 
	event_type VARCHAR NOT NULL, 
	aggregate_id VARCHAR NOT NULL, 
	payload_json TEXT NOT NULL, 
	idempotency_key VARCHAR NOT NULL, 
	state VARCHAR NOT NULL, 
	attempts INTEGER NOT NULL, 
	next_attempt_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_error VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_integration_outbox_key UNIQUE (tenant_id, target, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_integration_outbox_state ON integration_outbox (state);

CREATE INDEX IF NOT EXISTS ix_integration_outbox_target ON integration_outbox (target);

CREATE INDEX IF NOT EXISTS ix_integration_outbox_event_type ON integration_outbox (event_type);

CREATE INDEX IF NOT EXISTS ix_integration_outbox_aggregate_id ON integration_outbox (aggregate_id);

CREATE INDEX IF NOT EXISTS ix_integration_outbox_tenant_id ON integration_outbox (tenant_id);

CREATE TABLE IF NOT EXISTS integration_results (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	outbox_id VARCHAR NOT NULL, 
	source VARCHAR NOT NULL, 
	result_key VARCHAR NOT NULL, 
	payload_json TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (result_key)
);

CREATE INDEX IF NOT EXISTS ix_integration_results_tenant_id ON integration_results (tenant_id);

CREATE INDEX IF NOT EXISTS ix_integration_results_outbox_id ON integration_results (outbox_id);

CREATE TABLE IF NOT EXISTS support_tickets (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	created_by VARCHAR NOT NULL, 
	category VARCHAR NOT NULL, 
	subject VARCHAR NOT NULL, 
	description TEXT NOT NULL, 
	status VARCHAR NOT NULL, 
	priority VARCHAR NOT NULL, 
	odoo_reference VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_support_tickets_tenant_id ON support_tickets (tenant_id);

CREATE TABLE IF NOT EXISTS tenant_export_jobs (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	requested_by VARCHAR NOT NULL, 
	scope_json TEXT NOT NULL, 
	state VARCHAR NOT NULL, 
	object_reference VARCHAR, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_tenant_export_jobs_tenant_id ON tenant_export_jobs (tenant_id);

CREATE TABLE IF NOT EXISTS account_closures (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	requested_by VARCHAR NOT NULL, 
	state VARCHAR NOT NULL, 
	confirmation_hash VARCHAR NOT NULL, 
	grace_until TIMESTAMP WITH TIME ZONE NOT NULL, 
	billing_settled BOOLEAN NOT NULL, 
	retention_policy VARCHAR NOT NULL, 
	confirmed_at TIMESTAMP WITH TIME ZONE, 
	closed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_account_closures_tenant_id ON account_closures (tenant_id);

CREATE TABLE IF NOT EXISTS tenant_send_gates (
	tenant_id VARCHAR NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	reason VARCHAR NOT NULL, 
	updated_by VARCHAR NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (tenant_id)
);

CREATE TABLE IF NOT EXISTS reconciliation_runs (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR, 
	kind VARCHAR NOT NULL, 
	state VARCHAR NOT NULL, 
	drift_count INTEGER NOT NULL, 
	details_json TEXT NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_reconciliation_runs_tenant_id ON reconciliation_runs (tenant_id);

CREATE TABLE IF NOT EXISTS users (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	password_hash VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	reset_hash VARCHAR, 
	reset_expires TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

CREATE TABLE IF NOT EXISTS api_keys (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	key_hash VARCHAR NOT NULL, 
	revoked BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	UNIQUE (key_hash)
);

CREATE INDEX IF NOT EXISTS ix_api_keys_tenant_id ON api_keys (tenant_id);

CREATE TABLE IF NOT EXISTS domains (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	domain VARCHAR NOT NULL, 
	token VARCHAR NOT NULL, 
	verified BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_domain_tenant_name UNIQUE (tenant_id, domain), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_domains_tenant_id ON domains (tenant_id);

CREATE TABLE IF NOT EXISTS allowed_senders (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	address VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_allowed_sender_tenant_address UNIQUE (tenant_id, address), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_allowed_senders_tenant_id ON allowed_senders (tenant_id);

CREATE INDEX IF NOT EXISTS ix_allowed_senders_address ON allowed_senders (address);

CREATE TABLE IF NOT EXISTS inbound_route_configs (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	address VARCHAR NOT NULL, 
	destination_kind VARCHAR NOT NULL, 
	destination_ref VARCHAR, 
	verified BOOLEAN NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_inbound_route_tenant_address UNIQUE (tenant_id, address), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_inbound_route_configs_address ON inbound_route_configs (address);

CREATE INDEX IF NOT EXISTS ix_inbound_route_configs_tenant_id ON inbound_route_configs (tenant_id);

CREATE TABLE IF NOT EXISTS messages (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	recipient VARCHAR NOT NULL, 
	sender VARCHAR NOT NULL, 
	subject VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_messages_tenant_id ON messages (tenant_id);

CREATE TABLE IF NOT EXISTS events (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	message_id VARCHAR NOT NULL, 
	kind VARCHAR NOT NULL, 
	payload TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_events_message_id ON events (message_id);

CREATE INDEX IF NOT EXISTS ix_events_tenant_id ON events (tenant_id);

CREATE TABLE IF NOT EXISTS suppressions (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	reason VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_suppressions_email ON suppressions (email);

CREATE INDEX IF NOT EXISTS ix_suppressions_tenant_id ON suppressions (tenant_id);

CREATE TABLE IF NOT EXISTS contacts (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	name VARCHAR, 
	subscribed BOOLEAN NOT NULL, 
	metadata_json TEXT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_contact_tenant_email UNIQUE (tenant_id, email), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_contacts_email ON contacts (email);

CREATE INDEX IF NOT EXISTS ix_contacts_tenant_id ON contacts (tenant_id);

CREATE TABLE IF NOT EXISTS campaigns (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	subject VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_campaigns_tenant_id ON campaigns (tenant_id);

CREATE TABLE IF NOT EXISTS webhook_endpoints (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	url VARCHAR NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	secret_hash VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_webhook_endpoints_tenant_id ON webhook_endpoints (tenant_id);

CREATE TABLE IF NOT EXISTS profiles (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	email VARCHAR, 
	phone VARCHAR, 
	external_id VARCHAR, 
	customer_id VARCHAR, 
	attributes_json TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_profiles_external_id ON profiles (external_id);

CREATE INDEX IF NOT EXISTS ix_profiles_email ON profiles (email);

CREATE INDEX IF NOT EXISTS ix_profiles_tenant_id ON profiles (tenant_id);

CREATE INDEX IF NOT EXISTS ix_profiles_customer_id ON profiles (customer_id);

CREATE TABLE IF NOT EXISTS segments (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	rules_json TEXT NOT NULL, 
	kind VARCHAR NOT NULL, 
	revision INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_segments_tenant_id ON segments (tenant_id);

CREATE TABLE IF NOT EXISTS journeys (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	version INTEGER NOT NULL, 
	graph_json TEXT NOT NULL, 
	goal_event VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_journeys_tenant_id ON journeys (tenant_id);

CREATE TABLE IF NOT EXISTS onboarding (
	tenant_id VARCHAR NOT NULL, 
	step INTEGER NOT NULL, 
	use_case VARCHAR, 
	checklist_json TEXT NOT NULL, 
	completed BOOLEAN NOT NULL, 
	PRIMARY KEY (tenant_id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS campaign_email_domains (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	campaign_id VARCHAR NOT NULL, 
	campaign_name VARCHAR NOT NULL, 
	primary_domain VARCHAR NOT NULL, 
	alias_domains TEXT NOT NULL, 
	sender_domain_verified BOOLEAN NOT NULL, 
	inbound_domain_verified BOOLEAN NOT NULL, 
	sending_enabled BOOLEAN NOT NULL, 
	receiving_enabled BOOLEAN NOT NULL, 
	human_mailbox_enabled BOOLEAN NOT NULL, 
	domain_classification VARCHAR NOT NULL, 
	default_reply_to VARCHAR, 
	support_address VARCHAR, 
	billing_address VARCHAR, 
	status VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	approved_by VARCHAR, 
	approved_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_campaign_email_domain UNIQUE (tenant_id, campaign_id), 
	CONSTRAINT uq_campaign_primary_domain_owner UNIQUE (tenant_id, primary_domain), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_campaign_email_domains_campaign_id ON campaign_email_domains (campaign_id);

CREATE INDEX IF NOT EXISTS ix_campaign_email_domains_tenant_id ON campaign_email_domains (tenant_id);

CREATE TABLE IF NOT EXISTS agent_mailboxes (
	mailbox_id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	agent_id VARCHAR NOT NULL, 
	employee_id VARCHAR, 
	keycloak_user_id VARCHAR, 
	odoo_user_id VARCHAR, 
	vicidial_user_id VARCHAR, 
	campaign_id VARCHAR NOT NULL, 
	campaign_name VARCHAR NOT NULL, 
	domain VARCHAR NOT NULL, 
	local_part VARCHAR NOT NULL, 
	primary_email VARCHAR NOT NULL, 
	display_name VARCHAR NOT NULL, 
	sending_enabled BOOLEAN NOT NULL, 
	receiving_enabled BOOLEAN NOT NULL, 
	mailbox_status VARCHAR NOT NULL, 
	quota INTEGER NOT NULL, 
	rate_limit INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	activated_at TIMESTAMP WITH TIME ZONE, 
	suspended_at TIMESTAMP WITH TIME ZONE, 
	deactivated_at TIMESTAMP WITH TIME ZONE, 
	last_send_at TIMESTAMP WITH TIME ZONE, 
	last_receive_at TIMESTAMP WITH TIME ZONE, 
	provisioning_correlation_id VARCHAR NOT NULL, 
	provisioning_error VARCHAR, 
	audit_version INTEGER NOT NULL, 
	outbound_validated BOOLEAN NOT NULL, 
	inbound_validated BOOLEAN NOT NULL, 
	PRIMARY KEY (mailbox_id), 
	CONSTRAINT uq_agent_mailbox_address UNIQUE (tenant_id, domain, local_part), 
	CONSTRAINT uq_agent_mailbox_assignment UNIQUE (tenant_id, agent_id, campaign_id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_agent_mailboxes_campaign_id ON agent_mailboxes (campaign_id);

CREATE INDEX IF NOT EXISTS ix_agent_mailboxes_primary_email ON agent_mailboxes (primary_email);

CREATE INDEX IF NOT EXISTS ix_agent_mailboxes_tenant_id ON agent_mailboxes (tenant_id);

CREATE INDEX IF NOT EXISTS ix_agent_mailboxes_agent_id ON agent_mailboxes (agent_id);

CREATE INDEX IF NOT EXISTS ix_agent_mailboxes_provisioning_correlation_id ON agent_mailboxes (provisioning_correlation_id);

CREATE TABLE IF NOT EXISTS klyrow_plans (
	id VARCHAR NOT NULL, 
	product_id VARCHAR NOT NULL, 
	code VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	features_json TEXT NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES klyrow_products (id), 
	UNIQUE (code)
);

CREATE TABLE IF NOT EXISTS klyrow_subscriptions (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	plan_id VARCHAR NOT NULL, 
	price_id VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	period_start TIMESTAMP WITH TIME ZONE NOT NULL, 
	period_end TIMESTAMP WITH TIME ZONE NOT NULL, 
	trial_end TIMESTAMP WITH TIME ZONE, 
	cancel_at_period_end BOOLEAN NOT NULL, 
	version INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_klyrow_subscriptions_tenant_id ON klyrow_subscriptions (tenant_id);

CREATE TABLE IF NOT EXISTS organizations (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	slug VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	UNIQUE (slug)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_organizations_tenant_id ON organizations (tenant_id);

CREATE TABLE IF NOT EXISTS customer_events (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	profile_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	properties_json TEXT NOT NULL, 
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(profile_id) REFERENCES profiles (id)
);

CREATE INDEX IF NOT EXISTS ix_customer_events_profile_id ON customer_events (profile_id);

CREATE INDEX IF NOT EXISTS ix_customer_events_tenant_id ON customer_events (tenant_id);

CREATE INDEX IF NOT EXISTS ix_customer_events_occurred_at ON customer_events (occurred_at);

CREATE INDEX IF NOT EXISTS ix_customer_events_name ON customer_events (name);

CREATE TABLE IF NOT EXISTS consents (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	profile_id VARCHAR NOT NULL, 
	topic VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	source VARCHAR NOT NULL, 
	version VARCHAR NOT NULL, 
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	proof_json TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(profile_id) REFERENCES profiles (id)
);

CREATE INDEX IF NOT EXISTS ix_consents_tenant_id ON consents (tenant_id);

CREATE INDEX IF NOT EXISTS ix_consents_profile_id ON consents (profile_id);

CREATE TABLE IF NOT EXISTS preferences (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	profile_id VARCHAR NOT NULL, 
	topic VARCHAR NOT NULL, 
	subscribed BOOLEAN NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(profile_id) REFERENCES profiles (id)
);

CREATE INDEX IF NOT EXISTS ix_preferences_profile_id ON preferences (profile_id);

CREATE INDEX IF NOT EXISTS ix_preferences_tenant_id ON preferences (tenant_id);

CREATE TABLE IF NOT EXISTS mfa_configs (
	user_id VARCHAR NOT NULL, 
	secret VARCHAR NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	recovery_hashes_json TEXT NOT NULL, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS klyrow_prices (
	id VARCHAR NOT NULL, 
	plan_id VARCHAR NOT NULL, 
	version INTEGER NOT NULL, 
	currency VARCHAR NOT NULL, 
	billing_cycle VARCHAR NOT NULL, 
	base_amount NUMERIC(18, 6) NOT NULL, 
	included_units INTEGER NOT NULL, 
	overage_amount NUMERIC(18, 8) NOT NULL, 
	effective_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	retired_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_klyrow_price_version UNIQUE (plan_id, version), 
	FOREIGN KEY(plan_id) REFERENCES klyrow_plans (id)
);

CREATE INDEX IF NOT EXISTS ix_klyrow_prices_plan_id ON klyrow_prices (plan_id);

COMMIT;
