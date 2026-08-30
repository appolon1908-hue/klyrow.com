# Klyrow Differentiated Feature Missions for Codex

Read these files completely before implementing any mission in this document:

1. `KLYROW_CODEX_EXECUTION_INDEX.md`
2. `KLYROW_AUTH_CODEX_SPEC.md` and every linked authentication part
3. `KLYROW_MODERN_SAAS_PROGRAM.md`
4. `docs/implementation/KLYROW_FEATURE_MISSIONS.md`
5. `KLYROW_IDENTITY_AUTOMATION_ODOO_CONTROL_PLANE.md`
6. `docs/implementation/KLYROW_CONTROL_PLANE_BRANCH_MISSIONS.md`
7. `docs/implementation/KLYROW_ADMIN_ODOO_N8N_ACCEPTANCE_MATRIX.md`
8. `KLYROW_DIFFERENTIATED_FEATURES_PROGRAM.md`
9. this document

Before editing, inventory existing related code and mark every requirement `IMPLEMENTED`, `PARTIAL`, `MISSING` or `UNSAFE`. Extend working behavior rather than duplicating it.

---

# Mission 26 — Communication Decision and Policy Ledger

**Branch:** `feat/klyrow-decision-policy-ledger`

## Objective

Create the mandatory pre-send authorization layer and immutable causal ledger behind every outbound message. The feature must explain why a communication was requested, which policy evaluated it, which evidence was used, whether it was allowed, what entitlement or quota it consumed and what happened afterward.

## Required backend modules

Prefer domain modules such as:

```text
apps/gateway/app/decisions/
├── api.py
├── models.py
├── schemas.py
├── service.py
├── policy.py
├── approvals.py
├── evidence.py
├── passports.py
├── permissions.py
└── events.py
```

Do not add more unrelated behavior to the existing monolithic gateway files when a domain module is practical.

## Required data model

Additive PostgreSQL migrations must define an appropriate form of:

### `communication_intents`

- `id`
- `tenant_id`
- `idempotency_key`
- `source_kind` such as API, SMTP, campaign, journey, security, support, system or admin
- `source_reference`
- `requested_by_identity_id` or service account
- `profile_id` and recipient normalization reference
- `purpose`
- `stream`
- `template_id` and immutable template version
- requested sender/domain
- requested/scheduled timestamps
- request payload hash
- state
- created timestamp

### `policy_bundles`

- tenant or platform scope
- stable key and display name
- active version ID
- status
- default/fallback behavior

### `policy_versions`

- immutable version number
- validated rule document
- effective period
- created by
- published by
- publication timestamp
- content hash
- superseded reference

### `decision_records`

- immutable ID
- intent ID
- tenant ID
- policy version ID
- decision: `ALLOW`, `DENY`, `DEFER`, `REQUIRE_APPROVAL` or `QUARANTINE`
- stable reason codes
- input fact snapshot hash
- evaluated timestamp
- valid-until timestamp where applicable
- approval requirement
- usage/billing reservation reference
- attention decision reference when available
- risk decision reference when available
- engine version

### `decision_evidence`

Store references and safe snapshots for:

- membership/permission decision;
- consent evidence;
- preference state;
- suppression state;
- sender/domain verification;
- stream and credential scope;
- quota/entitlement state;
- billing hold or reservation;
- quiet hours/frequency state;
- risk state;
- approval state.

Do not copy secrets or unnecessary message content.

### `communication_approvals`

- decision or intent ID
- required permission
- reason
- requested by
- requested/expired/resolved timestamps
- resolver identity
- outcome
- step-up authentication evidence reference
- immutable resolution note

### `message_passports`

- message ID
- decision ID
- tenant ID
- purpose and stream
- sender domain
- template version/hash
- policy version/hash
- provider name and provider reference
- accepted and final timestamps
- canonical lifecycle hash
- signing key ID
- signature

The passport must exclude body content and raw recipient PII where possible.

## Required decision rules

The evaluator must support, at minimum:

1. authenticated actor/service;
2. authoritative tenant resolution;
3. permission/capability;
4. tenant/account suspension;
5. stream and credential scope;
6. sender authorization and verified domain;
7. marketing consent and topic preference;
8. global, complaint, hard-bounce and abuse suppressions;
9. plan entitlement and feature availability;
10. quota and atomic usage reservation;
11. billing hold and account state;
12. quiet hours and recipient time zone;
13. recipient frequency limits;
14. campaign/journey collision hooks;
15. risk-review hooks;
16. production delivery gates;
17. human approval requirements.

Evaluation must fail closed if required authoritative facts are unavailable.

Mutable facts such as suspension, suppression and consent must be revalidated immediately before provider enqueue, even if an earlier decision exists.

## Required APIs

Use versioned endpoints with permissions, idempotency and OpenAPI examples. Include an appropriate form of:

