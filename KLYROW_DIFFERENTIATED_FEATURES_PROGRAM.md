# Klyrow Differentiated Features Program

## 1. Purpose

This document extends the existing Klyrow modern SaaS program. It does not authorize a rewrite of the current platform.

The implementation must build on the system already present:

- Keycloak at `https://auth.codestra.co/realms/codestra` for human authentication, verified identity, MFA, sessions and identity-provider linkage;
- Klyrow FastAPI and PostgreSQL for authoritative SaaS tenancy, permissions, product state, usage, entitlements, communication policy and integration state;
- Postal 3.3.7 as the primary email-delivery engine;
- Mautic only through a Klyrow-owned adapter where campaign capabilities are retained;
- Codestra middleware as the only cross-system integration boundary;
- n8n as non-authoritative automation;
- Odoo as the platform owner's CRM, accounting, billing, support and back-office operations surface;
- RabbitMQ plus durable database outbox/inbox patterns for retryable work;
- Prometheus/Grafana-compatible observability.

The product objective is not to become another generic email API. Klyrow should become a governed customer-communications operating system in which every message is authorized, explainable, auditable, portable and financially reconciled.

## 2. Non-rewrite rule

Every branch in this program must:

1. inventory existing behavior before editing;
2. retain compatible endpoints and workflows where they are safe;
3. extend existing models through additive migrations;
4. introduce adapters around existing Postal, Mautic, middleware and Odoo integrations rather than replacing them without a reviewed migration reason;
5. preserve safe-mode and production delivery gates;
6. provide a versioned migration path for existing portal and API callers;
7. avoid direct writes to Keycloak, Postal or Odoo databases;
8. avoid direct feature-to-n8n or feature-to-Odoo calls;
9. publish shared domain events through the Klyrow control plane;
10. remain independently reviewable and non-deploying.

## 3. Product promise

Klyrow must be able to answer four questions for every communication:

1. **Why was this message requested?**
2. **Was it permitted, and by which policy and evidence?**
3. **What did it cost and which entitlement or quota did it consume?**
4. **What happened across Klyrow, middleware, n8n, Odoo and the delivery provider?**

The six feature families below create that promise.

## 4. New branch catalog

### 4.1 `feat/klyrow-decision-policy-ledger`

Build the authoritative communication-intent, policy-decision, approval, explanation and signed message-passport layer.

This branch owns:

- communication intent creation;
- versioned policy bundles;
- fail-closed pre-send evaluation;
- immutable decision evidence;
- human approval workflow for governed exceptions;
- message explanation timeline;
- signed message passports;
- policy and decision administration UI.

### 4.2 `feat/klyrow-simulation-attention-engine`

Build a no-side-effect digital twin for campaigns and journeys plus a recipient attention-budget and collision-resolution engine.

This branch owns:

- historical and synthetic simulation;
- deterministic replay of journey, segment and policy behavior;
- volume, cost, queue and integration-impact estimates;
- recipient collision detection;
- communication priority and frequency arbitration;
- defer, drop, digest and approval decisions;
- simulation comparison UI.

### 4.3 `feat/klyrow-recipient-trust-center`

Build a secure public recipient experience for communication explanations, subscription preferences, consent visibility, privacy requests and abuse reporting.

This branch owns:

- signed and scoped recipient-access tokens;
- safe `Why am I receiving this?` explanations;
- topic and frequency preferences;
- unsubscribe and double-opt-in flows;
- communication-history summaries;
- export/deletion requests;
- abuse and support reporting;
- multilingual accessible public UI.

### 4.4 `feat/klyrow-reconciliation-self-healing`

Build continuous cross-system drift detection and governed repair for Keycloak, Klyrow, Postal, middleware, n8n and Odoo.

This branch owns:

- expected-state snapshots;
- external-state adapters;
- reconciliation rules and findings;
- repair classification;
- dry-run repair plans;
- approval and step-up requirements;
- idempotent repair execution;
- integrity dashboards and Customer 360 reconciliation views.

### 4.5 `feat/klyrow-provider-mesh-portability`

Keep Postal 3.3.7 as the primary provider while adding a provider-neutral routing, health, failover-safety and configuration-portability foundation.

This branch owns:

- provider capability contracts;
- provider accounts backed by secret references;
- routing policies;
- provider health and circuit state;
- global message identity across providers;
- ambiguous-outcome reconciliation;
- controlled failover;
- signed configuration export/import and plan/apply workflows.

### 4.6 `feat/klyrow-reseller-white-label`

Build a secure reseller hierarchy, delegated administration, price books, margin and wallet ledgers, white-label branding and Odoo accounting synchronization.

This branch owns:

- reseller accounts and child-tenant relationships;
- price books and commercial versions;
- wholesale/retail margin calculation;
- prepaid credit and wallet controls;
- reseller commission metadata;
- delegated administration;
- branded portals and custom domains;
- reseller Customer 360 and billing views;
- Odoo reseller/customer/accounting mappings through middleware.

