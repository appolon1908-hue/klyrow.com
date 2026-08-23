# CODEX MISSION — Klyrow Corporate Email SaaS Completion 1–12

## Mission

Implement the complete corporate Email SaaS roadmap defined in:

- `docs/KLYROW_CORPORATE_EMAIL_SAAS_COMPLETION_BLUEPRINT.md`
- `config/klyrow-corporate-saas-contract.yaml`

Target terminal state:

`KLYROW_CORPORATE_EMAIL_SAAS_PRODUCTION_CERTIFIED`

This is an implementation mission, not a documentation-only mission.

## Repository

`appolon1908-hue/klyrow.com`

## Primary rule

Do not rebuild working Klyrow/Postal/Mautic functionality merely because the blueprint describes it. First discover current implementation, tests, migrations, runtime contracts, and production evidence. Reuse an existing capability when it satisfies the exact contract; extend it when incomplete; replace it only with a documented migration reason and rollback.

## Architecture authority

Preserve:

- Klyrow as commercial multi-tenant authority.
- Postal as email transport.
- Mautic only where it remains a useful internal campaign/content component.
- PostgreSQL as durable source of truth.
- Redis only for ephemeral coordination/rate/cache.
- broker for asynchronous transport.
- Keycloak/OIDC as canonical identity authority.
- Middleware as the governed boundary to Odoo/n8n/other corporate systems.
- no direct Odoo database writes.
- no raw Postal/Mautic admin APIs exposed as the customer SaaS surface.

## Production safety

Until explicitly certified, keep all broad external delivery gates fail-closed.

Do not enable bulk/campaign delivery merely to test implementation.

Use synthetic fixtures and isolated environments for load/failure tests. A bounded real-email canary is allowed only when the existing production canary governance, domain/sender/recipient restrictions, backup/restore/rollback, and owner approval gates pass.

Never:

- bypass GitHub review/branch protections;
- self-approve a required independent review;
- use unrestricted root/sudo as an implementation shortcut;
- expose PostgreSQL/Redis/RabbitMQ/Kong Admin/provider admin interfaces publicly;
- store raw payment-card data;
- weaken consent/suppression/abuse controls;
- implement spam-evasion/provider-bypass behavior;
- log secrets, passwords, private keys, API tokens, SMTP passwords, payment tokens, or raw credential files.

## Execution model

Implement phases in order 1 -> 12.

For each phase:

1. Re-read the current protected/default branch and all active PRs touching the same files.
2. Discover existing source, schemas, APIs, runtime configuration, and tests.
3. Produce a gap matrix: `REUSE`, `EXTEND`, `NEW`, `DEPRECATE`, `BLOCKED_EXTERNAL`.
4. Create a scoped implementation branch/PR for the phase or a tightly coupled subset.
5. Implement source and forward migrations.
6. Update OpenAPI/API docs and SDKs for public endpoints.
7. Add unit, integration, security, migration, replay/idempotency, and role/tenant-isolation tests.
8. Add monitoring, alerts, operational docs, backup/rollback notes.
9. Run all affected tests plus full regression before merge.
10. Run secret/dependency/container scans as applicable.
11. Obtain legitimate independent review where repository policy requires it.
12. Merge only through protected governance.
13. Deploy only the exact immutable reviewed release.
14. Read back runtime source/digest/migrations/health.
15. Run changed-path production-safe canaries.
16. Create evidence and SHA-256 manifest.
17. Fix internal failures -> retest -> continue.

Do not start the next phase while the current phase has unresolved critical/high defects or an incomplete migration/rollback contract.

# PHASE 1 — Production handshake and reconciliation

Implement/reconcile:

- Klyrow <-> Server A HTTPS/mTLS.
- service identity/audience/scope.
- Postal/provider event inbox.
- durable Klyrow -> Middleware delivery-event outbox.
- event signature/timestamp/replay protection.
- retry/backoff/DLQ/operator replay.
- complete message/provider/usage/middleware reconciliation.
- exact one-message production canary ledger.
- message trace endpoint.

Required API contract from blueprint:

- `POST /v1/internal/provider-events/postal`
- `POST /v1/internal/middleware/events`
- `GET /v1/internal/middleware/events/{event_id}`
- `POST /v1/admin/reconciliation/email`
- `GET /v1/admin/reconciliation/email/{run_id}`
- `GET /v1/admin/canary-gate`
- `POST /v1/admin/canary-gate/reserve`
- `POST /v1/admin/canary-gate/close`
- `GET /v1/messages/{message_id}/trace`

Reuse equivalent routes if already correct; do not duplicate them.

Definition of done:

`PHASE_1_PRODUCTION_HANDSHAKE=PASS`