```text
POST   /v1/communication-intents
POST   /v1/communication-intents/{id}/evaluate
GET    /v1/communication-intents/{id}
GET    /v1/communication-decisions/{id}
GET    /v1/communication-decisions
GET    /v1/messages/{message_id}/explanation
GET    /v1/messages/{message_id}/passport
GET    /v1/policies
POST   /v1/policies
POST   /v1/policies/{id}/versions
POST   /v1/policies/{id}/versions/{version}/validate
POST   /v1/policies/{id}/versions/{version}/publish
POST   /v1/policies/{id}/versions/{version}/simulate
GET    /v1/communication-approvals
POST   /v1/communication-approvals/{id}/approve
POST   /v1/communication-approvals/{id}/deny
```

Do not trust a browser-supplied tenant ID. Approval endpoints require step-up authentication for platform, billing, risk or production exceptions.

## Required integration

- API sends, SMTP relay, campaigns, journeys, AI-assisted actions and administrative test sends must reference a valid decision before provider enqueue.
- The Postal adapter must receive the Klyrow message ID and decision correlation without exposing the decision internals to Postal.
- Domain events must be published through the shared control-plane service.
- Odoo may receive safe communication/audit summaries through middleware, not direct calls.
- n8n may react to approval or denial events but cannot change the decision record directly.

## Required UI

### Tenant policy center

- policy list;
- draft and published versions;
- readable rule editor plus advanced JSON view;
- validation errors;
- dry-run preview;
- version comparison;
- publication confirmation;
- affected send paths;
- rollback to a prior version by creating a new version.

### Decision explorer

- filters by time, tenant-authorized scope, decision, reason, source, campaign, journey, profile, sender/domain and message;
- causal timeline;
- safe evidence details;
- links to consent, usage, billing, provider and integration records;
- explanation of `DENY`, `DEFER`, `REQUIRE_APPROVAL` and `QUARANTINE` outcomes.

### `Why was this sent?`

Authenticated owner/customer view must display the complete safe causal chain without exposing secrets or unrelated recipient data.

### Approval inbox

- clear impact summary;
- requested exception;
- policy rule being overridden;
- estimated recipients and cost when available;
- expiration;
- approve/deny with reason;
- step-up authentication;
- immutable audit history.

## Required events

Publish applicable events from `KLYROW_DIFFERENTIATED_FEATURES_PROGRAM.md` plus policy-version and approval-expiration events. Event payloads must contain IDs and safe summaries, not secrets or full message content.

## Required metrics and alerts

- decisions by outcome/reason/tenant-safe dimension;
- evaluation latency;
- fail-closed errors;
- pending and expired approvals;
- stale decisions blocked at enqueue;
- passport-signing failures;
- decision/provider reconciliation drift.

Alert on unusual deny spikes, evaluator unavailability and sends reaching a provider path without a valid decision.

## Critical tests

- every rule and reason code;
- policy version immutability;
- rule-order determinism;
- fail-closed fact lookup;
- concurrent quota reservation;
- consent revoked between initial decision and enqueue;
- tenant suspended between decision and enqueue;
- cross-tenant IDOR;
- wrong approval permission;
- expired approval;
- approval replay;
- decision idempotency;
- direct-send bypass attempts;
- provider enqueue without decision;
- passport signature verification and tamper detection;
- no secrets or message bodies in passports/events/logs;
- browser and accessibility tests for policy, explorer and approval flows.

## Exclusions

- no production policy activation from this feature branch;
- no direct Postal, Keycloak or Odoo database writes;
- no policy bypass for platform administrators;
- no automatic approval by AI or n8n;
- no live send merely because a simulation succeeds.

## Definition of done

This mission is complete when all release-scoped send paths are covered by an authoritative decision contract, bypass attempts fail, decision explanations are usable, immutable evidence and passports verify, migrations and rollback are documented, tests pass and production flags remain disabled.

---

# Mission 27 — Simulation and Recipient Attention Engine

**Branch:** `feat/klyrow-simulation-attention-engine`

## Objective

Build a no-side-effect digital twin that replays campaigns, segments, journeys, policies, costs and expected integrations before publication, and build a runtime attention-budget arbiter that coordinates competing communications for the same recipient.

## Required data model

Add an appropriate form of:

### `simulation_runs`

- tenant ID
- requested by
- target kind and immutable version IDs
- historical or synthetic input mode
- time window and fixed simulation clock
- status
- engine version
- source snapshot hashes
- started/completed timestamps
- failure information

### `simulation_results`

Store aggregate and drill-down results for:

- eligible recipients;
- denied/deferred/quarantined recipients;
- expected volume by hour/day;
- sender/domain/provider route;
- expected usage and cost;
- queue-load estimates;
- journey node counts;
- loops/unreachable nodes;
- collision counts;
- expected n8n/Odoo event counts;
- differences from the current published version.

### `attention_policies` and immutable versions

Support:

- maximum per hour/day/week;
- category-specific limits;
- mandatory cooldowns;
- quiet hours;
- priority classes;
- digest eligibility;
- emergency/security exemptions with audit;
- tenant defaults and optional recipient preference reductions.

