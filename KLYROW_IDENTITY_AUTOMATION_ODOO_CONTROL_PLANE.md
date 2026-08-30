# Klyrow Identity, Automation and Odoo Control Plane

## 1. Purpose

This document is a mandatory cross-cutting contract for every Klyrow feature branch.

Klyrow must operate as one coherent SaaS product while integrating safely with:

- Keycloak for human identity and authentication;
- the Codestra middleware as the only trusted system-integration boundary;
- n8n for non-authoritative business-process automation;
- Odoo for back-office customer, CRM, accounting, billing, support and operational management;
- Postal 3.3.7 for email delivery.

Signup, onboarding, membership, billing, subscription, usage, invoice, payment, support, Postal-provisioning and account-state changes must produce reliable domain events. Those events are delivered asynchronously through the middleware so n8n and Odoo can react without making Klyrow's core browser flows depend on either system being online.

This contract supplements `KLYROW_MODERN_SAAS_PROGRAM.md` and `docs/implementation/KLYROW_FEATURE_MISSIONS.md`. Where this document is more specific, this document controls the Keycloak, middleware, n8n and Odoo boundaries.

---

## 2. Non-negotiable system-of-record boundaries

### 2.1 Keycloak is authoritative for human identity

Keycloak at `https://auth.codestra.co/realms/codestra` owns:

- email/password registration;
- Google identity brokering;
- verified-email state;
- password and credential lifecycle;
- MFA and identity-level authentication policy;
- OIDC sessions and identity-provider linkage;
- immutable OIDC issuer and subject identifiers.

Keycloak must not become the accounting, subscription, invoice, payment, usage or customer-data database.

Only small authorization-oriented claims may be projected into Keycloak when required. Never store invoice lines, card data, payment history, message-level usage or full Odoo records in Keycloak attributes or tokens.

### 2.2 Klyrow PostgreSQL is authoritative for the SaaS product

Klyrow owns:

- local identity linkage by `(issuer, subject)`;
- organizations/workspaces;
- memberships, permissions and capabilities;
- onboarding state;
- plans, subscriptions, entitlements and quota enforcement;
- append-only usage ledger and billing reconciliation metadata;
- domains, senders, API keys, SMTP credentials and Postal mappings;
- customer profiles, events, consent, preferences and suppressions;
- templates, campaigns, journeys, experiments and analytics;
- integration state, outbox/inbox records and audit records.

Odoo may mirror and manage approved back-office fields, but Odoo must not silently bypass Klyrow authorization, entitlement, consent, suppression or sending controls.

### 2.3 Odoo is the back-office management surface

Odoo receives synchronized business records so the platform owner and authorized staff can manage:

- customer companies and contacts;
- sales/CRM relationships;
- plans and commercial subscription references;
- usage statements;
- invoices, credits, payment state and collections workflows;
- support cases;
- customer communication and internal activities;
- links to other installed Odoo applications.

Odoo accounting records may be authoritative for formal accounting documents after they are created there. Klyrow remains authoritative for metering, entitlements and product-access enforcement. Reconciliation must make disagreements visible rather than choosing a winner silently.

### 2.4 Middleware is the only cross-system trust boundary

Klyrow, Keycloak event adapters, n8n and Odoo communicate through authenticated middleware contracts.

Required protections:

- mTLS and/or short-lived service credentials;
- explicit service identity and permission;
- signed versioned payloads;
- request, correlation and causation IDs;
- replay protection;
- idempotency;
- bounded timeouts;
- durable retries;
- dead-letter visibility;
- audit events;
- no direct Odoo, Keycloak, Postal or Klyrow database access.

### 2.5 n8n is an orchestrator, not an authority

n8n may:

- send internal notifications;
- schedule onboarding follow-up;
- create Odoo activities;
- route support and collections work;
- coordinate approved middleware calls;
- trigger reconciliation or review workflows;
- transform non-sensitive payloads under an approved schema.

n8n must not:

