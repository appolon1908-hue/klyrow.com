# Klyrow Modern Email SaaS — Implementation Program

## 1. Program objective

Evolve Klyrow into a modern, secure, multi-tenant email SaaS while preserving the existing production safety controls and Postal 3.3.7 delivery boundary.

This program is designed for Codex execution. Every feature family has its own implementation branch and mission document. Each branch must remain independently reviewable and must not deploy directly to production.

The intended product includes:

- polished customer authentication and onboarding;
- transactional and marketing email operations;
- customer profiles, events, consent and preferences;
- segmentation, campaigns, templates and automation journeys;
- experiments, analytics and attribution;
- deliverability operations;
- developer APIs, SMTP credentials and webhooks;
- integrations, AI assistance, billing and enterprise administration;
- reliability, observability, security and controlled production release.

## 2. Fixed platform boundaries

### Canonical components

- Identity: Keycloak at `https://auth.codestra.co/realms/codestra`
- Delivery engine: Postal 3.3.7
- Application API/BFF: FastAPI under `apps/gateway`
- Authoritative SaaS data: Klyrow PostgreSQL
- Queueing: RabbitMQ and durable database outbox/inbox patterns
- Campaign integration: Mautic only through a Klyrow-owned adapter
- Middleware integration: through authenticated APIs/events; never direct Odoo database access
- Monitoring: Prometheus/Grafana-compatible metrics and structured logs

### Non-negotiable restrictions

- Do not expose Postal or Mautic administrator APIs to customer browsers.
- Do not write directly to Postal or Odoo databases.
- Do not store OIDC access or refresh tokens in browser storage.
- Do not use OAuth password grant or Keycloak Direct Access Grants.
- Do not add a second Klyrow password database for production users.
- Do not weaken tenant isolation, consent enforcement, suppression enforcement or production delivery gates.
- Do not enable unrestricted production sending from a feature branch.
- Do not deploy, merge, restart services, rotate credentials or alter production DNS while implementing an ordinary feature PR.

## 3. Target architecture

### Frontend

Introduce a modern customer application under `apps/web` using Vue 3 and TypeScript. Use progressive migration so the existing portal remains available until the replacement routes pass acceptance testing.

The frontend must provide:

- responsive desktop, tablet and mobile layouts;
- keyboard-complete navigation;
- accessible labels, focus states, errors and status announcements;
- reusable design-system primitives;
- loading, empty, error, permission-denied and suspended-account states;
- optimistic interaction only where rollback behavior is clear;
- no direct Postal, Mautic, database or secret access.

### Backend

The FastAPI application remains the public BFF/API boundary. Feature modules should be split by domain rather than expanding a single monolithic file indefinitely.

Preferred module structure:

```text
apps/gateway/app/
├── api/
├── auth/
├── tenancy/
├── billing/
├── profiles/
├── consent/
├── segments/
├── content/
├── campaigns/
├── journeys/
├── experiments/
├── analytics/
├── deliverability/
├── developer/
├── integrations/
├── ai/
├── admin/
├── providers/
├── workers/
└── observability/
```

Existing working endpoints may be retained, wrapped and migrated incrementally. Do not break existing callers without a versioned migration plan.

### Data and execution

- PostgreSQL is authoritative for tenant, user, workspace, configuration, customer data, billing metadata and product workflow state.
- Provider operations use idempotent jobs and a durable outbox.
- Provider callbacks use signed verification, replay protection and a durable inbox.
- Long-running or retryable operations never block browser requests.
- Every tenant-owned table must have an explicit tenant key and tested isolation.

## 4. Product design system

Use a clean Klyrow visual language:

- calm neutral surfaces with a strong blue/violet primary accent;
- readable typography and generous spacing;
- left navigation on desktop and compact navigation on mobile;
- consistent page headers, filters, tables, cards, drawers, modals and toasts;
- destructive actions require explicit confirmation;
- dangerous production actions use a second confirmation and permission check;
- important states use both text and iconography, never color alone.

Required reusable components include:

- application shell and responsive navigation;
- page header and breadcrumbs;
- button, input, select, combobox, date/time controls and code editor wrappers;
- data table with sorting, filtering, pagination and accessible row actions;
- empty state, skeleton, inline alert, toast and error boundary;
- modal, drawer and confirmation dialog;
- metric card, chart container and status badge;
- permission guard and feature/capability guard;
- domain/DNS record display with copy buttons;
- code sample tabs for curl, JavaScript, Python and PHP.

