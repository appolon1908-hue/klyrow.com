# Klyrow Feature Missions for Codex

Read `KLYROW_MODERN_SAAS_PROGRAM.md` first. The common security, migration, testing, PR and release contracts in that file apply to every mission below.

Before implementing any mission, Codex must inventory the current code and mark each requirement as `IMPLEMENTED`, `PARTIAL`, `MISSING` or `UNSAFE`. Existing working behavior must be extended or migrated safely rather than duplicated.

---

## Mission 01 — Authentication theme and customer UI

**Branch:** `feat/klyrow-auth-theme-ui`

### Objective

Deliver a polished, responsive Klyrow authentication experience for email/password signup and Google sign-in through Keycloak.

### Required implementation

- Vue/TypeScript authentication shell or an equivalent progressively mounted frontend compatible with the existing portal.
- Login, signup, verify-email, resend-verification, forgot-password, reset-password, invitation-entry and logged-out states.
- Klyrow Keycloak login theme and email theme.
- English and Spanish strings.
- Password visibility, strength guidance, validation, disabled/loading states and server-error mapping.
- Google button that starts Keycloak identity brokering; never integrate the browser directly with a Google client secret.
- Responsive behavior at mobile, tablet and desktop widths.
- Full keyboard operation, visible focus, screen-reader labels, reduced-motion support and WCAG 2.2 AA checks.

### Critical tests

- Component tests for every state and validation path.
- Browser tests for login navigation, signup navigation, Google redirect initiation, reset flow entry and logout success state.
- Automated accessibility checks plus manual keyboard assertions.
- No OIDC tokens or secrets in browser storage.

### Exclusions

Do not implement token exchange, session cookies, Postal provisioning or production deployment in this branch.

---

## Mission 02 — OIDC BFF and secure sessions

**Branch:** `feat/klyrow-auth-bff-sessions`

### Objective

Replace browser-managed bearer tokens with a same-origin BFF using Authorization Code + PKCE S256 and opaque server-side sessions.

### Required implementation

- Endpoints for login start, callback, session status, refresh, logout and logout-all.
- Server-side storage of PKCE verifier, state, nonce and return URL with expiration and one-time use.
- OIDC issuer, signature, audience, azp, nonce and time-claim validation.
- Opaque `__Host-klyrow_session` cookie with `Secure`, `HttpOnly`, `Path=/` and appropriate SameSite behavior.
- CSRF protection for state-changing browser requests.
- Session rotation after login, privilege change and refresh.
- Refresh-token storage encrypted or protected at rest; never return it to the browser.
- Keycloak end-session flow and local session revocation.
- Session listing and revocation APIs.
- Migration path from the existing `sessionStorage` bearer-token portal without breaking non-browser API clients.

### Data contract

Persist session ID, identity ID, tenant context, created/last-seen/expires timestamps, rotation lineage, revoked timestamp, user agent hash and IP metadata appropriate to policy.

### Critical tests

State/nonce replay, PKCE mismatch, bad issuer/audience/azp, expired code/session, fixation, CSRF, logout, logout-all, concurrent refresh, cookie attributes and browser-storage scans.

---

## Mission 03 — Identity, tenancy and onboarding

**Branch:** `feat/klyrow-tenancy-onboarding`

### Objective

Make `(issuer, subject)` the canonical human identity and provide safe organization, membership, invitation and first-login onboarding flows.

### Required implementation

- Local identity record linked by canonical issuer and subject; email is profile data, not the immutable identity key.
- Organizations/workspaces, memberships, roles, invitations and organization switching.
- First-login transaction that either accepts a valid invitation or creates a single starter workspace idempotently.
- Onboarding state machine with resumable steps and completion evidence.
- Authoritative tenant resolution for every browser and API request.
- RBAC permissions rather than UI-only role checks.
- Invitation expiration, revocation, single use and email normalization.
- UI for workspace creation, invite acceptance, use-case selection, team invitations and onboarding checklist.