- authenticate Klyrow users;
- assign platform-owner privileges;
- edit the Klyrow billing ledger directly;
- grant entitlements without an authorized Klyrow command;
- bypass consent or suppression;
- modify databases directly;
- store Keycloak, Postal, payment-provider or Klyrow administrator secrets in workflow exports;
- become required for successful signup, login, logout or normal API requests.

---

## 3. Platform-owner account and authorization

The intended platform owner must have a clean administration experience, but platform ownership must never be granted by matching an email address alone.

### 3.1 Owner binding

Use deployment configuration for:

```text
KLYROW_PLATFORM_OWNER_ISSUER=https://auth.codestra.co/realms/codestra
KLYROW_PLATFORM_OWNER_SUBJECT=<exact-keycloak-subject>
KLYROW_PLATFORM_OWNER_EMAIL=<verified-owner-mailbox>
```

The exact owner mailbox supplied by the operator must be validated before activation. Do not hard-code an informally typed address into source code.

The permanent authorization binding is `(issuer, subject)`. Email is display/bootstrap metadata and may change.

### 3.2 Owner role

Create an explicit `PLATFORM_OWNER` permission set distinct from tenant `OWNER`.

Required controls:

- assignment only by an additive migration or approved operator command;
- no public endpoint that can self-promote a user;
- verified email;
- MFA required;
- step-up authentication for high-risk actions;
- immutable audit evidence;
- session listing and revocation;
- owner-protection rules;
- optional separately controlled break-glass identity with offline procedure;
- no exposure of raw provider, SMTP, API, refresh-token or payment secrets.

### 3.3 High-risk actions

Require a fresh authorization check, reason and confirmation for:

- tenant suspension or deletion;
- sending suspension or re-enable;
- credits and billing adjustments;
- manual payment confirmation;
- plan or entitlement override;
- role elevation;
- credential revocation;
- Odoo conflict override;
- event replay that could create an accounting document;
- production-delivery activation.

Dual approval should be supported for production activation, large credits and destructive account actions.

---

## 4. Clean platform-admin design

The platform administration application must be designed for the owner and authorized operators, not as a raw API table viewer.

### 4.1 Application shell

Provide:

- a dedicated protected admin route or host;
- responsive desktop/tablet layout;
- persistent navigation with keyboard support;
- global search for tenant, user, invoice, domain, message and external Odoo reference;
- page headers, breadcrumbs and clear environment banner;
- loading, empty, stale, degraded, permission-denied and error states;
- saved filters where safe;
- accessible data tables, drawers and confirmation dialogs;
- English and Spanish strings;
- WCAG 2.2 AA behavior.

### 4.2 Admin overview

Show real, sourced metrics only:

- new signups and verified users;
- active, trial, past-due and suspended workspaces;
- plan distribution;
- message usage and quota risk;
- issued, paid, failed and overdue invoices;
- credits and adjustments;
- Postal provisioning state;
- domain/deliverability risk;
- middleware, n8n and Odoo sync health;
- outbox/inbox backlog;
- failed automations and dead-letter records;
- open support and collections work;
- security alerts and active privileged sessions.

Do not invent MRR, ARR, churn or revenue. Calculate financial metrics only from reconciled billing/accounting records and display definition/source details.

### 4.3 Customer 360 view

For every workspace show:

- company and billing profile;
- users, identities, roles and last activity;
- onboarding progress;
- plan, subscription, entitlements and usage;
- invoice, credit and payment history;
- domains, senders and Postal provisioning;
- consent/suppression summary;
- support tickets;
- Odoo partner/contact/subscription/invoice references;
- n8n automation history;
- middleware event and sync timeline;
- audit trail;
- safe actions appropriate to the operator's permission.

### 4.4 Integration operations view

Provide:

- Keycloak event adapter status;
- middleware connectivity;
- n8n workflow subscription status;
- Odoo capability/module discovery;
- last successful sync by entity type;
- retryable, blocked, conflict and dead-letter states;
- event payload metadata with PII masking;
- retry/reconcile actions with permission, reason and audit;
- external deep links to Odoo records when configured;
- no secret display.

---

## 5. Control-plane architecture