with duplicate event effects = 0 and one bounded canary reconciling end-to-end.

# PHASE 2 — Horizontal gateway and worker scale

Implement:

- shared Redis rate limiting;
- separate gateway and worker processes;
- mail/provider/webhook/journey/campaign/analytics/integration workers;
- durable outbox publisher;
- publisher confirms;
- leases/crash recovery;
- per-tenant fairness/backpressure;
- worker heartbeats;
- queue/operator status APIs.

Production must use `KLYROW_EMBEDDED_WORKERS=false`.

Test three gateway replicas and worker failure.

Definition of done:

`PHASE_2_DISTRIBUTED_RUNTIME=PASS`

# PHASE 3 — Durable journey engine

Implement the complete node executor for:

TRIGGER, SEGMENT_ENTRY, EVENT_TRIGGER, WAIT_DURATION, WAIT_UNTIL, EMAIL_SEND, CONDITION, PERCENT_SPLIT, AB_SPLIT, GOAL, PROFILE_UPDATE, WEBHOOK, MIDDLEWARE_EVENT, SEGMENT_ADD, SEGMENT_REMOVE, SUPPRESS, EXIT.

Existing `Journey`, `JourneyVersion`, and `JourneyRun` data must be reused/migrated rather than duplicated.

Add durable node executions, wakeups, event waits, goal hits, leases, retries, history, version pinning, pause/resume/rollback, debugger APIs.

No in-memory-only timers.

Definition of done:

`PHASE_3_JOURNEY_ENGINE=PASS`

# PHASE 4 — High-volume campaign execution

Implement:

- campaign execution generations;
- frozen audience snapshot;
- recipient snapshot members;
- batches;
- per-recipient state;
- send-time consent/suppression recheck;
- frequency caps;
- per-tenant/domain/stream budgets;
- pause/resume/cancel;
- progress and reconciliation APIs;
- safe test send/preflight;
- zero duplicate logical recipient sends.

Do not iterate an entire large audience inside the HTTP request.

Definition of done:

`PHASE_4_CAMPAIGN_ENGINE=PASS`

# PHASE 5 — Scalable profiles/events/segments

Implement:

- batch profile/event APIs;
- asynchronous imports;
- deterministic identity merge limited to tenant;
- segment revisions;
- compiled/indexed plans;
- incremental materialization;
- full rebuild jobs;
- member history;
- profile/event retention/partitioning;
- segment preview/stats/members APIs.

Do not leave production segmentation dependent on Python scanning all profiles.

Definition of done:

`PHASE_5_SEGMENTATION_DATA_PLANE=PASS`

# PHASE 6 — HA/DR

Implement production architecture and code/config support for:

- 2+ gateways;
- 2+ critical workers;
- PostgreSQL HA/PITR;
- RabbitMQ quorum/approved broker HA;
- Redis HA;
- Postal redundancy supported by deployed architecture;
- off-host encrypted backup;
- isolated scheduled restore;
- maintenance/drain mode;
- topology/replication/DR status APIs;
- RPO/RTO evidence.

Run controlled failover drills without destructive data loss.

Definition of done:

`PHASE_6_HA_DR=PASS`

# PHASE 7 — Entitlements and payment billing

Extend the existing Klyrow billing model. Do not create a competing billing engine.

Implement:

- central entitlements service;
- plans/prices/trials/seats/domains/profiles/messages/API limits/retention/features;
- immutable usage metering;
- overage;
- invoice/credit/refund lifecycle;
- tokenized payment references;
- provider adapter interface;
- signed idempotent provider webhooks;
- checkout;
- dunning/grace/suspension/recovery;
- billing reconciliation;
- reseller entitlement/settlement foundations.

No raw card data.

Definition of done:

`PHASE_7_BILLING_ENTITLEMENTS=PASS`

# PHASE 8 — Enterprise SSO/SAML/SCIM

Keep Keycloak as identity authority.

Implement:

- tenant enterprise connection management;
- SAML and OIDC customer IdPs;
- domain-enforced SSO;
- JIT;
- SCIM 2.0 Users/Groups;
- group/role mappings;
- deprovisioning/session revocation;
- customer MFA/session policy;
- optional network/IP restrictions;
- audited break-glass policy.

Never allow a tenant-controlled SAML/SCIM mapping to create `platform_admin`.

Definition of done:

`PHASE_8_ENTERPRISE_IDENTITY=PASS`

# PHASE 9 — Analytics and deliverability command center

Implement event/fact pipeline and aggregates for accepted, queued, sent, delivered, deferred, bounces, complaints, unsubscribes, opens, clicks, conversions, suppressions, rejections, provider failures.

