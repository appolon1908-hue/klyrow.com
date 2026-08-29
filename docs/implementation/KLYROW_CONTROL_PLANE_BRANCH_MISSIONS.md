# Klyrow Control Plane Branch Missions

Read `KLYROW_CODEX_EXECUTION_INDEX.md` and `KLYROW_IDENTITY_AUTOMATION_ODOO_CONTROL_PLANE.md` completely before implementing either branch.

## Mission A — Shared control-plane events

**Branch:** `feat/klyrow-control-plane-events`

### Objective

Implement the common event/command infrastructure that reliably shares approved identity, signup, workspace, membership, Postal, billing, support and operational state through the Codestra middleware for n8n and Odoo consumers.

### Required implementation

- Shared versioned domain-event service.
- Atomic domain mutation, audit, domain-event and outbox transaction.
- Durable integration outbox, inbox, deliveries, leases, retries and dead-letter handling.
- Signed/replay-protected middleware event and result contracts.
- Keycloak event normalization and supported reconciliation through API/event adapter, never database access.
- n8n subscriptions, execution result and correlation contracts.
- Authorized inbound command API with permissions, version checks and idempotency.
- Admin event search, delivery timeline, retry, reconciliation and dead-letter views.
- Metrics, alerts and runbooks.
- Migrations, rollback, OpenAPI and complete tests.

### Critical tests

- Duplicate and out-of-order events.
- Worker crash before/after delivery.
- Timeout after downstream success.
- Forged signature and replay.
- Cross-tenant event/command rejection.
- Keycloak registration and verification normalization.
- Signup success during middleware/n8n/Odoo outage.
- No secrets or prohibited PII in payloads/logs.
- Dead-letter replay audit.

### Exclusions

Do not implement direct Odoo database access, embed n8n credentials, deploy, enable production automations or change Postal source.

---

## Mission B — Odoo back-office synchronization

**Branch:** `feat/klyrow-odoo-backoffice-sync`

### Objective

Synchronize approved Klyrow customer, membership, onboarding, billing, invoice, payment, credit, support and operational data to Odoo through middleware, and deliver a clean platform-owner administration experience.

### Required implementation

- Capability-aware Odoo adapter through middleware.
- Workspace/company and member/contact upsert.
- Explicit rule that a Klyrow user does not become an Odoo internal user unless separately authorized.
- CRM/onboarding activity integration.
- Plan, subscription, usage statement, invoice, payment and credit mapping.
- External-reference table and unique mapping rules.
- Field ownership, version/checksum conflict detection and audited resolution.
- Incremental synchronization, checkpointing and scheduled reconciliation.
- Odoo-side addon/connector contract where required.
- n8n workflow definitions and test fixtures without credentials.
- Platform-owner overview, Customer 360, billing, automation, Odoo mapping, conflict and dead-letter UI.
- Odoo record deep links where configured.
- Metrics, alerts and runbooks.
- Migrations, rollback, OpenAPI, integration tests, browser tests and accessibility tests.

### Platform-owner security

- Bind `PLATFORM_OWNER` to exact Keycloak issuer and subject, never email alone.
- Require verified email, MFA and step-up authentication.
- Require reason/audit for credits, payment confirmation, entitlement override, suspension, role elevation, conflict override and replay.
- Never display provider, SMTP, API, OIDC, n8n, Odoo or payment secrets.

### Critical tests

- Idempotent signup-to-Odoo upsert.
- Odoo/n8n outage and recovery.
- Duplicate company/contact prevention.
- Billing usage and invoice reconciliation.
- Manual payment/credit authorization.
- Out-of-order payment status.
- Conflict detection and resolution.
- Cross-tenant and privilege-escalation rejection.
- Owner role cannot be granted by email matching.
- No real charges in tests.
- No direct database access.

### Exclusions

Do not deploy directly to production, make Odoo authoritative for Klyrow authorization/entitlements, store billing records in Keycloak, or let n8n mutate authoritative data without an authenticated Klyrow command.

---

# Completion report

Each branch must report repository, branch, starting/final SHA, commits, changed files, implemented behavior, migrations/rollback, exact tests/results, OpenAPI, UI/accessibility, security, tenant isolation, sync/reconciliation evidence, known blockers and confirmation that no deployment, production activation, database bypass, secret output or Postal modification occurred.