### 5.1 Write path

Every externally meaningful state mutation must follow this pattern:

```text
validated command
  -> authoritative Klyrow transaction
  -> domain record mutation
  -> audit record
  -> domain-event record
  -> integration outbox record
  -> commit once
  -> asynchronous middleware delivery
  -> n8n and/or Odoo processing
  -> signed result callback
  -> durable Klyrow inbox
  -> mapping/sync-state update
```

The domain mutation and event/outbox insertion must commit atomically.

### 5.2 Read path

Customer-facing reads use Klyrow's authoritative database. They must not synchronously query Odoo or n8n.

Admin pages may display Odoo/n8n mirror state already stored in Klyrow. Explicit refresh/reconciliation actions must run as asynchronous jobs.

### 5.3 Failure behavior

- Signup, login and workspace creation succeed even when middleware, n8n or Odoo is unavailable.
- The record is marked `PENDING_SYNC` or `DEGRADED`, not rolled back.
- Retries use bounded exponential backoff with jitter.
- Ambiguous timeouts are retried with the same idempotency key.
- Permanent validation failures become `BLOCKED` with operator guidance.
- Retry exhaustion becomes `DEAD_LETTER` with an audited replay path.
- Conflicting edits become `CONFLICT`; they are never overwritten silently.

---

## 6. Versioned event envelope

All cross-system events use a stable envelope similar to:

```json
{
  "specversion": "1.0",
  "id": "01J...",
  "type": "klyrow.billing.invoice.issued.v1",
  "source": "klyrow-api",
  "subject": "invoice/<klyrow-invoice-id>",
  "time": "2026-08-26T04:00:00Z",
  "environment": "staging",
  "tenant_id": "<workspace-id>",
  "actor": {
    "kind": "human|service|system",
    "issuer": "https://auth.codestra.co/realms/codestra",
    "subject": "<oidc-sub-or-service-id>"
  },
  "correlation_id": "<request-or-workflow-id>",
  "causation_id": "<prior-event-or-command-id>",
  "idempotency_key": "<stable-operation-key>",
  "schema_version": 1,
  "pii_classification": "none|limited|sensitive",
  "data": {}
}
```

Required rules:

- IDs are globally unique.
- Event type and schema version are explicit.
- Timestamps are UTC.
- Tenant context is mandatory for tenant-owned events.
- Actor context is mandatory for sensitive changes.
- Payloads contain only required data.
- Passwords, password hashes, OIDC tokens, API secrets, SMTP secrets, full card numbers, CVV values and private keys are prohibited.
- Payment information is token/reference based and masked.
- Schema evolution is backward compatible or uses a new event version.
- Middleware verifies signature/service identity before accepting an event.

---

## 7. Required event catalog

### Identity and signup

- `identity.user.observed.v1`
- `identity.user.registered.v1`
- `identity.email.verified.v1`
- `identity.profile.updated.v1`
- `identity.user.disabled.v1`
- `identity.user.enabled.v1`
- `identity.mfa.enrolled.v1`
- `identity.session.revoked.v1`

Keycloak-originated events must be normalized through a supported event listener/adapter or a reconciler using the Keycloak Admin API. Never read the Keycloak database directly.

### Workspace and membership

- `workspace.created.v1`
- `workspace.updated.v1`
- `workspace.suspended.v1`
- `workspace.reactivated.v1`
- `membership.invited.v1`
- `membership.accepted.v1`
- `membership.role_changed.v1`
- `membership.removed.v1`
- `onboarding.started.v1`
- `onboarding.step_completed.v1`
- `onboarding.completed.v1`

### Postal and email operations

- `postal.provisioning.requested.v1`
- `postal.provisioning.ready.v1`
- `postal.provisioning.failed.v1`
- `domain.verification.changed.v1`
- `sending.suspended.v1`
- `sending.reactivated.v1`
- `usage.email.recorded.v1`

### Billing and commercial state