### `attention_claims`

- recipient/profile;
- intent and decision references;
- priority;
- category;
- time window;
- status;
- scheduled/deferred/canceled timestamps;
- collision group;
- reason codes.

### `digest_groups`

- recipient/profile;
- compatible intents;
- digest template/version;
- deadline;
- final decision and generated message reference.

## Simulation execution requirements

- Use the same segment, journey, policy, rendering and pricing contracts used in runtime, with providers and external side effects replaced by recording adapters.
- Freeze all referenced versions and the clock for deterministic replay.
- Support historical events, synthetic fixtures and sampled profiles.
- Never write usage charges, provider outbox items, middleware events, Odoo records or n8n executions.
- Mark all results as simulation data.
- Support cancellation, progress, bounded resource use and expiry/retention.
- Provide exact caveats when provider reputation, future behavior or external data cannot be predicted.

## Attention arbitration requirements

For every runtime intent, evaluate:

- communication priority;
- purpose and stream;
- current recipient claims;
- quiet hours;
- configured limits;
- recent delivered and scheduled communications;
- collision with security, billing, support, onboarding or marketing messages;
- digest compatibility;
- expiration/usefulness of the intent;
- tenant and recipient preference.

Return one of:

```text
SEND_NOW
DEFER_UNTIL
DROP_SUPERSEDED
COMBINE_IN_DIGEST
REQUIRE_APPROVAL
```

Critical security, password, fraud or service notifications may have special policy but still require audit and mandatory abuse protections.

## Required APIs

```text
POST   /v1/simulations
GET    /v1/simulations
GET    /v1/simulations/{id}
POST   /v1/simulations/{id}/cancel
GET    /v1/simulations/{id}/recipients
GET    /v1/simulations/{id}/collisions
GET    /v1/simulations/{id}/cost
POST   /v1/simulations/{id}/compare
GET    /v1/attention-policies
POST   /v1/attention-policies
POST   /v1/attention-policies/{id}/versions
POST   /v1/attention-policies/{id}/versions/{version}/publish
GET    /v1/profiles/{profile_id}/attention
POST   /v1/attention/evaluate
```

## Required UI

### Simulation setup

- choose campaign, journey, segment, template and policy versions;
- historical/synthetic time range;
- sample/full mode with estimated resource use;
- recipient exclusions;
- no-side-effect warning;
- start/cancel controls.

### Simulation report

- recipient funnel;
- allow/deny/defer reasons;
- hourly/daily volume;
- queue and provider-route estimates;
- expected cost and quota effect;
- collisions;
- journey graph heatmap;
- unreachable nodes and loops;
- expected middleware/n8n/Odoo events;
- comparison to currently published version;
- exportable evidence.

### Attention center

- policy versions;
- priority matrix;
- recipient timeline;
- collision groups;
- deferred queue;
- digest groups;
- override requests with permission and audit.

## Required integration

- The decision ledger invokes attention evaluation.
- Journeys and campaigns expose immutable definitions to simulation.
- Billing supplies test-mode pricing calculations only.
- Provider mesh supplies route/health assumptions without live calls.
- n8n and Odoo effects are recorded as expected events only during simulation.

## Critical tests

- deterministic replay;
- zero real outbox/inbox/provider/Odoo/n8n side effects;
- duplicate simulation requests;
- time zone and daylight-saving behavior;
- segment and journey version isolation;
- large-run cancellation and recovery;
- resource limits;
- collision priority;
- security message versus marketing collision;
- weekly/daily/hourly limits;
- quiet hours;
- digest compatibility;
- stale deferred intent;
- concurrent attention claims;
- simulation result authorization and tenant isolation;
- browser/accessibility tests.

## Exclusions

- no autonomous campaign publication;
- no claim that estimated delivery or revenue is guaranteed;
- no live provider failover testing from the simulation branch;
- no recipient-contact frequency override without audit and permission.

## Definition of done

The digital twin must produce deterministic, explainable, side-effect-free evidence, and the attention arbiter must prevent uncontrolled recipient collisions across release-scoped send paths.

---

# Mission 28 — Recipient Trust Center

**Branch:** `feat/klyrow-recipient-trust-center`

## Objective

Give recipients a secure, accessible and privacy-safe way to understand communications, manage preferences, review consent, reduce frequency, request data actions and report abuse without requiring a Klyrow customer account.

## Required data model

Add an appropriate form of:

### `recipient_access_tokens`

- tenant ID
- recipient/profile reference
- token hash or signed-token nonce
- purpose/scope
- issued/expires/consumed timestamps
- message or decision reference
- locale
- revocation state

Tokens must be scoped, expiring and protected from cross-tenant replay. Store hashes rather than reusable raw tokens where server lookup is used.

### `recipient_trust_sessions`

- short-lived session ID;
- recipient/profile and tenant scope;
- verified token purpose;
- created/expires timestamps;
- rate-limit and abuse metadata.