## 5. Shared authority boundaries

### Keycloak

Keycloak remains authoritative only for:

- passwords and credentials;
- verified email;
- MFA;
- OIDC sessions;
- social identity linkage;
- canonical human identity by `(issuer, subject)`.

Do not store communication decisions, billing, invoices, usage, margins, consent evidence or provider credentials in Keycloak.

### Klyrow

Klyrow remains authoritative for:

- organizations, tenants and memberships;
- roles and permissions;
- profiles and events;
- consent, preferences and suppressions;
- plans, subscriptions, usage and entitlements;
- policies and communication decisions;
- attention budgets;
- simulations;
- provider routing intent;
- reseller hierarchy and commercial rules;
- reconciliation state;
- integration state and audit evidence.

### Postal and future providers

Postal remains the primary delivery engine. Providers are authoritative only for their delivery-side identifiers and events. Provider callbacks never become authoritative for Klyrow tenancy, consent, billing or permissions.

### Middleware

Codestra middleware is the only boundary for communication with n8n and Odoo. All deliveries must use authenticated, versioned, idempotent contracts with correlation, causation, retries and replay protection.

### n8n

n8n may orchestrate notifications, reminders, reviews and support workflows. It cannot grant entitlements, change policy decisions, alter the usage ledger, assign platform ownership, bypass consent or directly write to Klyrow/Odoo/PostgreSQL databases.

### Odoo

Odoo is the owner's back-office management surface. It receives approved customer, subscription, usage, invoice, payment, credit, reseller and support records through middleware. Klyrow remains authoritative for real-time communication permission, usage reservation and delivery eligibility.

## 6. Shared communication lifecycle

All outbound paths must converge on the following lifecycle:

```text
request source
  -> communication intent
  -> authoritative tenant and permission resolution
  -> recipient/profile resolution
  -> consent, suppression and stream policy
  -> quota, entitlement and billing reservation
  -> attention-budget arbitration
  -> risk and sender/domain checks
  -> decision: ALLOW | DENY | DEFER | REQUIRE_APPROVAL | QUARANTINE
  -> immutable decision evidence
  -> provider outbox with decision ID
  -> provider acceptance/reconciliation
  -> signed message passport
  -> delivery and engagement events
  -> middleware domain events
  -> n8n/Odoo side effects
  -> end-to-end explanation timeline
```

No API, SMTP client, campaign, journey, AI action, n8n workflow, administrator or provider retry may bypass this lifecycle once the decision branch is enabled for that path.

## 7. Shared decision vocabulary

The platform must use stable machine-readable reason codes. Examples include:

```text
ALLOW_POLICY_SATISFIED
AUTHENTICATION_REQUIRED
TENANT_SUSPENDED
PERMISSION_DENIED
CAPABILITY_DISABLED
MARKETING_CONSENT_MISSING
TOPIC_UNSUBSCRIBED
GLOBAL_SUPPRESSION
HARD_BOUNCE_SUPPRESSION
COMPLAINT_SUPPRESSION
SENDER_NOT_AUTHORIZED
DOMAIN_NOT_VERIFIED
STREAM_SCOPE_MISMATCH
QUOTA_EXHAUSTED
BILLING_HOLD
ATTENTION_BUDGET_EXHAUSTED
QUIET_HOURS
LOWER_PRIORITY_COLLISION
RISK_REVIEW_REQUIRED
HUMAN_APPROVAL_REQUIRED
PROVIDER_UNAVAILABLE
PROVIDER_OUTCOME_AMBIGUOUS
```

Human-readable explanations may be localized, but stored reason codes remain stable and versioned.

## 8. Shared event catalog

The new branches must publish applicable versioned domain events through the shared event service. Minimum events include:

```text
communication.intent.created.v1
communication.decision.allowed.v1
communication.decision.denied.v1
communication.decision.deferred.v1
communication.approval.requested.v1
communication.approval.resolved.v1
message.passport.issued.v1
simulation.started.v1
simulation.completed.v1
attention.claim.created.v1
attention.claim.deferred.v1
recipient.preference.changed.v1
recipient.privacy_request.created.v1
recipient.abuse_report.created.v1
reconciliation.run.completed.v1
reconciliation.finding.created.v1
reconciliation.repair.approved.v1
reconciliation.repair.completed.v1
provider.route.selected.v1
provider.failover.requested.v1
provider.outcome.reconciled.v1
reseller.created.v1
reseller.price_book.published.v1
reseller.wallet.adjusted.v1
reseller.margin.recorded.v1
```

Events must not contain passwords, bearer tokens, API/SMTP secrets, private keys, full payment credentials or unnecessary message content.

## 9. Shared data requirements

Every new tenant-owned table must include:

- explicit tenant or platform scope;
- creation and update timestamps;
- stable ID;
- version or immutable-revision strategy where applicable;
- audit actor/service context;
- indexes for tenant and operational queries;
- tested tenant isolation;
- retention classification;
- no secret values unless using an approved encrypted secret store or secret reference.

Decision, consent, usage, margin, wallet and repair-evidence ledgers must be append-only or compensating rather than destructively overwritten.

## 10. Shared API requirements

New endpoints must preserve the existing `/v1` compatibility contract and include, where applicable:

- authoritative tenant resolution;
- explicit permissions;
- request IDs;
- idempotency keys;
- optimistic concurrency or immutable versions;
- RFC 7807-style errors;
- cursor pagination;
- stable filters and sort fields;
- OpenAPI examples;
- audit records;
- rate limits;
- no raw provider, n8n or Odoo credentials or internal administrator APIs.

## 11. Shared UI requirements

Use the Klyrow Vue 3 and TypeScript application and design system established by the earlier branches.

Required UX qualities:

- clean desktop, tablet and mobile layouts;
- accessible keyboard-complete navigation;
- WCAG 2.2 AA behavior;
- explainable status and reason text;
- preview and dry-run before dangerous actions;
- explicit confirmation for destructive or financially material actions;
- step-up authentication for high-risk owner actions;
- loading, empty, partial, stale, retrying and error states;
- cross-system correlation links without exposing secrets;
- English and Spanish interface strings.

## 12. Shared failure and safety behavior

- Klyrow requests must not block indefinitely on Postal, middleware, n8n or Odoo.
- Provider and external-system work must be asynchronous where retry is possible.
- Unknown provider outcome must enter reconciliation, not blind failover.
- n8n/Odoo outage must not block login, signup or normal Klyrow reads.
- Reconciliation may propose repairs but cannot silently execute destructive, financial, security or identity changes.
- Simulation must never enqueue real provider, middleware, n8n or Odoo work.
- White-label custom domains must not become active until DNS and TLS verification pass.
- Feature flags default to disabled for production tenants until migration, review and canary evidence are complete.

## 13. Branch dependencies

### Decision and policy ledger

Prerequisites:

- `feat/klyrow-auth-bff-sessions`
- `feat/klyrow-tenancy-onboarding`
- `feat/klyrow-consent-preferences`
- `feat/klyrow-billing-plans-usage`
- `feat/klyrow-stream-separation`
- `feat/klyrow-control-plane-events`

### Simulation and attention engine

Prerequisites:

- decision and policy ledger;
- segmentation;
- journeys;
- experimentation;
- analytics;
- billing.

### Recipient trust center

Prerequisites:

- consent/preferences;
- decision and policy ledger;
- content and message lifecycle;
- control-plane events.

### Reconciliation and self-healing

Prerequisites:

- Postal provisioning;
- integrations;
- billing;
- enterprise admin;
- control-plane events;
- Odoo synchronization.

### Provider mesh and portability

Prerequisites:

- Postal provisioning;
- deliverability;
- developer platform;
- stream separation;
- decision and policy ledger;
- control-plane events.

### Reseller and white label

Prerequisites:

- billing;
- enterprise admin;
- Odoo synchronization;
- provider mesh;
- decision and policy ledger.

## 14. Common test contract

Every new branch must include applicable:

- domain unit tests;
- PostgreSQL migration and integration tests;
- tenant and reseller isolation tests;
- API authorization tests;
- idempotency and optimistic-concurrency tests;
- worker lease, retry and recovery tests;
- provider/middleware/Odoo/n8n contract tests using mocks or isolated test services;
- browser and component tests;
- accessibility and keyboard tests;
- OpenAPI validation;
- feature-flag and backward-compatibility tests;
- failure-state and timeout tests;
- secret and PII leakage checks;
- dependency and container security scans.

Exact commands and exact results are required. Unit-test success alone does not establish production readiness.

## 15. PR delivery contract

Each branch must contain:

1. implementation;
2. additive migration;
3. downgrade or rollback plan;
4. unit tests;
5. PostgreSQL integration tests;
6. authorization and isolation tests;
7. worker/provider/integration contract tests;
8. frontend/browser/accessibility tests where applicable;
9. OpenAPI changes;
10. metrics and alerts;
11. operational runbooks;
12. domain-event catalog updates;
13. exact build and test evidence;
14. known limitations and blockers.

Do not combine these six branches into one large PR.

## 16. Production restriction

No new feature branch may deploy directly to production.

Production activation is allowed only through `release/klyrow-production-readiness` after reviewed merges, staging, migrations, rollback rehearsal, backup/restore evidence, security and tenant-isolation certification, Keycloak/middleware/n8n/Odoo/Postal preflight, billing reconciliation, restricted canary and explicit owner go/no-go.

The existence of a branch, passing unit tests or a Codex completion report is not production authorization.