- `billing.plan.assigned.v1`
- `billing.subscription.created.v1`
- `billing.subscription.changed.v1`
- `billing.subscription.canceled.v1`
- `billing.subscription.past_due.v1`
- `billing.usage.threshold_reached.v1`
- `billing.usage.period_closed.v1`
- `billing.invoice.requested.v1`
- `billing.invoice.issued.v1`
- `billing.invoice.paid.v1`
- `billing.invoice.payment_failed.v1`
- `billing.invoice.voided.v1`
- `billing.credit.created.v1`
- `billing.adjustment.created.v1`
- `billing.reconciliation.failed.v1`

### Support, compliance and operations

- `support.ticket.created.v1`
- `support.ticket.updated.v1`
- `compliance.export.requested.v1`
- `compliance.deletion.requested.v1`
- `integration.sync.failed.v1`
- `integration.sync.recovered.v1`
- `security.risk.detected.v1`

Each feature branch must document which events it owns and include contract tests. Feature code must publish internal domain events through one shared event service; it must not call n8n or Odoo directly.

---

## 8. Inbound command contract

Odoo and n8n may request approved changes only through middleware and Klyrow command APIs.

A command must include:

- command ID and idempotency key;
- issuing service identity;
- tenant and target entity;
- required permission/capability;
- expected entity version or ETag for conflicting writes;
- reason and originating Odoo/n8n reference;
- requested mutation;
- signature/authentication metadata;
- correlation and causation IDs.

Approved command families may include:

- update billing/contact address;
- attach an Odoo external reference;
- record a validated manual payment result;
- request a credit or adjustment for review;
- request plan change for review/validation;
- open/update a support case;
- add an internal account note;
- request tenant or sending suspension for authorized review;
- request reconciliation.

Commands that affect entitlements, credits, payments, suspension or privileged roles require explicit Klyrow validation and audit. Odoo/n8n cannot directly change a Klyrow role, owner binding, usage ledger or send-policy decision.

---

## 9. Odoo synchronization model

### 9.1 Capability-aware adapter

The Odoo adapter must discover installed modules/capabilities and use an explicit mapping profile. It must not assume that every Odoo installation has the same subscription, helpdesk, accounting or CRM modules.

Preferred mappings when available:

| Klyrow entity | Odoo target | Authority |
|---|---|---|
| Workspace/company | `res.partner` company | Klyrow identity/status; Odoo approved back-office fields |
| Member/contact | child `res.partner` contact | Keycloak/Klyrow identity; Odoo CRM/contact mirror |
| Odoo login | `res.users` only when explicitly authorized | Odoo |
| Lead/onboarding opportunity | CRM lead/opportunity | Odoo |
| Commercial subscription | installed subscription/sales model through adapter | Klyrow entitlement; Odoo commercial mirror |
| Usage statement | custom `klyrow.usage.statement` or attachment/model | Klyrow |
| Invoice | `account.move` when Accounting is installed | Odoo accounting document |
| Payment | Odoo payment/status reference | Odoo/accounting or validated provider event |
| Credit/adjustment | accounting credit/adjustment record | Odoo accounting with Klyrow entitlement reconciliation |
| Support ticket | Helpdesk ticket or configured fallback | Odoo workflow; Klyrow reference/status mirror |
| Domain/deliverability incident | activity/tag/custom record | Klyrow technical state |

Do not automatically create an Odoo login for every Klyrow customer. Most Klyrow users should be Odoo contacts, not internal Odoo users.

### 9.2 External references

Klyrow must store mappings without exposing Odoo internals to customers:

```text
provider = odoo
entity_type
klyrow_entity_id
odoo_model
odoo_record_id
odoo_external_key
mapping_version
last_klyrow_version
last_odoo_write_date
last_payload_checksum
last_synced_at
sync_state
```

Unique constraints must prevent two active Odoo records from claiming the same Klyrow entity mapping.

### 9.3 Field ownership

Every mapped field has an owner:

- `KLYROW`: Odoo receives a mirror and may not overwrite it.
- `ODOO`: Klyrow receives an approved mirror through middleware.
- `MERGED`: changes use an explicit rule and conflict detection.
- `LOCAL_ONLY`: never synchronized.