### `privacy_requests`

- export, correction or deletion type;
- recipient/profile and tenant;
- verification state;
- requested timestamp;
- review and execution state;
- legal/retention hold reason where applicable;
- completion evidence;
- Odoo support mapping reference.

### `recipient_abuse_reports`

- message/decision reference;
- safe reason category;
- optional redacted comment;
- status;
- tenant and platform review references;
- suppression action reference.

## Required public experience

### Why am I receiving this?

Display only safe information:

- verified sending organization;
- message purpose and category;
- date/time;
- subscription topic;
- high-level source of permission;
- current preference state;
- recent communication-frequency summary;
- available preference, unsubscribe, support and privacy actions.

Do not expose sensitive segment criteria, medical/financial/risk attributes, internal fraud classifications, employee notes, other recipients or security-sensitive system details.

### Preference center

Support:

- global marketing unsubscribe;
- topic-level preferences;
- frequency reduction;
- preferred language;
- quiet-hour preferences where offered;
- double opt-in confirmation;
- restore/resubscribe flow with appropriate proof;
- immediate clear confirmation and email receipt where configured.

### Communication history

Provide a privacy-safe summary, not a raw data dump. It may show recent date, sender organization, purpose/category and outcome when lawful and appropriate.

### Privacy and abuse

- data export request;
- deletion request;
- correction/support request;
- report spam/abuse;
- contact sender support;
- request status using a secure token or verified flow.

## Required APIs

Public routes must be deliberately separate from authenticated tenant APIs and strongly rate-limited.

```text
GET    /public/v1/trust/{token}
POST   /public/v1/trust/{token}/preferences
POST   /public/v1/trust/{token}/unsubscribe
POST   /public/v1/trust/{token}/resubscribe
POST   /public/v1/trust/{token}/privacy-requests
GET    /public/v1/trust/{token}/privacy-requests/{request_id}
POST   /public/v1/trust/{token}/abuse-reports
POST   /public/v1/trust/{token}/support
GET    /v1/recipient-trust/settings
PATCH  /v1/recipient-trust/settings
GET    /v1/privacy-requests
GET    /v1/privacy-requests/{id}
POST   /v1/privacy-requests/{id}/approve
POST   /v1/privacy-requests/{id}/complete
POST   /v1/privacy-requests/{id}/reject
GET    /v1/abuse-reports
```

## Required integration

- Explanations derive from the decision ledger's safe projection.
- Preference and unsubscribe writes use the authoritative consent/preferences service.
- Abuse reports may create immediate suppressions according to policy.
- Privacy/support events flow through middleware to Odoo and approved n8n workflows.
- Odoo remains a work-management surface and cannot directly change consent without a signed Klyrow command.
- Postal links must point to Klyrow trust endpoints, not expose Postal administration.

## Required UI

- branded but clearly identifies the sending organization;
- mobile-first;
- English and Spanish;
- high-contrast and keyboard accessible;
- reduced-motion support;
- no dark patterns;
- plain-language explanation of consequences;
- confirmation before global unsubscribe or deletion request;
- clear pending/completed/error states;
- privacy-safe support request form.

Tenant administrators need configuration for branding, topics, contact details, allowed preference options and lawful retention messaging. Platform owner needs abuse, privacy SLA and failed-workflow dashboards.

## Critical tests

- expired/revoked token;
- token replay and wrong purpose;
- cross-tenant token misuse;
- token enumeration resistance;
- rate limits;
- safe explanation redaction;
- preference update race;
- global unsubscribe precedence;
- double opt-in proof;
- deletion request with retention/legal hold;
- abuse report suppression;
- Odoo/n8n outage without losing request;
- localization;
- mobile, keyboard and accessibility tests;
- no authenticated tenant information leakage.

## Exclusions

- no display of sensitive segmentation or internal decision facts;
- no unauthenticated access to full profile data;
- no direct Odoo or n8n mutation;
- no automatic deletion that violates required retention or audit obligations.

## Definition of done

A recipient can securely understand and control communications, while Klyrow preserves tenant isolation, auditability, suppression enforcement and privacy-safe external integrations.

---

# Mission 29 — Cross-System Reconciliation and Governed Self-Healing

**Branch:** `feat/klyrow-reconciliation-self-healing`

## Objective

Continuously compare expected Klyrow state against Keycloak, Postal, Codestra middleware, n8n and Odoo, detect drift, produce explainable repair plans and safely execute only approved classes of repairs.

## Required architecture

Create adapter contracts that read supported external state through authenticated APIs or existing connector contracts. Never read external databases directly.

Suggested modules:

```text
apps/gateway/app/reconciliation/
├── api.py
├── models.py
├── rules.py
├── snapshots.py
├── findings.py
├── plans.py
├── approvals.py
├── executor.py
├── adapters/
└── events.py
```

## Required data model

### `reconciliation_runs`