## 5. Shared API contract

Preserve existing `/v1` compatibility while organizing new endpoints consistently.

All APIs must support, where applicable:

- authentication and authoritative tenant resolution;
- explicit permission checks;
- `X-Request-ID` propagation;
- structured RFC 7807-style errors;
- cursor pagination for large collections;
- stable filtering and sorting contracts;
- idempotency keys for externally visible writes;
- optimistic concurrency through version fields or ETags;
- audit records for sensitive mutations;
- rate limiting with clear retry information;
- OpenAPI examples and documented error responses.

No API may trust a tenant identifier supplied by the browser without validating membership and permissions.

## 6. Database and migration contract

Every branch that changes persistence must include:

1. additive forward migration;
2. deterministic downgrade or a documented irreversible boundary;
3. indexes and unique constraints for the intended access pattern;
4. tenant-isolation constraints where practical;
5. migration tests against PostgreSQL;
6. compatibility with rolling deployment when required;
7. no production data deletion as part of normal migration.

Schema changes and code changes must be deployable in a safe order.

## 7. Common test contract

Each feature branch must include the applicable tests below:

- unit tests for domain rules;
- API authorization and tenant-isolation tests;
- PostgreSQL integration tests;
- worker retry, lease, idempotency and recovery tests;
- provider adapter contract tests with mocked external boundaries;
- frontend component tests;
- browser tests for the critical user journey;
- accessibility checks and keyboard navigation tests;
- OpenAPI validation;
- secret scanning and dependency/security scanning;
- migration upgrade/downgrade tests;
- failure-state tests, not only success paths.

The completion report must show exact commands and exact results. A green CI run is evidence, not independent approval.

## 8. Branch and dependency catalog

All implementation branches start from this planning baseline for their mission document. Before implementation, Codex must rebase or recreate the branch from the latest reviewed prerequisite baseline shown below.

### Foundation

1. `feat/klyrow-auth-theme-ui`
   - Klyrow login, signup, verification, reset and logout experience.
   - Prerequisite: documentation baseline.

2. `feat/klyrow-auth-bff-sessions`
   - Authorization Code + PKCE BFF, opaque cookies, CSRF, callback and logout.
   - Prerequisite: branch 1 merged.

3. `feat/klyrow-tenancy-onboarding`
   - Canonical identities, organizations, memberships, invitations and onboarding.
   - Prerequisite: branch 2 merged.

4. `feat/klyrow-postal-provisioning`
   - Durable, idempotent Postal organization/server/credential provisioning.
   - Prerequisite: branch 3 merged.

### Core product

5. `feat/klyrow-customer-data-events`
   - Profiles, identity resolution, event ingestion, timelines and import/export.
   - Prerequisite: branch 3 merged.

6. `feat/klyrow-consent-preferences`
   - Consent ledger, subscription topics, preference center, unsubscribe and deletion/export workflows.
   - Prerequisite: branches 3 and 5 merged.

7. `feat/klyrow-segmentation`
   - Dynamic/manual/exclusion segments, previews, estimates and safe evaluation.
   - Prerequisite: branches 5 and 6 merged.

8. `feat/klyrow-content-studio`
   - Templates, reusable blocks, brand styles, editor, previews and test sends.
   - Prerequisite: branches 4 and 6 merged.

9. `feat/klyrow-journeys-automation`
   - Versioned visual automation graph, triggers, waits, actions, goals and run history.
   - Prerequisite: branches 5 through 8 merged.

10. `feat/klyrow-experimentation`
    - A/B definitions, deterministic assignment, holdouts, winner calculation and auditability.
    - Prerequisite: branches 8 and 9 merged.

11. `feat/klyrow-analytics-attribution`
    - Delivery, engagement, campaign, journey, cohort and supplied-revenue attribution views.
    - Prerequisite: branches 5, 8, 9 and 10 merged.

12. `feat/klyrow-deliverability`
    - DNS/TLS/PTR checks, domain health, queue metrics, alerts and conservative ramp guidance.
    - Prerequisite: branch 4 merged.

### Platform and commercial

13. `feat/klyrow-developer-platform`
    - Scoped API keys, SMTP credentials, webhook management, logs, replay, docs and sandbox events.
    - Prerequisite: branches 2 through 4 merged.