### Required endpoints

Identity/profile, organizations list/create/switch, members, invitations create/list/revoke/accept, onboarding read/update/complete and current authorization context.

### Critical tests

Cross-tenant access, duplicate callback/first login, invitation race, invitation for an existing identity, disabled membership, workspace switching, role enforcement and audit events.

---

## Mission 04 — Durable Postal provisioning

**Branch:** `feat/klyrow-postal-provisioning`

### Objective

Provision Postal resources asynchronously and idempotently after a Klyrow workspace is ready, without exposing Postal administration to customers.

### Required implementation

- Provider abstraction with a Postal 3.3.7 adapter.
- Klyrow-owned mappings for workspace to Postal organization/server/credential identifiers.
- Provisioning state machine: `PENDING`, `RUNNING`, `READY`, `RETRYABLE_FAILURE`, `BLOCKED`, `DISABLED`.
- Transactional outbox, worker leases, bounded retries, backoff, dead-letter visibility and manual retry.
- Idempotency keys for every provider-side create/update operation.
- Compensating behavior for partial provider success.
- Customer UI that shows provisioning progress without provider secrets.
- Platform-admin view for failures, retry and provider correlation IDs.
- Provider credentials loaded only from secret files or approved secret management.

### Critical tests

Duplicate jobs, worker crash after provider success, timeout ambiguity, provider 4xx/5xx, partial resource creation, retry exhaustion, disabled workspace and tenant mapping isolation.

### Exclusions

No direct Postal database writes, Postal source changes, unrestricted production sending or secret output.

---

## Mission 05 — Customer profiles and event platform

**Branch:** `feat/klyrow-customer-data-events`

### Objective

Provide a tenant-isolated customer data layer that supports multiple identifiers, profile merging and high-quality event ingestion.

### Required implementation

- Profiles with email, phone, external CRM ID, customer ID and custom attributes.
- Deterministic identity resolution and auditable merge rules.
- Immutable event records with event properties, source, occurred/received timestamps and idempotency.
- Profile timeline and lookup by any supported identifier.
- Single and batch ingestion APIs with validation and partial-failure reporting.
- CSV import/export jobs with secure object handling, progress and error reports.
- Retention configuration and deletion scheduling.
- Middleware/Odoo synchronization only through authenticated integration contracts.
- Modern profile list, profile detail, timeline, import and export UI.

### Critical tests

Tenant leakage, duplicate identifiers, merge races, repeated event IDs, out-of-order timestamps, malformed batches, large import recovery and retention boundaries.

---

## Mission 06 — Consent, preferences and compliance center

**Branch:** `feat/klyrow-consent-preferences`

### Objective

Make consent and recipient preferences enforceable product rules rather than display-only metadata.

### Required implementation

- Append-only consent evidence including source, timestamp, policy/version, actor and proof metadata.
- Global and topic-level subscription preferences.
- Double opt-in workflow where configured.
- Signed, expiring and single-purpose unsubscribe/preference links.
- Hard-bounce, complaint and abuse suppressions.
- Send-time policy service used by every marketing path.
- Data export and deletion-request workflows with review, execution and audit state.
- Tenant retention policies.
- Public preference center and authenticated compliance administration UI.

### Critical tests

Unsubscribed marketing recipient, transactional policy boundaries, replayed preference token, consent revocation race, suppression precedence, cross-tenant token misuse, export authorization and deletion safety.

---

## Mission 07 — Segmentation engine

**Branch:** `feat/klyrow-segmentation`

### Objective

Build dynamic, manual and exclusion segments over profile, event, engagement and consent data.

### Required implementation

- Versioned rule AST supporting nested AND/OR/NOT.
- Attribute, identifier, event occurrence/count/property, time-window, engagement, geography and integration-fed fields.
- Safe query compilation using parameterized SQL; no user-authored SQL.
- Preview with estimated count, sample profiles and explainable rule output.
- Materialized or incremental evaluation strategy appropriate to scale.
- Suppression and consent awareness.
- Revision history and references showing campaigns/journeys that use a segment.
- Visual rule builder with accessible keyboard interactions and JSON advanced view.