Passwords, secrets, tokens, recovery codes and private provider configuration are always `LOCAL_ONLY`.

### 9.4 Reconciliation

Provide:

- incremental sync by cursor/checkpoint;
- scheduled reconciliation by entity type and time window;
- count, external-reference and checksum comparison;
- missing-record detection;
- stale-version detection;
- duplicate mapping detection;
- manual conflict resolution with reason and audit;
- dry run before bulk repair;
- safe replay with original idempotency key where appropriate.

---

## 10. New-signup and onboarding flow

The complete flow is:

```text
User registers with email/password or Google in Keycloak
  -> Keycloak verifies/authenticates identity
  -> Klyrow BFF validates OIDC response
  -> Klyrow resolves (issuer, subject)
  -> Klyrow accepts invitation or creates starter workspace idempotently
  -> Klyrow writes identity/workspace/membership/onboarding records
  -> Klyrow writes audit + domain events + outbox in the same transaction
  -> browser continues to Klyrow onboarding immediately
  -> middleware receives events asynchronously
  -> n8n executes approved onboarding automations
  -> Odoo partner/company/contact/lead records are upserted
  -> results return through the durable inbox
  -> admin Customer 360 shows sync state and external references
```

Required properties:

- duplicate OIDC callbacks do not duplicate workspace or Odoo records;
- Google and password identities with the same verified mailbox follow explicit safe-linking rules;
- Odoo/n8n outages do not block login/signup;
- unverified email status is propagated without inventing verification;
- invitation metadata is preserved;
- no passwords or OIDC tokens enter events;
- first-login and Odoo upsert operations are idempotent;
- admin receives clear pending/failure status.

---

## 11. Billing and Odoo accounting flow

### 11.1 Usage and entitlement

Klyrow records usage in an append-only ledger and enforces product entitlements. At the end of a billing period it creates a reconciled usage statement and invoice request event.

### 11.2 Invoice creation

When Odoo Accounting is configured:

```text
Klyrow billing period closes
  -> Klyrow freezes a usage-statement version
  -> billing.invoice.requested.v1 enters the outbox
  -> middleware sends an idempotent Odoo upsert command
  -> Odoo creates/updates the accounting invoice
  -> Odoo returns model, record ID, invoice number and accounting status
  -> Klyrow stores the external mapping and mirror status
  -> customer/admin billing UI shows the reconciled state
```

The Odoo invoice must reference the Klyrow workspace, subscription, usage-statement version and idempotency key.

### 11.3 Payments and credits

- Signed payment-provider events are processed through Klyrow's durable inbox.
- Payment/credit state is synchronized to Odoo through middleware.
- Manual payments or credits entered in Odoo return as signed commands/events.
- Klyrow validates amount, currency, invoice, tenant, duplication and authorization.
- Entitlement changes occur only after the approved Klyrow billing policy confirms the state.
- Out-of-order or conflicting payment events are reconciled, not overwritten silently.
- Tests and staging use provider test mode and cannot create real charges.

### 11.4 Billing fields synchronized to Odoo

At minimum, when authorized and available:

- workspace/customer reference;
- legal/billing name;
- billing contact;
- billing address and tax metadata;
- plan and subscription reference;
- billing period;
- usage statement totals;
- invoice line summary;
- currency;
- subtotal, tax, discount, credit and total;
- invoice status;
- due date;
- payment status/reference;
- collection state;
- Klyrow and Odoo external IDs;
- reconciliation timestamp/status.

Never synchronize full payment-card data, CVV, secret tokens or unmasked bank credentials.

---

## 12. n8n automation catalog

Provide versioned, exportable workflow definitions without credentials.

Recommended workflows include:

1. New verified signup
   - create/update Odoo company/contact;
   - create an onboarding activity or CRM opportunity;
   - notify the platform owner/operator;
   - schedule approved onboarding reminders.

2. Workspace onboarding stalled
   - create a follow-up activity after configurable inactivity;
   - avoid duplicate reminders using event ID/idempotency.