Build campaign/journey/segment/domain/IP-pool analytics, deliverability alerts, DNS/TLS/PTR/DKIM/DMARC checks, DMARC report ingestion foundation, feedback-loop adapters, blocklist monitoring, Postmaster/SNDS adapter hooks where authorized.

Do not run heavy unbounded analytics on transactional message tables.

No invented revenue.

Definition of done:

`PHASE_9_ANALYTICS_DELIVERABILITY=PASS`

# PHASE 10 — Corporate portal/content/journey UI

Build the UI routes/layouts defined in the blueprint.

Required product areas:

- overview;
- messages/streams/domains/senders/inbound/suppressions;
- template/content studio;
- media/brand settings;
- profiles/imports/segments/preferences;
- campaigns;
- journey visual builder and run debugger;
- analytics;
- deliverability;
- developer keys/service accounts/SMTP/webhooks/logs/OpenAPI;
- billing;
- organization/team/security/SSO/SCIM/retention/audit/integrations;
- support;
- platform admin shell.

Use OIDC Authorization Code + PKCE, route RBAC, safe HTML, CSP, accessibility, responsive UI, and Playwright role matrix.

Definition of done:

`PHASE_10_CORPORATE_PORTAL=PASS`

# PHASE 11 — Compliance/privacy/data governance

Implement:

- global/topic unsubscribe;
- optional double opt-in;
- consent version/source/proof;
- DSAR export;
- deletion/rectification workflow;
- account closure;
- legal holds;
- retention policy/jobs;
- append-only security/admin audit;
- expiring authorized export objects;
- encryption-key rotation evidence hooks;
- data-region policy abstraction.

Legal hold must override deletion where policy requires it.

Do not claim SOC 2/ISO/GDPR certification merely because controls exist.

Definition of done:

`PHASE_11_COMPLIANCE_GOVERNANCE=PASS`

# PHASE 12 — Full corporate certification

Build production-equivalent isolated certification and run:

- API throughput/latency;
- email submission;
- profile/event batch;
- segment materialization;
- campaign batching;
- journey wakeups;
- webhook dispatch;
- analytics queries;
- gateway loss;
- worker loss;
- Redis outage;
- broker outage;
- PostgreSQL failover;
- Postal outage;
- Middleware outage;
- webhook destination outage;
- tenant isolation matrix;
- DB RLS negative tests;
- IDOR/SSRF/CORS/CSRF/replay/upload/rate tests;
- SAST/secret/dependency/container scans;
- Open Relay denial;
- public port scan;
- deliverability alignment;
- backup/restore/rollback.

Record P50/P95/P99, RPS, errors, CPU/RAM, DB connections, broker depth, oldest job age, Redis use, worker utilization.

Do not use destructive DoS testing.

Final required gates:

```text
CRITICAL_SECURITY_OPEN=0
HIGH_SECURITY_OPEN=0
UNEXPECTED_PUBLIC_PORTS=0
CROSS_TENANT_ACCESS=0
DUPLICATE_LOGICAL_EFFECTS=0
DATA_LOSS=0
OPEN_RELAY=DENIED
DATABASE_PUBLIC=DENIED
REDIS_PUBLIC=DENIED
BROKER_PUBLIC=DENIED
BACKUP=PASS
RESTORE=PASS
ROLLBACK=PASS
HA_FAILOVER=PASS
API_LOAD=PASS
CAMPAIGN_ENGINE=PASS
JOURNEY_ENGINE=PASS
BILLING_RECONCILIATION=PASS
SSO_SCIM=PASS
COMPLIANCE_WORKFLOWS=PASS
DELIVERABILITY=PASS
```

Final:

`FINAL_STATUS=KLYROW_CORPORATE_EMAIL_SAAS_PRODUCTION_CERTIFIED`

## Required evidence per phase

Create an evidence directory under a consistent governed path, containing as applicable:

- `DISCOVERY.md`
- `GAP_MATRIX.csv`
- `MIGRATION_TESTS.md`
- `API_CONTRACT.md`
- `SECURITY_TESTS.md`
- `PERFORMANCE.md`
- `FAILURE_RECOVERY.md`
- `BACKUP_RESTORE.md`
- `RUNTIME_READBACK.md`
- `ROLLBACK.md`
- `FINAL_REPORT.md`
- `SHA256SUMS`

No evidence file may contain live secrets.

## Failure policy

If internally fixable:

`discover -> backup -> fix source -> migration/test -> CI -> review -> immutable release -> deploy -> retest -> continue`

Do not stop merely because a test failed if the failure is an implementation defect you can repair safely.

Stop only at:

- a real external DNS/provider/legal/payment/account dependency;
- a required independent governance approval you cannot provide;
- a destructive operation requiring explicit owner confirmation;
- or successful terminal certification.