### Critical tests

Nested rules, time zones, null semantics, event windows, concurrent edits, invalid AST, tenant isolation, estimate accuracy bounds and suppression-aware membership.

---

## Mission 08 — Template and content studio

**Branch:** `feat/klyrow-content-studio`

### Objective

Create a modern content experience for reusable, responsive and safely rendered email.

### Required implementation

- Template definitions and immutable versions.
- HTML and plain-text content, reusable blocks, brand styles and media references.
- Visual editor with advanced HTML mode and responsive preview.
- Variable schema, sample data, personalization and conditional content.
- Server-side rendering and HTML sanitization.
- Link tracking preparation and safe URL validation.
- Test-send workflow restricted to verified/authorized senders and safe recipients.
- Clone, archive, restore and version comparison.
- Mobile/desktop preview and accessible editor controls.

### Critical tests

Stored/reflected XSS, unsafe URLs, missing variables, escaping, conditional content, tenant media leakage, version immutability and test-send gates.

---

## Mission 09 — Journey and automation engine

**Branch:** `feat/klyrow-journeys-automation`

### Objective

Provide a versioned visual journey engine with durable execution and per-profile traceability.

### Required implementation

- Draft journey, immutable published version and rollback to a prior definition.
- Nodes for trigger, segment entry, event, wait/delay, wait-until, email, condition, percentage split, experiment branch, goal, profile update, webhook, middleware event, segment mutation, unsubscribe/suppress and exit.
- Durable run state, scheduled wakeups, leases, idempotent node execution and retry policy.
- Pause/resume/stop semantics at journey and run level.
- Entry deduplication and re-entry policy.
- Conversion goals and exit criteria.
- Visual graph builder, validation, publish review and troubleshooting timeline.

### Critical tests

Worker crash/replay, clock/time-zone behavior, duplicate trigger, branch determinism, pause during wait, goal completion, webhook retry, suppression before send and version isolation.

---

## Mission 10 — Experimentation and optimization

**Branch:** `feat/klyrow-experimentation`

### Objective

Support auditable experiments for subject, sender, content, CTA and send time without overstating statistical certainty.

### Required implementation

- Experiment definitions, variants, allocation, holdout and success metric.
- Deterministic tenant/profile assignment stable across retries.
- Start, pause, conclude and cancel lifecycle.
- Winner evaluation with sample size, confidence/credible interval and explicit inconclusive state.
- Manual or policy-approved winner application; never silently change live content without audit.
- Exposure and outcome events.
- UI for setup, monitoring, comparison and decision history.

### Critical tests

Allocation distribution, assignment stability, mutually exclusive exposures, late events, small samples, no-winner case, metric changes and tenant isolation.

---

## Mission 11 — Analytics and attribution

**Branch:** `feat/klyrow-analytics-attribution`

### Objective

Build trustworthy dashboards from real internal events for delivery, engagement, campaigns, journeys and tenant usage.

### Required implementation

- Canonical event/fact definitions for accepted, queued, sent, delivered, deferred, bounced, complained, unsubscribed, opened and clicked.
- Unique and total engagement metrics with bot/privacy caveats.
- Campaign, segment, journey, domain, stream and time filters.
- Conversion and revenue attribution only when supplied by the tenant; never invent revenue.
- Cohort and trend views where evidence supports them.
- Incremental aggregation jobs with rebuild/reconciliation path.
- Export and API access.
- Accessible dashboard cards, charts, tables, comparisons and empty/error states.

### Critical tests

Metric definitions, duplicate provider events, late-arriving events, time zones, aggregation replay, source reconciliation, tenant isolation and export authorization.

---

## Mission 12 — Deliverability command center

**Branch:** `feat/klyrow-deliverability`