- scope: platform, tenant, customer, billing period, provider or connector;
- requested/scheduled by;
- adapter versions;
- snapshot timestamps;
- status;
- counts by severity;
- started/completed timestamps;
- error and retry state.

### `reconciliation_snapshots`

- system name;
- resource kind and external ID;
- tenant mapping;
- normalized safe state;
- state hash;
- observed timestamp;
- expiration/staleness.

Do not store external secrets or unnecessary PII.

### `reconciliation_findings`

- stable finding type;
- severity;
- tenant/customer scope;
- expected state;
- observed state;
- first/last seen;
- occurrences;
- evidence references;
- repair classification;
- status;
- suppression/waiver metadata.

### `repair_plans`

- finding IDs;
- ordered steps;
- preconditions;
- expected effects;
- rollback/compensation;
- classification:
  - `SAFE_AUTOMATIC`
  - `OWNER_APPROVAL_REQUIRED`
  - `FINANCIAL_APPROVAL_REQUIRED`
  - `SECURITY_REVIEW_REQUIRED`
  - `MANUAL_ONLY`
- plan hash and expiry.

### `repair_executions`

- plan ID;
- idempotency key;
- requested/approved/executed by;
- step-up evidence;
- per-step state;
- external correlation IDs;
- compensation state;
- final outcome.

## Minimum reconciliation rules

### Keycloak ↔ Klyrow

- OIDC identity maps to a missing/disabled local identity;
- Klyrow identity references an unavailable Keycloak subject;
- owner identity configuration mismatch;
- membership exists for disabled identity;
- MFA/step-up policy evidence missing for platform owner.

Email differences must not reassign identity authority; identity remains `(issuer, subject)`.

### Klyrow ↔ Postal

- workspace mapping incomplete;
- provider resource missing;
- provider credential revoked but Klyrow marks active;
- Klyrow tenant suspended but provider route remains enabled;
- domain/provider state mismatch;
- provider message outcome unresolved;
- duplicate external resources.

### Klyrow ↔ middleware/n8n

- outbox event exhausted retries;
- expected workflow execution absent;
- workflow completed without result callback;
- duplicate or replayed result;
- workflow version mismatch;
- dead-letter accumulation.

### Klyrow ↔ Odoo

- missing/duplicate partner or contact;
- wrong tenant/external mapping;
- subscription state mismatch;
- usage statement missing;
- invoice mapping missing/duplicated;
- payment confirmed in Odoo but not reconciled in Klyrow;
- credit/adjustment mismatch;
- support ticket status drift;
- reseller hierarchy or price-list mismatch.

### Internal Klyrow

- decision/provider lifecycle mismatch;
- reserved usage never finalized or released;
- orphan attention claim;
- incomplete privacy request;
- stale approval;
- ledger aggregate mismatch.

## Repair rules

Safe automatic repair may include idempotent re-emission of a missing non-financial event or refresh of a stale read model.

The following always require explicit approval and step-up where applicable:

- financial records;
- payments, credits or wallet adjustments;
- entitlements or suspension;
- identity or ownership;
- credential creation/revocation;
- provider route changes;
- deletion;
- cross-tenant mapping changes;
- policy overrides;
- production activation.

Never silently delete duplicate Odoo, Postal or Keycloak resources. Produce a manual or compensating plan.

## Required APIs

```text
POST   /v1/reconciliation/runs
GET    /v1/reconciliation/runs
GET    /v1/reconciliation/runs/{id}
GET    /v1/reconciliation/findings
GET    /v1/reconciliation/findings/{id}
POST   /v1/reconciliation/findings/{id}/waive
POST   /v1/reconciliation/findings/{id}/repair-plan
GET    /v1/reconciliation/repair-plans/{id}
POST   /v1/reconciliation/repair-plans/{id}/approve
POST   /v1/reconciliation/repair-plans/{id}/execute
POST   /v1/reconciliation/repair-plans/{id}/cancel
GET    /v1/reconciliation/repair-executions/{id}
GET    /v1/customers/{tenant_id}/integrity
```

## Required UI

### System Integrity

- health by system and domain;
- findings by severity/type/age;
- stale snapshots;
- dead letters;
- financial and identity findings separated;
- repair-plan preview;
- approval queue;
- execution timeline;
- rollback/compensation state.

### Customer 360 integrity tab

Show safe linked state for Keycloak identity, workspace, Postal, middleware, n8n, Odoo, billing, decisions and provider events with external deep links where authorized.

## Required metrics and alerts

- runs and duration;
- adapter failures;
- findings by type/severity/age;
- unresolved financial/security findings;
- repair success/failure;
- repeat drift after repair;
- dead-letter and stale-snapshot counts.

## Critical tests

- adapter timeout and partial state;
- stale snapshot handling;
- duplicate external records;
- finding deduplication;
- plan hash/precondition changes;
- concurrent repair;
- approval expiration;
- wrong permission/tenant;
- idempotent repair command;
- compensation after partial failure;
- no destructive automatic repair;
- financial and identity step-up enforcement;
- cross-system outage;
- secrets/PII absent from snapshots/logs;
- browser/accessibility tests.