14. `feat/klyrow-integrations`
    - Connector framework for middleware/Odoo, n8n, Google-authorized workflows, webhook, CSV and REST.
    - Prerequisite: branches 5, 6 and 13 merged.

15. `feat/klyrow-billing-plans-usage`
    - Plans, subscriptions, trials, seats, allowances, usage ledger, invoices, credits and provider abstraction.
    - Prerequisite: branch 3 merged.

16. `feat/klyrow-ai-assist`
    - Optional provider abstraction for drafting, rewriting, segments, journeys and anomaly explanations.
    - Prerequisite: branches 7 through 11 merged.

17. `feat/klyrow-enterprise-admin`
    - RBAC, MFA/session controls, audit, suspension, support tooling and platform operations center.
    - Prerequisite: branches 2, 3, 12 and 15 merged.

18. `feat/klyrow-stream-separation`
    - Separate transactional and marketing credentials, policy, quota, analytics and sender paths.
    - Prerequisite: branches 4, 6, 11 and 13 merged.

### Operations and release

19. `feat/klyrow-reliability-ha`
    - Stateless scale-out, worker leases, graceful shutdown, maintenance mode, backup/restore and rollout design.
    - Prerequisite: major product branches merged.

20. `feat/klyrow-observability-sre`
    - Metrics, dashboards, alerts, structured logging, traces/correlation and runbooks.
    - Prerequisite: branch 19 merged.

21. `feat/klyrow-security-hardening`
    - CSP, CSRF, session hardening, SSRF, rate limits, secret lifecycle, container and supply-chain controls.
    - Prerequisite: all product branches merged.

22. `feat/klyrow-cross-channel-contract`
    - Separately permissioned middleware contract for future Klyrow journey to Telnexa SMS events.
    - Prerequisite: branches 9 and 14 merged.

23. `release/klyrow-production-readiness`
    - Full integration certification, staging deployment, backup/restore evidence, canary, rollback and owner go/no-go.
    - Prerequisite: reviewed merges of all release-scoped feature PRs.

## 9. Required PR delivery contract

Every feature is delivered as a separate pull request containing all applicable items:

1. implementation;
2. additive migration;
3. downgrade/rollback plan;
4. unit tests;
5. PostgreSQL integration tests;
6. security and tenant-isolation tests;
7. frontend/component/browser/accessibility tests;
8. OpenAPI changes;
9. operational documentation;
10. monitoring and alert changes;
11. exact test and build evidence;
12. known limitations and remaining blockers.

Do not bundle unrelated feature branches into one large PR.

## 10. Release governance

Feature branches may be built and tested locally and in isolated CI. They must not directly deploy to production.

Required path:

```text
feature branch
  -> targeted tests
  -> complete CI
  -> independent review
  -> merge into reviewed integration baseline
  -> staging deployment
  -> staging migration and smoke tests
  -> security and tenant-isolation certification
  -> backup/restore verification
  -> controlled canary
  -> owner go/no-go
  -> production rollout
  -> post-deploy verification
```

Production email delivery remains gated until DNS, PTR/rDNS, TLS, suppression, consent, provider connectivity and owner-approved canary evidence pass.

## 11. Codex branch execution protocol

For every feature branch, Codex must:

1. read this program and the branch-specific mission completely;
2. print repository, branch, starting SHA and clean/dirty status;
3. inventory existing related code before editing;
4. identify what is already implemented, partial, missing or unsafe;
5. update the branch from its reviewed prerequisites;
6. implement only the mission scope;
7. create logical commits;
8. run targeted and complete checks;
9. push the branch and open/update its PR;
10. provide the required completion report;
11. stop on missing external credentials or destructive production operations.

No completion report may call a branch production-ready merely because unit tests pass.

## 12. Program definition of done

Klyrow is considered ready for a production release only when:

- all selected feature PRs are independently reviewed and merged;
- tenant isolation and authorization tests pass across every domain;
- signup, login, logout, onboarding and invitation flows pass browser tests;
- Postal provisioning and callbacks are durable and idempotent;
- marketing sends enforce consent, preferences and suppressions;
- transactional traffic still enforces abuse and mandatory safety controls;
- billing usage is reconcilable and does not charge during tests;
- observability and alerts cover critical queues and dependencies;
- backup/restore and rollback evidence is current;
- staging and canary evidence is complete;
- no secrets are committed;
- production activation receives an explicit owner go/no-go decision.