### Objective

Give customers and operators actionable visibility into domain, DNS, TLS, queue and reputation-related signals.

### Required implementation

- SPF, DKIM, DMARC, MX, tracking, return-path, TLS and PTR/rDNS status checks.
- Domain verification history and next-action guidance.
- Bounce, complaint, defer, block, latency, suppression and volume metrics by tenant/domain/stream where available.
- Alert rules for verification loss, certificate expiry, spikes, queue backlog and suspension.
- Conservative sending-ramp guidance for explicit opt-in traffic; no evasion or provider-bypass logic.
- Domain suspension and controlled re-enable workflow.
- Customer dashboard plus platform operations view.

### Critical tests

DNS timeout/changes, stale cache, malformed records, alert deduplication, threshold windows, domain suspension enforcement and no cross-tenant metrics.

---

## Mission 13 — Developer platform

**Branch:** `feat/klyrow-developer-platform`

### Objective

Provide a first-class developer experience for REST, SMTP and webhooks without exposing provider internals.

### Required implementation

- Scoped API keys with prefix, hash, environment, expiry, last-used data, IP restrictions and rotation/revocation.
- Scoped SMTP credentials with one-time secret display.
- Webhook endpoints, event subscriptions, signing, attempts, logs, retry, manual resend and replay protection.
- Request IDs, idempotency, rate-limit headers and consistent errors.
- Sandbox/test mode and simulated provider events clearly marked as test data.
- OpenAPI explorer and code examples for curl, JavaScript/TypeScript, Python and PHP.
- Developer UI for credentials, webhooks, logs and docs.

### Critical tests

Secret hashing/non-retrieval, scope denial, expiration, rotation race, IP policy, webhook signature, replay, retry schedule, idempotent resend and sandbox isolation.

---

## Mission 14 — Integration framework

**Branch:** `feat/klyrow-integrations`

### Objective

Create a connector framework for authenticated, observable and recoverable data movement.

### Required implementation

- Connector registry, installation, configuration schema, credential references, capabilities and status.
- Durable sync jobs, checkpoints/cursors, retries, dead-letter visibility and reconciliation.
- Initial adapters for Codestra middleware/Odoo, n8n, Google-authorized workflows, generic webhook, CSV and generic REST.
- Google integration must request only the scopes required by the selected workflow; Gmail is not the bulk delivery engine.
- Field mapping, dry run, test connection, sync history and error details.
- Per-tenant encryption/secret references and permission checks.
- Integration marketplace-style UI.

### Critical tests

Credential isolation, cursor replay, partial page failure, rate limiting, revoked authorization, mapping errors, duplicate records, SSRF protections and tenant isolation.

---

## Mission 15 — Billing, plans and usage

**Branch:** `feat/klyrow-billing-plans-usage`

### Objective

Build a provider-agnostic SaaS billing foundation with accurate entitlement and usage enforcement.

### Required implementation

- Plans and versions with message, profile, seat, API and optional feature limits.
- Subscription states: trial, active, past due, suspended, canceled and scheduled change.
- Append-only usage ledger with source/reference and reconciliation.
- Meter aggregation and quota enforcement with documented transactional behavior.
- Invoice metadata, line items, taxes/discount placeholders, credits and adjustments.
- Payment-provider adapter interface and signed durable webhook inbox.
- Customer billing portal, plan comparison, usage, invoice history and payment-method handoff.
- Platform administration for plans, credits and reconciliation.
- Test mode that cannot create real charges.

### Critical tests

Usage deduplication, concurrent quota claims, plan change proration policy, webhook replay/out-of-order events, credit audit, suspended entitlement, seat limit and zero real billing during tests.

---

## Mission 16 — AI-assisted workflows

**Branch:** `feat/klyrow-ai-assist`

### Objective

Add optional, controlled AI assistance for content and operational insight without autonomous sending or undisclosed data transfer.

### Required implementation