## Exclusions

- no direct database reads or writes to Keycloak, Postal or Odoo;
- no general-purpose arbitrary remote command execution;
- no automatic financial, identity, credential, suspension or deletion repair;
- no bypass of middleware for Odoo/n8n.

## Definition of done

The system detects material drift, produces durable evidence and safe repair plans, and can execute approved idempotent repairs without losing auditability or crossing authority boundaries.

---

# Mission 30 — Provider Mesh and Configuration Portability

**Branch:** `feat/klyrow-provider-mesh-portability`

## Objective

Preserve Postal 3.3.7 as the primary delivery engine while creating a provider-neutral contract, controlled routing, health-aware failover safety and portable configuration lifecycle.

## Required provider contracts

Define stable interfaces for:

- account capability discovery;
- sender/domain readiness;
- message submit;
- idempotency/correlation support;
- status lookup;
- event normalization;
- inbound route support;
- suppression handling where provider-specific;
- health and quota;
- credential rotation reference;
- provider-specific error classification.

Implement the Postal 3.3.7 adapter fully against existing supported boundaries. Additional providers may be adapter interfaces, test doubles or disabled preview integrations unless credentials and a separate reviewed activation scope exist.

Do not use provider failover to evade abuse, reputation, policy or suspension controls.

## Required data model

### `provider_accounts`

- tenant/platform owner scope;
- provider type;
- display name;
- secret reference, never raw credential;
- region/environment;
- status;
- verified capabilities;
- created/updated/audited metadata.

### `provider_routes` and immutable versions

Rules may use:

- tenant;
- stream;
- sender/domain;
- region/data-residency policy;
- dedicated/shared pool;
- plan/SLA;
- cost class;
- provider health;
- approved fallback sequence.

### `provider_health_snapshots`

- submit and status endpoint health;
- queue/latency where available;
- error rates;
- circuit state;
- observed timestamp;
- source/confidence.

### `provider_message_mappings`

- canonical Klyrow message ID;
- attempt ID;
- provider account/route;
- provider message ID;
- submit state;
- outcome certainty;
- timestamps;
- reconciliation state.

### `provider_failover_attempts`

- original attempt;
- reason;
- outcome certainty;
- approval or automatic policy;
- selected fallback;
- idempotency and duplicate-protection evidence.

### Configuration portability

Add immutable export/import jobs and signed packages for supported:

- policies;
- templates and versions;
- segments;
- journeys;
- consent topics;
- stream definitions;
- domains and sender metadata without private keys;
- webhook definitions without secrets;
- alert rules;
- role definitions;
- integration mappings without credentials.

## Routing and failover rules

- Every message has one canonical Klyrow ID independent of provider.
- Provider submit uses an idempotency/correlation strategy appropriate to the adapter.
- A timeout or connection loss after submit creates `OUTCOME_AMBIGUOUS`; do not immediately submit to another provider.
- Reconcile ambiguous outcome using status lookup, callbacks or bounded waiting.
- Failover is permitted only when the previous attempt is proven not accepted, or when a reviewed duplicate-risk policy explicitly permits it for a narrowly defined message type.
- The fallback provider must have the sender/domain configured and verified.
- Policy, consent, suppression, suspension and attention decisions remain authoritative across providers.
- Provider health routing must be deterministic and audited.

## Required APIs

```text
GET    /v1/provider-accounts
POST   /v1/provider-accounts
POST   /v1/provider-accounts/{id}/test
POST   /v1/provider-accounts/{id}/disable
GET    /v1/provider-routes
POST   /v1/provider-routes
POST   /v1/provider-routes/{id}/versions
POST   /v1/provider-routes/{id}/versions/{version}/validate
POST   /v1/provider-routes/{id}/versions/{version}/publish
GET    /v1/provider-health
GET    /v1/messages/{message_id}/provider-attempts
POST   /v1/provider-attempts/{id}/reconcile
POST   /v1/provider-attempts/{id}/request-failover
POST   /v1/configuration-exports
GET    /v1/configuration-exports/{id}
POST   /v1/configuration-imports
GET    /v1/configuration-imports/{id}
POST   /v1/configuration-imports/{id}/validate
POST   /v1/configuration-imports/{id}/plan
POST   /v1/configuration-imports/{id}/apply
```

## Required UI

- provider account list with health and secret-reference status;
- route/version builder;
- dry-run route test;
- health/circuit dashboard;
- message attempt timeline;
- ambiguous-outcome and failover approval queue;
- configuration export/import wizard;
- validate and plan diff before apply;
- signature and source verification;
- rollback package creation.

## Required developer tooling

Extend the developer-platform CLI or add a reviewed Klyrow CLI surface supporting:

```text
klyrow export
klyrow validate
klyrow plan
klyrow apply
klyrow rollback
```

Commands must use APIs, not direct database access. Secrets are referenced or re-entered separately and never included in export packages.