3. Postal provisioning ready/failed
   - notify customer success or operations;
   - create/update an Odoo activity/ticket on failure.

4. Trial ending
   - create a sales/customer-success activity;
   - send only approved transactional notifications through Klyrow.

5. Usage threshold reached
   - notify authorized user and owner;
   - create an Odoo activity;
   - never auto-upgrade without an approved policy/command.

6. Invoice issued
   - attach/link invoice context;
   - start approved collections schedule.

7. Payment succeeded/failed/past due
   - update Odoo activity and collection state;
   - request Klyrow entitlement review through an authenticated command.

8. Plan change or cancellation
   - update CRM/subscription workflow;
   - schedule retention or offboarding activities.

9. Support ticket
   - route by category/severity;
   - synchronize status through middleware.

10. Deliverability/security incident
    - create an operations ticket;
    - notify approved channels;
    - never automatically re-enable sending.

Every workflow must have:

- explicit trigger event versions;
- expected input/output schema;
- idempotency handling;
- timeout and retry policy;
- dead-letter route;
- audit/correlation IDs;
- PII minimization;
- disabled-by-default production activation;
- test fixtures;
- no embedded credentials.

---

## 13. Required persistence

Add or normalize tables equivalent to:

- `domain_events`;
- `integration_outbox`;
- `integration_inbox`;
- `integration_deliveries`;
- `external_entity_links`;
- `sync_runs`;
- `sync_checkpoints`;
- `sync_conflicts`;
- `sync_dead_letters`;
- `automation_subscriptions`;
- `automation_executions`;
- `admin_approvals`;
- `billing_reconciliations`.

Required common fields include tenant, event/command ID, entity type/ID, state, version, attempts, lease owner/expiry, next attempt, request/correlation/causation IDs, payload checksum, created/updated/completed timestamps and sanitized last error.

Payload storage must follow retention, encryption and PII-minimization policy.

---

## 14. Required APIs

Exact routing may follow the existing API structure, but the capability set must include:

### Internal service APIs

- publish/receive normalized events;
- receive signed integration results;
- receive authorized commands;
- acquire/acknowledge/retry integration jobs;
- Keycloak identity reconciliation;
- Odoo capability discovery/test connection;
- Odoo entity upsert/reconciliation through middleware;
- n8n workflow subscription/result callbacks.

### Platform-admin APIs

- integration health summary;
- event/outbox/inbox search;
- entity sync status;
- external mappings;
- conflict list/detail/resolve;
- dead-letter list/detail/replay;
- reconciliation create/status/result;
- Odoo and n8n configuration metadata using secret references;
- automation execution history;
- privileged action approval.

All APIs require explicit permissions, tenant/platform scope validation, pagination, request IDs, structured errors and audit coverage.

---

## 15. Observability

Add metrics and dashboards for:

- domain events created by type;
- outbox pending/leased/retry/dead-letter counts;
- inbox accepted/duplicate/rejected counts;
- middleware delivery latency and error rate;
- Keycloak event/reconciliation lag;
- n8n workflow success/failure/duration;
- Odoo sync success/failure/conflict/lag;
- billing reconciliation drift;
- signup-to-Odoo synchronization latency;
- invoice-request-to-Odoo-invoice latency;
- dead-letter age;
- privileged admin actions.

Logs must carry correlation IDs and must not contain passwords, tokens, secrets, full payment details or unnecessary PII.

---

## 16. Security and privacy

Required controls:

- service-to-service mTLS and/or short-lived OIDC client credentials;
- audience-restricted service tokens;
- allowlisted middleware destinations;
- SSRF-resistant outbound client;
- signature/replay validation;
- encrypted secret references;
- field-level PII classification;
- masking in UI/logs;
- least-privilege Odoo service user;
- least-privilege n8n credentials;
- audit of every privileged sync/replay/conflict resolution;
- retention and deletion propagation where legally appropriate;
- no direct database credentials for n8n;
- no public Odoo administrator API exposure;
- no billing or user-list data in Keycloak tokens beyond minimal authorized claims.

---