- Provider-neutral interface and disabled-by-default tenant configuration.
- Explicit provider/region/model configuration and tenant consent.
- Capabilities for subject suggestions, draft, rewrite, campaign summary, segment rule draft, journey draft, send-time recommendation and anomaly explanation.
- Structured outputs validated before use.
- Redaction/minimization controls and policy for external providers.
- Human review and explicit apply action; never send or publish automatically.
- Usage limits, audit events and cost metadata where available.
- Clear AI-generated labeling and feedback controls.

### Critical tests

Disabled tenant, unsupported provider, malformed output, prompt injection through tenant content, sensitive-data redaction, rate/cost limits, no autonomous send and audit completeness.

---

## Mission 17 — Enterprise controls and admin operations

**Branch:** `feat/klyrow-enterprise-admin`

### Objective

Provide mature organization security and a safe platform operations center.

### Required implementation

- Explicit permission catalog and role definitions for owner, admin, developer, marketer/operator, analyst/read-only, billing and support.
- MFA/TOTP enrollment and recovery, session policy and revocation.
- Organization security policy, allowed domains and enterprise SSO extension points.
- Immutable audit trail with filters/export and retention.
- Tenant suspension, sending suspension, credential revocation and reason/evidence.
- Support access/impersonation only if implemented with approval, time limit, banner, reason and full audit; never expose secrets.
- Operations dashboard for tenant health, queues, domains, risk, billing, webhook failures and service health.

### Critical tests

Privilege escalation, owner protection, MFA recovery, support access expiration, audit tamper resistance, suspension enforcement and platform-admin tenant boundaries.

---

## Mission 18 — Marketing and transactional stream separation

**Branch:** `feat/klyrow-stream-separation`

### Objective

Separate marketing and transactional traffic operationally while preserving mandatory abuse and legal safeguards.

### Required implementation

- Stream definitions and policy engine.
- Separate API/SMTP scopes, credentials, sender/domain eligibility, quotas and analytics.
- Marketing path requires consent/topic preference and suppression checks.
- Transactional path may apply different topic rules but cannot bypass complaint, abuse, hard-bounce, account or provider safety restrictions.
- Separate queue/routing metadata and optional provider pools where configured.
- UI that makes stream choice and policy consequences clear.

### Critical tests

Marketing without consent, transactional misuse, wrong credential scope, sender/domain mismatch, stream quota, suppression precedence and analytics separation.

---

## Mission 19 — Reliability and high availability

**Branch:** `feat/klyrow-reliability-ha`

### Objective

Make the current server a scale-out node rather than a permanent single point of failure.

### Required implementation

- Stateless API nodes where practical and centralized session/state storage.
- Worker leases with heartbeat, expiration, retry and duplicate-safe execution.
- Graceful shutdown, readiness/liveness, connection draining and maintenance mode.
- Queue scaling and backpressure.
- Database backup, restore, replica/readiness guidance and tested recovery.
- Postal/Mautic worker scaling guidance without unsafe shared-state assumptions.
- Rolling deployment and rollback runbooks.
- Resource requests/limits and capacity signals.

### Critical tests

Worker kill/restart, lease expiry, duplicate delivery protection, API-node loss, queue backlog recovery, maintenance behavior, backup restore and rollback rehearsal.

---

## Mission 20 — Observability and SRE

**Branch:** `feat/klyrow-observability-sre`

### Objective

Provide actionable telemetry, alerts and runbooks for the full SaaS path.

### Required implementation

- Structured logs with request, tenant-safe, actor, job and provider correlation IDs.
- Metrics for API latency/errors, auth, sessions, queues, outbox/inbox, workers, Postal, Mautic, billing, DNS/TLS, webhooks, campaigns and journeys.
- Dashboards for customer-safe analytics and operator infrastructure views.
- Alert rules with severity, deduplication, runbook link and actionable thresholds.
- SLO/SLI definitions for API availability, queue latency and webhook delivery.
- Health and readiness endpoints that distinguish dependencies.
- Runbooks for common incidents and data reconciliation.