## Required events

Publish route, health, ambiguity, reconciliation, failover and configuration lifecycle events through the shared control plane.

## Critical tests

- Postal adapter compatibility;
- capability mismatch;
- provider secret non-retrieval;
- route determinism;
- domain not verified on fallback;
- timeout before submit versus timeout after submit;
- duplicate prevention under ambiguous outcome;
- callback/status race;
- circuit open/half-open/closed;
- cross-tenant provider-account access;
- disabled provider;
- export excludes secrets;
- signature verification;
- invalid/unsupported package version;
- plan shows all changes;
- apply idempotency and rollback;
- no policy or suppression bypass;
- browser/accessibility tests.

## Exclusions

- no unrestricted multi-provider live routing from this branch;
- no provider credentials committed to Git or export packages;
- no spam-evasion or reputation bypass;
- no blind failover after ambiguous submit;
- no removal of Postal as the primary provider.

## Definition of done

Postal works through a stable adapter, provider attempts are duplicate-safe and explainable, routing can be validated without activation, and supported Klyrow configuration can be exported, reviewed, imported and rolled back without secrets.

---

# Mission 31 — Reseller and White-Label Platform

**Branch:** `feat/klyrow-reseller-white-label`

## Objective

Build a secure multi-level commercial operating model in which platform owner, reseller and customer tenant responsibilities are explicit, pricing and margin are auditable, Odoo accounting records reconcile and branded customer experiences remain isolated.

## Required hierarchy

```text
Klyrow platform
  -> reseller account
      -> customer tenant
          -> customer users and workspaces
```

Do not permit arbitrary unlimited nesting unless a later reviewed requirement adds it.

A reseller is not a platform owner. Reseller administrators may access only their assigned customers and delegated permissions.

## Required data model

### `reseller_accounts`

- platform-scoped ID;
- legal/display name;
- Odoo partner mapping;
- status;
- commercial currency;
- settlement mode;
- default price book;
- risk/credit state;
- created/approved/suspended metadata.

### `reseller_tenants`

- reseller ID;
- customer tenant ID;
- relationship status;
- effective dates;
- customer-specific price book;
- delegated support settings;
- uniqueness and history.

A tenant cannot silently move between resellers. Transfer requires an explicit effective-dated workflow, financial reconciliation and audit.

### `price_books` and immutable versions

Support wholesale and retail rules for:

- base subscription;
- included messages/profiles/seats/API volume;
- marketing and transactional message rates;
- dedicated resources;
- overages;
- support tier;
- optional features;
- taxes/discount metadata;
- effective period and currency.

### `reseller_contracts`

- approved price-book version;
- credit terms;
- minimum commitments;
- settlement schedule;
- commission/margin rules;
- effective dates;
- Odoo contract/subscription mapping.

### `reseller_wallets` and `wallet_transactions`

Use append-only transactions for:

- deposits;
- reservations;
- usage finalization;
- releases;
- credits;
- refunds;
- manual adjustments;
- expiration where lawful;
- reconciliation corrections.

Never mutate balance without a ledger entry. High-risk adjustments require step-up authentication and dual-control policy where configured.

### `margin_ledger`

Record:

- tenant/customer;
- service period/message/campaign reference;
- provider cost basis;
- Klyrow platform cost allocation;
- reseller wholesale charge;
- customer retail charge;
- gross margin;
- currency and FX reference when applicable;
- price-book versions;
- reconciliation state.

### `brand_profiles`

- reseller or tenant scope;
- logo/media references;
- color and typography tokens;
- product display name;
- support contact;
- email footer/legal text;
- locale defaults;
- custom domain configuration;
- version and publication state.

### `delegated_admin_grants`

- reseller administrator identity;
- customer tenant;
- explicit permission set;
- reason;
- effective/expiry timestamps;
- revocation;
- audit.

## Required commercial behavior

- Klyrow usage ledger remains authoritative for real-time usage.
- Price-book versions determine customer and reseller charges.
- Odoo receives approved commercial records through middleware for accounting, invoices, payments, credits and settlements.
- Test mode must never create real charges or Odoo posted invoices.
- Plan/price changes are effective-dated and auditable.
- Currency changes require a new contract/version, not silent conversion.
- Suspended reseller behavior must be explicitly defined for child tenants; it must not silently terminate security or legally required messages.
- Customer entitlements cannot be granted solely because an Odoo or n8n record says so; Klyrow validates a signed command and commercial state.

## Required white-label behavior

- branded login/portal selection only after verified domain routing and TLS readiness;
- safe fallback to Klyrow branding when custom branding is unavailable;
- tenant/reseller assets isolated;
- no custom scripts or unsafe HTML;
- email footer and sender identity remain truthful and compliant;
- recipient trust center identifies the actual sending organization;
- white-labeling never hides required legal, abuse or Klyrow operator notices.

## Required APIs