## 17. Feature-branch integration rule

Every feature branch that creates or changes externally meaningful state must:

1. identify its owned domain events;
2. write events through the shared domain-event service in the authoritative transaction;
3. avoid direct n8n/Odoo calls;
4. document event schemas and PII classification;
5. add contract tests;
6. add audit and correlation data;
7. define retry/reconciliation behavior;
8. expose customer/admin sync status only where useful;
9. remain functional when integrations are unavailable.

The billing branch must emit the billing events in this document. The identity/tenancy branches must emit signup, workspace and membership events. The enterprise-admin branch must implement the owner console and integration-operations experience. The integration branch must provide the connector framework used by the two dedicated branches below.

---

## 18. Dedicated implementation branches

### Branch A — `feat/klyrow-control-plane-events`

Objective: implement the shared event/command control plane.

Required scope:

- domain-event service and schema registry;
- atomic domain-event/outbox writes;
- durable outbox/inbox/delivery workers;
- middleware adapter with service authentication;
- idempotency, signature and replay controls;
- Keycloak event normalization and reconciliation adapter;
- n8n event subscription/result contract;
- event search and dead-letter admin APIs;
- correlation/audit/metrics;
- migrations, rollback, OpenAPI, tests and runbooks.

Prerequisites:

- reviewed auth/BFF and tenancy foundations;
- integration framework;
- billing event definitions implemented or available on the integration baseline.

### Branch B — `feat/klyrow-odoo-backoffice-sync`

Objective: provide complete Odoo back-office synchronization and owner operations UX.

Required scope:

- capability-aware Odoo adapter through middleware;
- company/contact/user-reference synchronization;
- onboarding/CRM activities;
- plan/subscription/usage/invoice/payment/credit mapping;
- external-reference storage;
- field-ownership and conflict policy;
- incremental sync and reconciliation workers;
- Odoo-side connector/addon contract where required;
- owner Customer 360, billing, automation and sync operations UI;
- Odoo deep links without secret exposure;
- n8n workflow definitions and fixtures;
- migrations, rollback, OpenAPI, tests, dashboards and runbooks.

Prerequisites:

- billing, integration, enterprise-admin and control-plane branches reviewed and merged into the implementation baseline.

Neither branch may deploy directly to production.

---

## 19. Critical acceptance tests

At minimum test:

- duplicate Keycloak registration/callback;
- email verification update;
- Google and password identity safe linking;
- signup succeeds while Odoo/n8n are unavailable;
- one Klyrow workspace maps to one intended Odoo company;
- member upsert does not create an Odoo internal user unless authorized;
- cross-tenant event and command rejection;
- forged signature and replay rejection;
- duplicate event and out-of-order result handling;
- middleware timeout after Odoo success;
- n8n retry without duplicate activity;
- Odoo conflict detection;
- billing usage deduplication;
- invoice idempotency;
- payment and credit reconciliation;
- manual Odoo payment command authorization;
- entitlement cannot be changed by an unauthorized Odoo/n8n command;
- owner role cannot be granted by email matching;
- MFA/step-up on high-risk admin action;
- PII and secret leakage scans;
- dead-letter replay audit;
- reconciliation after prolonged outage;
- no direct Odoo/Keycloak/Postal database access;
- zero real charges in tests.

---

## 20. Release gates

Production activation requires all existing release gates plus:

- exact verified platform-owner issuer and subject;
- owner MFA and recovery procedure;
- middleware service identity and mTLS/OIDC validation;
- n8n workflow review with credentials excluded from exports;
- least-privilege Odoo service account;
- staging Odoo and n8n end-to-end evidence;
- signup, billing, invoice, payment, support and conflict test evidence;
- outbox/inbox/dead-letter dashboards and alerts;
- reconciliation report with no unexplained drift;
- backup/restore coverage for integration state;
- rollback that leaves authoritative Klyrow state intact;
- explicit owner go/no-go.

Missing Odoo modules, middleware credentials, Keycloak event integration, n8n credentials or exact owner identity remain blockers. Codex must never fabricate or bypass them.