### Critical tests

Metrics cardinality bounds, no secrets/PII in logs, alert expression tests, dependency failure readiness, correlation propagation and dashboard provisioning validation.

---

## Mission 21 — Security hardening

**Branch:** `feat/klyrow-security-hardening`

### Objective

Certify the integrated product against common web, API, container, provider and supply-chain risks.

### Required implementation

- Updated threat model and trust-boundary diagrams.
- CSP, HSTS where appropriate, secure headers, CSRF, origin checks and cookie hardening.
- SSRF defenses with DNS/IP revalidation and redirect policy.
- Rate limiting for authentication, APIs, imports, webhooks and expensive queries.
- Input/output validation, HTML sanitization and upload controls.
- Secret file/manager usage, rotation procedures and secret scanning.
- Dependency, container and image scanning; pinned/reproducible builds and SBOM/provenance where supported.
- Non-root/read-only containers, network isolation and least privilege.
- Security regression tests for every discovered issue.

### Critical tests

Cross-tenant IDOR, privilege escalation, CSRF, XSS, SSRF including DNS rebinding scenarios, webhook forgery/replay, brute force, resource exhaustion, unsafe file upload and secret leakage.

---

## Mission 22 — Cross-channel middleware contract

**Branch:** `feat/klyrow-cross-channel-contract`

### Objective

Prepare a clean, separately permissioned contract for a future Klyrow journey event to request a Telnexa SMS action through middleware.

### Required implementation

- Versioned event envelope with event ID, tenant, actor/service, correlation, causation, occurred time, purpose, consent context and payload schema.
- Outbox-backed middleware delivery with mTLS/service authentication, retries and dead-letter visibility.
- Permission/capability gate separate from Klyrow email permissions.
- Delivery-result inbox and journey correlation.
- Contract tests and example schemas.
- No direct Telnexa database or internal administrative API access.

### Critical tests

Unauthorized capability, duplicate event, replayed result, tenant mismatch, middleware timeout, schema evolution and consent/purpose propagation.

### Exclusion

Do not merge Klyrow and Telnexa products or enable live SMS in this branch.

---

## Mission 23 — Production readiness and controlled release

**Branch:** `release/klyrow-production-readiness`

### Objective

Integrate only reviewed feature work, certify it in staging and produce a controlled production release with rollback.

### Required implementation and evidence

- Exact release commit and immutable artifact identifiers.
- Full migration order, compatibility window and rollback decision points.
- Complete unit, integration, browser, accessibility, security and tenant-isolation results.
- Staging deployment and smoke/end-to-end evidence.
- Backup and restore evidence with measured RTO/RPO.
- DNS, PTR/rDNS, TLS, Postal, middleware, Keycloak, queue, database and observability preflight.
- Controlled canary restricted by tenant, sender, recipient and maximum deliveries.
- Monitoring during canary and automatic/manual stop criteria.
- Owner go/no-go record.
- Production rollout, post-deploy validation and rollback commands.

### Hard gate

Codex must not perform production activation merely because this branch exists. Production requires explicit owner authorization after the complete go/no-go packet is presented. Missing secrets, external DNS/PTR, reviewer approvals or provider credentials remain blockers and must never be fabricated or bypassed.

---

# Completion report required for every branch

Codex must report:

1. repository and current directory;
2. branch;
3. starting SHA;
4. final SHA;
5. every commit created;
6. every changed file;
7. implemented, retained, migrated and deferred behavior;
8. migration and rollback details;
9. exact targeted test commands/results;
10. exact full-suite commands/results;
11. lint, type-check, build, accessibility, security and secret-scan results;
12. OpenAPI and documentation changes;
13. known blockers and risks;
14. confirmation of tenant-isolation coverage;
15. confirmation that no secrets were printed or committed;
16. confirmation that no unauthorized deployment, merge, service restart, credential rotation or production activation occurred.