```text
GET    /v1/resellers
POST   /v1/resellers
GET    /v1/resellers/{id}
PATCH  /v1/resellers/{id}
POST   /v1/resellers/{id}/approve
POST   /v1/resellers/{id}/suspend
GET    /v1/resellers/{id}/customers
POST   /v1/resellers/{id}/customers
POST   /v1/reseller-relationships/{id}/transfer
GET    /v1/price-books
POST   /v1/price-books
POST   /v1/price-books/{id}/versions
POST   /v1/price-books/{id}/versions/{version}/publish
GET    /v1/reseller-wallets/{id}
GET    /v1/reseller-wallets/{id}/transactions
POST   /v1/reseller-wallets/{id}/adjustments
GET    /v1/reseller-margin
GET    /v1/reseller-settlements
POST   /v1/reseller-settlements/{id}/close
GET    /v1/brand-profiles
POST   /v1/brand-profiles
POST   /v1/brand-profiles/{id}/versions
POST   /v1/brand-profiles/{id}/versions/{version}/publish
GET    /v1/delegated-admin-grants
POST   /v1/delegated-admin-grants
DELETE /v1/delegated-admin-grants/{id}
```

## Required UI

### Platform owner

- reseller portfolio;
- reseller onboarding and approval;
- credit/risk state;
- customers and usage;
- wholesale revenue, retail revenue where supplied, provider cost and margin;
- wallets, credits and settlements;
- Odoo reconciliation;
- delegated-admin audit;
- brand/custom-domain readiness;
- suspension and recovery workflows.

### Reseller admin

- customer list and Customer 360;
- plan and price assignment within delegated bounds;
- usage and margin;
- wallet/balance;
- invoices and settlements;
- support requests;
- branding;
- delegated team members;
- Odoo-linked commercial status as authorized.

### Customer tenant

- branded portal;
- plan, usage, invoices and support appropriate to the commercial arrangement;
- truthful sender and legal information;
- no visibility into reseller wholesale pricing unless explicitly allowed.

## Required Odoo mappings

Through middleware, support:

- reseller partner/company;
- child customer partner/company/contact;
- CRM opportunity/onboarding activities;
- reseller contract/subscription;
- customer subscription;
- price list and effective version metadata;
- usage statements;
- customer invoices/payments/credits;
- reseller settlement and commission metadata;
- support tickets;
- external IDs and deep links.

Odoo is the accounting/back-office surface; Klyrow remains authoritative for usage, entitlement, wallet reservation and communication permission.

## Required events

Publish reseller, relationship, price-book, wallet, margin, settlement, branding and delegated-admin events through the shared control plane.

## Critical tests

- platform/reseller/customer permission matrix;
- cross-reseller and cross-customer IDOR;
- owner identity cannot be replaced by reseller role;
- child-tenant transfer race;
- price-book version/effective date;
- concurrent wallet reservations;
- negative-balance policy;
- credit/adjustment dual control;
- margin calculation and currency consistency;
- usage deduplication;
- Odoo invoice/payment replay;
- reseller suspension and child-tenant behavior;
- delegated access expiration;
- brand asset isolation;
- custom-domain verification and safe fallback;
- no real charge in test mode;
- browser/accessibility tests.

## Exclusions

- no unlimited reseller nesting;
- no reseller access to platform-wide secrets or infrastructure;
- no direct Odoo writes;
- no real billing activation from this feature branch;
- no unverified custom domain activation;
- no hidden sender identity or compliance information.

## Definition of done

The platform can safely model resellers and customers, calculate auditable commercial outcomes, enforce wallet and delegated-admin controls, synchronize approved accounting records to Odoo and deliver isolated white-label experiences without weakening security or tenant boundaries.

---

# Completion report required for every differentiated branch

Codex must report:

1. repository and current directory;
2. execution host and host IPs;
3. branch;
4. starting SHA;
5. final SHA;
6. every commit created;
7. every changed file;
8. requirement audit: implemented, partial, missing and unsafe;
9. implemented, retained, migrated and deferred behavior;
10. data model and additive migrations;
11. downgrade/rollback plan;
12. API and OpenAPI changes;
13. UI and accessibility behavior;
14. domain events and middleware contracts;
15. Odoo/n8n/provider contract changes;
16. exact targeted test commands/results;
17. exact full-suite commands/results;
18. lint, type-check and production-build results;
19. PostgreSQL migration/integration results;
20. authorization and tenant/reseller-isolation evidence;
21. idempotency, concurrency, retry and recovery evidence;
22. browser and accessibility results;
23. security, dependency, container and secret-scan results;
24. metrics, alerts and runbooks;
25. known limitations, external blockers and risks;
26. confirmation that Postal source was not modified;
27. confirmation that Keycloak, Postal and Odoo databases were not accessed directly;
28. confirmation that no secrets were printed or committed;
29. confirmation that no deployment, merge, service restart, DNS/TLS change, credential rotation, real billing, production provisioning or live activation occurred.

After posting the report to the branch PR, stop. Do not automatically begin the next branch.
