# Klyrow Corporate Email SaaS Completion Blueprint — Phases 1–12

Status: implementation specification for Codex

Scope: evolve the existing Klyrow/Postal/Mautic platform into a production-grade corporate multi-tenant Email SaaS/ESP without replacing working components unnecessarily.

## 0. Non-negotiable architecture and safety rules

Preserve the existing product direction:

- Klyrow owns the commercial tenant/API/control plane.
- Postal is transport, not the public product API.
- Mautic may provide campaign/content capabilities but is not the tenant authority.
- Canonical employee/customer identity is Keycloak/OIDC; add enterprise SAML/SCIM through governed adapters.
- Internet/API traffic follows Caddy/Nginx -> Kong -> identity -> Klyrow/Middleware as defined by the deployed environment.
- Klyrow never writes directly to Odoo PostgreSQL. Odoo/n8n integration goes through Middleware/outbox APIs.
- PostgreSQL owns durable Klyrow state. Redis is cache/rate/coordination only, never the sole authority for billing, consent, campaign, journey, mailbox, or delivery state.
- RabbitMQ/NATS/approved broker is transport; use transactional outbox/inbox around durable business writes.
- All tenant-owned records carry `tenant_id` and are enforced by application authorization plus database-level isolation for sensitive tables.
- All new write APIs support idempotency where replay can create a second business effect.
- External email stays gated until the specific production release, domain, sender, recipient, reputation, and operator gates pass.
- Do not weaken suppressions, consent, abuse, spam, security, or branch-review controls to obtain a passing test.

### Target request path

```text
Client/SDK/Portal
  -> TLS edge
  -> Kong/API policy
  -> Keycloak/enterprise identity
  -> Klyrow API
  -> PostgreSQL transaction
  -> transactional outbox
  -> worker/broker
  -> Postal/provider
  -> provider event
  -> Klyrow inbox/idempotency
  -> analytics/reconciliation/webhooks/Middleware
```

### API-wide standards

All public APIs use `/v1` unless an existing equivalent must be preserved for compatibility.

Required headers/behavior:

- `Authorization: Bearer <token>` or scoped Klyrow API credential.
- `Idempotency-Key` on message, campaign execution, billing, import, export, and mutation requests that could duplicate an effect.
- `X-Request-Id` returned on every response.
- `X-Correlation-Id` propagated through Klyrow -> broker -> Postal -> webhook -> Middleware.
- Standard cursor pagination: `?limit=...&cursor=...`.
- Standard error body: `{code, message, request_id, correlation_id?, details?}` with no secrets.
- Rate-limit response headers: limit, remaining, reset/retry-after.
- Webhook signature: versioned HMAC over timestamp + event_id + canonical body; replay window and persisted event-id rejection mandatory.
- OpenAPI is authoritative and SDK generation must stay in sync.

### Database-wide standards

For new tenant-scoped business tables use:

- UUID/ULID string or native UUID primary key.
- `tenant_id` indexed and non-null unless intentionally platform-global.
- `created_at`, `updated_at` UTC timestamps.
- explicit unique constraints for idempotency and ownership.
- optimistic `version` where concurrent updates matter.
- immutable append-only audit/event rows for security/consent/billing evidence.
- no secrets in plaintext columns. Store secret references or verifier hashes.
- PostgreSQL RLS for high-risk tenant tables before enterprise certification.

---

# PHASE 1 — Production Klyrow <-> Middleware/Server A handshake and terminal E2E

## Objective

Finish the real production event/reconciliation path so accepted mail, provider status, usage, and delivery outcomes can be proven end-to-end without direct database coupling.

## Required features

1. Canonical Klyrow service identity and mTLS client certificate.
2. Server A HTTPS/mTLS receiver with exact Klyrow audience/scope.
3. Provider event inbox with signature + timestamp + event-id replay prevention.
4. Durable delivery-event outbox from Klyrow to Middleware.
5. Retry/backoff/dead-letter and operator replay.
6. Reconciliation between Klyrow `Message`, outbox, Postal provider id, provider event, usage ledger, and Middleware acknowledgement.
7. One-message production canary reservation/claim/complete ledger.
8. Hard recipient/domain/sender/max-delivery restrictions for canary mode.
9. Correlation trace from API submit to final reconciliation.

## Endpoints

Reuse an equivalent existing endpoint if it already provides the exact contract; otherwise add:

- `POST /v1/internal/provider-events/postal`
- `POST /v1/internal/middleware/events`
- `GET /v1/internal/middleware/events/{event_id}`
- `POST /v1/admin/reconciliation/email`
- `GET /v1/admin/reconciliation/email/{run_id}`
- `GET /v1/admin/canary-gate`
- `POST /v1/admin/canary-gate/reserve`
- `POST /v1/admin/canary-gate/close`
- `GET /v1/messages/{message_id}/trace`

Internal endpoints require service identity + mTLS + scope and must not be usable by a tenant browser token.

## Database layout

Extend existing tables where possible; create only missing structures:

### `provider_event_inbox`

- id
- tenant_id
- provider
- provider_event_id
- event_type
- provider_message_id
- message_id
- payload_json
- signature_version
- received_at
- processed_at
- state (`RECEIVED|PROCESSING|PROCESSED|RETRY|DEAD_LETTER`)
- attempts
- next_attempt_at
- error_code_safe
- unique(provider, provider_event_id)

### `middleware_delivery_outbox`

- id
- tenant_id
- event_id
- event_type
- aggregate_type
- aggregate_id
- payload_json
- idempotency_key
- state
- attempts
- next_attempt_at
- acknowledged_at
- error_code_safe
- unique(tenant_id, idempotency_key)

### `email_reconciliation_runs`

- id
- tenant_id nullable for platform run
- started_at
- completed_at
- state
- message_count
- drift_count
- evidence_json

### `email_reconciliation_items`

- run_id
- tenant_id
- message_id
- provider_message_id
- api_state
- outbox_state
- provider_state
- usage_state
- middleware_state
- drift_code

Use the existing durable production canary table if present; do not create a second competing gate.

## Acceptance

- exact one-message canary can be reserved once, claimed once, completed once.
- duplicate provider event has zero duplicate business effects.
- Middleware outage -> retry/DLQ -> replay -> exactly one reconciliation result.
- no direct Odoo DB write.
- complete trace returns only authorized tenant/platform data.

---

# PHASE 2 — Shared rate limiting, distributed workers, and horizontal API scale

## Objective

Remove single-process coordination assumptions and make Klyrow safe for multiple gateway/worker replicas.

## Required topology

```text
Load balancer
  -> Klyrow gateway replicas (stateless)
       -> PostgreSQL
       -> Redis (rate/cache/short leases only)
       -> broker
            -> mail workers
            -> provider-event workers
            -> webhook workers
            -> journey workers
            -> campaign workers
            -> analytics workers
            -> integration workers
```

## Required features

- Redis-backed distributed rate limiting keyed by tenant + credential + route.
- Redis-backed short-lived lock/coordination only where PostgreSQL row locking is inappropriate.
- standalone worker processes; production gateway must not depend on embedded background workers.
- transactional outbox publishing.
- broker publisher confirms.
- consumer idempotency.
- leases and crash recovery.
- bounded retries with dead-letter queues.
- queue backpressure and per-tenant fairness.
- graceful shutdown and lease handoff.
- worker heartbeat/readiness.
- horizontal-safe session/cache policy.

## Endpoints

- `GET /v1/admin/system/workers`
- `GET /v1/admin/system/queues`
- `GET /v1/admin/system/rate-limits`
- `POST /v1/admin/system/queues/{queue}/pause`
- `POST /v1/admin/system/queues/{queue}/resume`
- `POST /v1/admin/system/jobs/{job_id}/retry`
- `POST /v1/admin/system/jobs/{job_id}/dead-letter`

All are platform-admin only.

## Database layout

### `outbox_events`

Canonical durable publisher table if an equivalent does not already exist:

- id
- tenant_id
- topic
- aggregate_type
- aggregate_id
- event_type
- payload_json
- idempotency_key
- created_at
- published_at
- attempts
- next_attempt_at
- unique(tenant_id, idempotency_key)

### `worker_jobs`

Only for business jobs requiring durable DB state; broker delivery is not the sole source of truth.

- id
- tenant_id
- job_type
- aggregate_id
- state
- priority
- attempts
- available_at
- lease_owner
- lease_expires_at
- completed_at
- error_code_safe
- unique(job_type, aggregate_id, optional generation/version)

### `worker_heartbeats`

- worker_id
- worker_type
- instance_id
- started_at
- heartbeat_at
- version
- release_sha
- current_job_id nullable

## Configuration

- `KLYROW_EMBEDDED_WORKERS=false` in production.
- Redis TLS/auth/ACL required.
- broker credentials per worker class, not one global superuser.
- gateway is horizontally scalable and stateless except durable DB/session authority.

## Acceptance

- run 3 gateway replicas without changing business outcome.
- kill one worker during a leased job; another recovers it once.
- rate limits remain correct across replicas.
- Redis loss causes bounded degradation/fail-closed policy, not data loss.
- broker loss causes outbox backlog and later recovery, not lost transactions.

---

# PHASE 3 — Real distributed journey execution engine

## Objective

Turn the existing journey definitions/runs into a durable automation engine capable of millions of waiting profiles without keeping timers in memory.

## Supported nodes

- `TRIGGER`
- `SEGMENT_ENTRY`
- `EVENT_TRIGGER`
- `WAIT_DURATION`
- `WAIT_UNTIL`
- `EMAIL_SEND`
- `CONDITION`
- `PERCENT_SPLIT`
- `AB_SPLIT`
- `GOAL`
- `PROFILE_UPDATE`
- `WEBHOOK`
- `MIDDLEWARE_EVENT`
- `SEGMENT_ADD`
- `SEGMENT_REMOVE`
- `SUPPRESS`
- `EXIT`

## Endpoints

- `POST /v1/journeys`
- `GET /v1/journeys`
- `GET /v1/journeys/{journey_id}`
- `PUT /v1/journeys/{journey_id}`
- `POST /v1/journeys/{journey_id}/validate`
- `POST /v1/journeys/{journey_id}/publish`
- `POST /v1/journeys/{journey_id}/pause`
- `POST /v1/journeys/{journey_id}/resume`
- `POST /v1/journeys/{journey_id}/rollback/{version}`
- `POST /v1/journeys/{journey_id}/runs`
- `GET /v1/journeys/{journey_id}/runs`
- `GET /v1/journey-runs/{run_id}`
- `GET /v1/journey-runs/{run_id}/history`
- `POST /v1/journey-runs/{run_id}/cancel`
- `POST /v1/admin/journey-runs/{run_id}/retry-node`

## Database layout

Reuse `journeys`, `journey_versions`, `journey_runs`; add durable execution tables:

### `journey_node_executions`

- id
- tenant_id
- journey_id
- journey_version
- run_id
- profile_id
- node_id
- node_type
- state (`PENDING|READY|RUNNING|WAITING|COMPLETED|SKIPPED|RETRY|FAILED|CANCELLED`)
- attempt
- input_json
- output_json
- idempotency_key
- scheduled_at
- lease_owner
- lease_expires_at
- started_at
- completed_at
- error_code_safe
- unique(run_id, node_id, execution_generation)

### `journey_wakeups`

- id
- tenant_id
- run_id
- node_execution_id
- wake_at
- state
- claimed_at
- unique(node_execution_id)

### `journey_event_waits`

- id
- tenant_id
- run_id
- node_execution_id
- event_name
- filter_json
- expires_at nullable
- state

### `journey_goal_hits`

- id
- tenant_id
- run_id
- goal_node_id
- event_id
- hit_at
- unique(run_id, goal_node_id, event_id)

## Engine requirements

- published versions immutable.
- run is pinned to a journey version.
- paused journey prevents new entries and configurable progression; never corrupt existing waits.
- deterministic percentage/A-B assignment.
- wait jobs survive deploy/restart.
- all send nodes use normal consent/suppression/sender/quota policy.
- no AI-generated journey can publish without user confirmation.

## Acceptance

- simulated 100k waiting runs with bounded DB/broker load.
- crash during node execution -> retry exactly once logically.
- event trigger resumes only matching tenant/profile runs.
- rollback creates/publishes a new version; does not rewrite history.

---

# PHASE 4 — High-volume campaign execution engine

## Objective

Make campaign scheduling/execution scalable, resumable, suppression-safe, and auditable.

## Endpoints

- `POST /v1/campaigns`
- `GET /v1/campaigns`
- `GET /v1/campaigns/{campaign_id}`
- `PUT /v1/campaigns/{campaign_id}`
- `POST /v1/campaigns/{campaign_id}/test`
- `POST /v1/campaigns/{campaign_id}/preflight`
- `POST /v1/campaigns/{campaign_id}/schedule`
- `POST /v1/campaigns/{campaign_id}/pause`
- `POST /v1/campaigns/{campaign_id}/resume`
- `POST /v1/campaigns/{campaign_id}/cancel`
- `GET /v1/campaigns/{campaign_id}/audience`
- `GET /v1/campaigns/{campaign_id}/progress`
- `GET /v1/campaigns/{campaign_id}/events`
- `POST /v1/admin/campaigns/{campaign_id}/reconcile`

Keep existing `campaign-definitions` routes as compatibility aliases until clients migrate.

## Database layout

### `campaigns`

Canonical campaign metadata; reuse existing definition table if possible.

- id
- tenant_id
- name
- stream_id
- sender_identity_id
- template_id
- template_version
- segment_id
- segment_revision
- status
- timezone
- scheduled_at
- frequency_cap
- tracking_json
- created_by
- approved_by nullable
- version

### `campaign_executions`

- id
- tenant_id
- campaign_id
- campaign_version
- state
- audience_snapshot_id
- started_at
- completed_at
- paused_at
- cancelled_at
- total_recipients
- eligible_recipients
- suppressed_count
- invalid_count
- sent_count
- failed_count
- unique(campaign_id, campaign_version, execution_generation)

### `audience_snapshots`

- id
- tenant_id
- source_type (`SEGMENT|IMPORT|MANUAL`)
- source_id
- source_revision
- created_at
- profile_count
- checksum

### `audience_snapshot_members`

Partitionable:

- snapshot_id
- tenant_id
- profile_id
- email
- eligibility_state
- exclusion_reason nullable
- personalization_json
- unique(snapshot_id, profile_id)

### `campaign_batches`

- id
- tenant_id
- execution_id
- batch_number
- state
- first_member_cursor
- last_member_cursor
- recipient_count
- attempts
- available_at
- lease_owner
- lease_expires_at

### `campaign_recipient_state`

- execution_id
- tenant_id
- profile_id
- message_id nullable
- state
- suppression_checked_at
- send_attempted_at
- provider_state
- unique(execution_id, profile_id)

## Requirements

- freeze audience revision at execution time.
- suppression/consent checked again at send time even after snapshot.
- per-tenant/per-domain/per-stream budget.
- adaptive deferral/backoff, no spam-evasion behavior.
- frequency caps.
- pause/resume without duplicate recipients.
- cancellation prevents new sends but preserves audit.
- test send uses explicit test recipients only.
- no HTTP request loops over the full audience.

## Acceptance

- 1M-recipient synthetic campaign can be planned in batches without unbounded memory.
- pause/resume/cancel are idempotent.
- profile suppressed after snapshot is still blocked before send.
- worker retry cannot double-send a logical campaign recipient.

---

# PHASE 5 — Scalable segmentation and profile/event data plane

## Objective

Replace full Python profile scanning with indexed/materialized segmentation suitable for millions of profiles/events.

## Endpoints

- `POST /v1/profiles`
- `POST /v1/profiles/batch`
- `GET /v1/profiles/{profile_id}`
- `GET /v1/profiles/{profile_id}/timeline`
- `POST /v1/events`
- `POST /v1/events/batch`
- `POST /v1/segments`
- `GET /v1/segments`
- `GET /v1/segments/{segment_id}`
- `PUT /v1/segments/{segment_id}`
- `POST /v1/segments/{segment_id}/preview`
- `POST /v1/segments/{segment_id}/rebuild`
- `GET /v1/segments/{segment_id}/members`
- `GET /v1/segments/{segment_id}/stats`
- `POST /v1/imports/profiles`
- `GET /v1/imports/{job_id}`

## Database layout

Reuse existing profiles/events/segments; add:

### `segment_revisions`

- id
- tenant_id
- segment_id
- revision
- rules_json
- compiled_plan_json
- created_by
- created_at
- unique(segment_id, revision)

### `segment_materializations`

- id
- tenant_id
- segment_id
- revision
- state
- started_at
- completed_at
- member_count
- checksum
- high_watermark_event_id
- unique(segment_id, revision)

### `segment_members`

Partitionable/indexed:

- tenant_id
- segment_id
- segment_revision
- profile_id
- entered_at
- exited_at nullable
- active
- unique(segment_id, segment_revision, profile_id)

### `segment_rebuild_jobs`

- id
- tenant_id
- segment_id
- revision
- state
- cursor
- attempts
- started_at
- completed_at

### `profile_identity_keys`

- id
- tenant_id
- profile_id
- identity_type
- normalized_value_hash/indexed normalized form where lawful
- verified
- unique(tenant_id, identity_type, normalized value)

## Engine requirements

- compile supported rules to SQL/index plans when possible.
- incremental updates from event/profile changes.
- full rebuild fallback as background job.
- segment membership history/audit.
- suppression-aware preview and execution.
- batch imports asynchronous with row-level result file.
- deterministic merge rules; no cross-tenant identity merging.
- event table partitioning/retention strategy.

## Optional analytics store

Add a provider abstraction for event analytics. PostgreSQL remains authoritative; ClickHouse or equivalent may be used for large-volume analytical facts/aggregates. No business mutation is authoritative in the analytics store.

## Acceptance

- segment preview uses bounded query.
- materialization survives worker restart.
- profile change updates only affected segments where possible.
- 5M synthetic profiles / 100M synthetic events performance target documented and load-tested in non-production.

---

# PHASE 6 — High availability, multi-node resilience, and disaster recovery

## Objective

Remove single-host dependency for production corporate SaaS.

## Target topology

- 2+ Klyrow gateway nodes behind load balancer.
- 2+ workers per critical worker class.
- PostgreSQL HA with streaming replication/managed failover and PITR.
- RabbitMQ quorum cluster or equivalent durable broker cluster.
- Redis HA/sentinel/managed equivalent; loss must not lose business state.
- Postal redundancy according to supported deployment model.
- object storage for exports, large inbound attachments, evidence, and optional template media.
- off-host encrypted backups.
- observability independent of one application node.

## Endpoints

- `GET /v1/admin/system/topology`
- `GET /v1/admin/system/health`
- `GET /v1/admin/system/readiness`
- `GET /v1/admin/system/databases`
- `GET /v1/admin/system/brokers`
- `GET /v1/admin/system/replication`
- `POST /v1/admin/dr/runbook-check`

## Database layout

### `system_instances`

- instance_id
- service
- role
- region
- zone
- version
- release_sha
- started_at
- heartbeat_at
- draining

### `dr_exercises`

- id
- exercise_type
- started_at
- completed_at
- rpo_seconds
- rto_seconds
- result
- evidence_reference

### `backup_catalog`

Metadata only; no secrets.

- id
- component
- backup_time
- checksum
- encrypted
- offsite
- retention_class
- restore_tested_at
- object_reference

## Requirements

- define RPO/RTO targets.
- WAL/PITR where supported.
- scheduled isolated restore tests.
- tested node loss, DB failover, broker node loss, gateway loss, worker loss.
- no DNS/manual secret improvisation required during ordinary failover.
- maintenance/drain mode.

## Acceptance

- loss of one gateway causes no user-visible outage beyond load-balancer retry.
- loss of one worker causes recovery with zero duplicate business effects.
- broker node loss preserves confirmed messages.
- DB failover meets documented RTO/RPO.
- full isolated restore proves tenant data + message metadata + billing + configuration.

---

# PHASE 7 — Billing entitlements, metering, and real payment-provider adapters

## Objective

Connect the existing strong billing domain model to real SaaS entitlements and payment lifecycle without storing raw card data.

## Required features

- products/plans/versioned prices.
- trials.
- seats, domains, profiles, message allowance, API rate limits, retention, feature flags.
- usage metering from immutable message events.
- overage calculation.
- invoices/credits/refunds.
- tokenized payment method references.
- provider adapter interface (Stripe/Adyen/etc. can be implemented without changing core schema).
- checkout session.
- signed provider webhooks.
- dunning/grace/suspension/recovery.
- billing reconciliation.
- reseller wholesale/retail settlement foundation.
- tax adapter interface; no fabricated tax determination.

## Endpoints

- `GET /v1/billing/plans`
- `GET /v1/billing/subscription`
- `POST /v1/billing/subscription`
- `POST /v1/billing/subscription/change`
- `POST /v1/billing/subscription/cancel`
- `GET /v1/billing/usage`
- `GET /v1/billing/invoices`
- `GET /v1/billing/invoices/{invoice_id}`
- `POST /v1/billing/checkout`
- `GET /v1/billing/payment-methods`
- `POST /v1/billing/payment-methods`
- `DELETE /v1/billing/payment-methods/{id}`
- `POST /v1/internal/billing/providers/{provider}/webhook`
- `POST /v1/admin/billing/reconcile`
- `GET /v1/admin/billing/reconciliation/{run_id}`
- `GET /v1/entitlements`

## Database layout

Reuse existing `klyrow_*` billing tables. Add only missing:

### `tenant_entitlements`

- tenant_id
- entitlement_key
- value_type
- int_value nullable
- bool_value nullable
- string_value nullable
- source (`PLAN|OVERRIDE|PROMOTION|RESELLER`)
- effective_at
- expires_at nullable
- version
- unique(tenant_id, entitlement_key)

Examples:

- `messages.monthly`
- `profiles.max`
- `seats.max`
- `domains.max`
- `api.per_minute`
- `retention.days`
- `feature.journeys`
- `feature.saml`
- `feature.dedicated_ip`

### `billing_provider_events`

- id
- provider
- provider_event_id
- signature_version
- event_type
- payload_reference/safe payload
- received_at
- processed_at
- state
- unique(provider, provider_event_id)

### `billing_reconciliation_runs/items`

Compare invoice/payment/refund/subscription/provider state.

## Enforcement

Create one central entitlement service used by API, SMTP, domain creation, seat invitations, campaign execution, profile import, and retention jobs. Do not scatter plan checks inconsistently.

## Acceptance

- message usage event creates at most one billable unit per configured billing event.
- over-plan send is blocked or moves to documented overage behavior.
- payment-provider webhook replay is idempotent.
- past-due -> grace -> suspension -> recovery is tested.
- raw card data never enters Klyrow logs/DB.

---

# PHASE 8 — Enterprise SSO, SAML, SCIM, and customer identity administration

## Objective

Upgrade OIDC-only business identity into enterprise identity lifecycle while retaining canonical Keycloak authority.

## Features

- enterprise connection per tenant/domain.
- SAML 2.0 service-provider integration via Keycloak/adapter.
- OIDC enterprise connection support.
- domain-enforced SSO.
- JIT provisioning.
- SCIM 2.0 Users and Groups.
- role/group mapping.
- automatic deprovision/revoke sessions/API access.
- customer MFA/session policies.
- optional IP allowlists/network policies.
- break-glass policy with platform audit.
- audit of sign-in/provisioning/admin changes.

## Endpoints

Tenant admin:

- `GET /v1/enterprise/connections`
- `POST /v1/enterprise/connections`
- `GET /v1/enterprise/connections/{id}`
- `PUT /v1/enterprise/connections/{id}`
- `POST /v1/enterprise/connections/{id}/verify`
- `POST /v1/enterprise/connections/{id}/enable`
- `POST /v1/enterprise/connections/{id}/disable`
- `GET /v1/enterprise/group-mappings`
- `PUT /v1/enterprise/group-mappings`
- `GET /v1/security/policies`
- `PUT /v1/security/policies`

SCIM surface:

- `GET/POST /scim/v2/Users`
- `GET/PUT/PATCH/DELETE /scim/v2/Users/{id}`
- `GET/POST /scim/v2/Groups`
- `GET/PUT/PATCH/DELETE /scim/v2/Groups/{id}`
- `GET /scim/v2/ServiceProviderConfig`
- `GET /scim/v2/Schemas`
- `GET /scim/v2/ResourceTypes`

SCIM requires tenant-bound token/credential and rate limiting.

## Database layout

### `enterprise_connections`

- id
- tenant_id
- type (`SAML|OIDC`)
- name
- domain
- keycloak_connection_ref
- metadata_url/reference
- status
- enforce_for_domain
- jit_enabled
- scim_enabled
- created_at
- verified_at

### `enterprise_group_mappings`

- id
- tenant_id
- connection_id
- external_group_id/name
- klyrow_role
- active

### `scim_tokens`

- id
- tenant_id
- connection_id
- token_prefix
- verifier_hash
- scopes_json
- expires_at
- revoked_at
- last_used_at

### `directory_objects`

- id
- tenant_id
- connection_id
- object_type
- external_id
- klyrow_user_id nullable
- payload_version
- active
- last_synced_at
- unique(connection_id, object_type, external_id)

### `provisioning_events`

Append-only SCIM/JIT lifecycle evidence.

## Acceptance

- cross-tenant SAML/SCIM token cannot enumerate another tenant.
- disabling user revokes active sessions.
- group mapping cannot grant `platform_admin`.
- domain-enforced SSO works with documented break-glass process.

---

# PHASE 9 — Enterprise analytics and deliverability command center

## Objective

Build high-volume operational/marketing analytics and deliverability views without overloading transactional tables.

## Event model

Canonical event types include:

- accepted
- queued
- sent
- delivered
- deferred
- soft_bounce
- hard_bounce
- complaint
- unsubscribe
- open
- unique_open
- click
- unique_click
- conversion
- suppression
- rejected
- provider_failed

Each event must include tenant, message, stream, campaign/journey when applicable, profile when lawful, timestamp, provider, domain, IP pool, correlation id.

## Endpoints

- `GET /v1/analytics/overview`
- `GET /v1/analytics/timeseries`
- `GET /v1/analytics/campaigns`
- `GET /v1/analytics/campaigns/{id}`
- `GET /v1/analytics/journeys/{id}`
- `GET /v1/analytics/segments/{id}`
- `GET /v1/analytics/domains/{id}`
- `GET /v1/analytics/links`
- `GET /v1/analytics/cohorts`
- `GET /v1/deliverability/overview`
- `GET /v1/deliverability/domains`
- `GET /v1/deliverability/domains/{id}`
- `GET /v1/deliverability/ip-pools`
- `GET /v1/deliverability/alerts`
- `POST /v1/deliverability/domains/{id}/check`
- `POST /v1/admin/deliverability/reputation/recalculate`

## Database/warehouse layout

Transactional DB keeps authoritative messages and provider events. Build append-only analytics facts and aggregate tables (PostgreSQL partitioned mode for smaller deployment; ClickHouse adapter recommended for large-scale production).

### `analytics_message_events`

- event_id
- tenant_id
- message_id
- profile_id nullable
- campaign_id nullable
- journey_id nullable
- stream_id nullable
- event_type
- domain
- ip_pool_id nullable
- provider
- occurred_at
- dimensions_json
- unique(event_id)

### Aggregate tables/materialized views

- `analytics_hourly_tenant`
- `analytics_hourly_domain`
- `analytics_hourly_campaign`
- `analytics_hourly_journey`
- `analytics_daily_segment`
- `analytics_link_stats`

### `deliverability_alerts`

- id
- tenant_id
- domain_id nullable
- ip_pool_id nullable
- alert_type
- severity
- state
- observed_value
- threshold
- opened_at
- acknowledged_at
- resolved_at

## Deliverability integrations

Prepare provider adapters for:

- Google Postmaster signals where authorized.
- Microsoft SNDS/JMRP where applicable.
- feedback loops.
- DMARC aggregate report ingestion.
- blocklist monitoring.
- TLS certificate expiry.
- DNS/SPF/DKIM/DMARC/PTR checks.

Never implement provider bypass/spam evasion.

## Acceptance

- analytical queries do not scan operational message tables unbounded.
- all dashboards enforce tenant scope.
- no invented revenue; attribution only from customer-supplied conversion/revenue events.
- bounce/complaint spike opens alert and can trigger policy suspension.

---

# PHASE 10 — Corporate web product: polished customer/admin portal, content studio, journey builder

## Objective

Build a modern SaaS frontend that exposes the backend already present and the new enterprise features.

Preferred implementation: Next.js/React/TypeScript or the existing frontend stack if already established. Do not rebuild the API in the frontend.

## Global layout

Desktop:

```text
+---------------------------------------------------------------+
| Top bar: org switcher | environment | search | help | user    |
+------------------+--------------------------------------------+
| Left nav         | Page header / actions                      |
|                  +--------------------------------------------+
| Overview         | Main content                               |
| Email            |                                            |
| Contacts         |                                            |
| Automations      |                                            |
| Analytics        |                                            |
| Deliverability   |                                            |
| Developer        |                                            |
| Billing          |                                            |
| Settings         |                                            |
+------------------+--------------------------------------------+
```

Responsive tablet/mobile with collapsible navigation; critical admin workflows remain usable at 1366x768 minimum target.

## Routes/pages

### Home

- `/app/overview`
  - delivery volume card
  - delivery/bounce/complaint rates
  - queue health
  - active campaigns/journeys
  - domain alerts
  - plan usage
  - onboarding checklist

### Email

- `/app/email/messages`
- `/app/email/messages/[id]`
- `/app/email/streams`
- `/app/email/domains`
- `/app/email/domains/[id]`
- `/app/email/senders`
- `/app/email/inbound`
- `/app/email/suppressions`

Message detail must show timeline: accepted -> queued -> provider -> delivered/bounced/complained plus correlation/request IDs.

### Content

- `/app/content/templates`
- `/app/content/templates/[id]`
- `/app/content/builder/[id]`
- `/app/content/media`
- `/app/content/brand`

Builder features:

- responsive drag/drop blocks
- columns, text, button, image, divider, spacer, social links
- HTML source mode
- plain text
- desktop/mobile preview
- personalization variables
- conditional blocks
- reusable blocks
- brand colors/fonts/logo settings
- version history
- publish/rollback
- test render/test send
- safe HTML sanitizer

### Contacts and segments

- `/app/audience/profiles`
- `/app/audience/profiles/[id]`
- `/app/audience/imports`
- `/app/audience/segments`
- `/app/audience/segments/[id]`
- `/app/audience/preferences`

Segment builder uses nested AND/OR/NOT rule groups, estimated count, sample profiles, exclusions, and last materialization status.

### Campaigns

- `/app/campaigns`
- `/app/campaigns/new`
- `/app/campaigns/[id]`

Wizard:

1. type/stream
2. audience
3. sender
4. template/content
5. tracking
6. schedule/timezone
7. preflight
8. confirmation

Progress view shows batches, eligible/suppressed/invalid/sent/delivered/bounced/complaints/cancelled.

### Journeys

- `/app/journeys`
- `/app/journeys/new`
- `/app/journeys/[id]/builder`
- `/app/journeys/[id]/runs`

Canvas:

- left node palette
- center graph
- right node configuration
- version/publish controls
- validation errors
- run debugger/history

### Analytics

- `/app/analytics/overview`
- `/app/analytics/campaigns`
- `/app/analytics/journeys`
- `/app/analytics/segments`
- `/app/analytics/links`

Filters: date, domain, stream, campaign, journey, segment.

### Deliverability

- `/app/deliverability`
- `/app/deliverability/domains/[id]`
- `/app/deliverability/ip-pools`
- `/app/deliverability/alerts`

Show DNS checks, TLS, PTR, DKIM version/rotation, queue/defer/bounce/complaint trends, warmup state, reputation state, and remediation instructions.

### Developer

- `/app/developer/api-keys`
- `/app/developer/service-accounts`
- `/app/developer/smtp`
- `/app/developer/webhooks`
- `/app/developer/logs`
- `/app/developer/openapi`

Include copy-safe SDK/curl examples with redacted secrets.

### Billing

- `/app/billing/plan`
- `/app/billing/usage`
- `/app/billing/invoices`
- `/app/billing/payment-methods`

### Settings

- `/app/settings/organization`
- `/app/settings/team`
- `/app/settings/security`
- `/app/settings/sso`
- `/app/settings/scim`
- `/app/settings/retention`
- `/app/settings/audit`
- `/app/settings/integrations`

### Support

- `/app/support`
- `/app/support/tickets/[id]`

### Platform admin

Separate authorization and visual shell:

- `/admin/tenants`
- `/admin/tenants/[id]`
- `/admin/deliverability`
- `/admin/abuse`
- `/admin/queues`
- `/admin/reconciliation`
- `/admin/billing`
- `/admin/system`
- `/admin/audit`

## Frontend requirements

- OIDC Authorization Code + PKCE.
- no privileged secrets in browser storage.
- tenant derived from authorized session, not arbitrary client header.
- route-level RBAC.
- accessibility target WCAG 2.1 AA.
- CSP-compatible assets.
- no raw HTML rendering without sanitizer.
- error boundary and request-id display for support.
- optimistic updates only where server version/idempotency makes them safe.

## Acceptance

Playwright tests for all critical flows and roles: OWNER, ADMIN, DEVELOPER, MARKETING, BILLING, SUPPORT, ANALYST/READ_ONLY.

---

# PHASE 11 — Compliance, privacy, data governance, and enterprise audit

## Objective

Make consent, retention, DSAR, deletion, legal hold, audit, and data residency enforceable product features.

## Features

- global and topic unsubscribe.
- double opt-in workflow when configured.
- consent source/version/proof.
- complaint/hard-bounce suppression.
- tenant retention policy.
- profile/message-event retention.
- data export request.
- deletion request.
- account closure.
- legal hold.
- admin access audit.
- security event audit.
- export/download expiry.
- encryption key rotation evidence.
- subprocessor/config inventory documentation hooks.
- region/data-residency policy abstraction.

## Endpoints

- `GET /v1/compliance/preferences/{profile_id}`
- `PUT /v1/compliance/preferences/{profile_id}`
- `POST /v1/compliance/double-opt-in`
- `POST /v1/compliance/double-opt-in/confirm`
- `POST /v1/privacy/exports`
- `GET /v1/privacy/exports/{id}`
- `POST /v1/privacy/deletions`
- `GET /v1/privacy/deletions/{id}`
- `POST /v1/privacy/deletions/{id}/confirm`
- `GET /v1/settings/retention`
- `PUT /v1/settings/retention`
- `GET /v1/audit/events`
- `POST /v1/admin/legal-holds`
- `DELETE /v1/admin/legal-holds/{id}`
- `GET /v1/admin/compliance/retention-jobs`

## Database layout

### `retention_policies`

- tenant_id
- profile_days
- message_metadata_days
- message_content_days
- event_days
- audit_days
- attachment_days
- updated_by
- version

### `privacy_requests`

- id
- tenant_id
- request_type (`EXPORT|DELETE|RECTIFY`)
- subject_type
- subject_id/email hash
- state
- requested_by
- confirmation_hash/reference
- created_at
- due_at
- completed_at
- object_reference nullable
- error_code_safe

### `legal_holds`

- id
- tenant_id nullable
- scope_type
- scope_id
- reason
- created_by
- created_at
- released_by nullable
- released_at nullable

### `retention_jobs`

- id
- tenant_id
- policy_version
- resource_type
- state
- cursor
- scanned_count
- deleted_count
- skipped_legal_hold_count
- started_at
- completed_at

### `security_audit_events`

Append-only, partitioned:

- id
- tenant_id nullable
- actor_type
- actor_id
- action
- resource_type
- resource_id
- source_ip safely stored according to policy
- user_agent_hash/details policy
- request_id
- correlation_id
- result
- created_at
- evidence_json without secrets

## Compliance rules

- suppression enforcement always wins over campaign state.
- deletion never erases records under active legal hold; records are marked/isolated according to policy.
- billing/tax/security evidence retention follows documented legal basis.
- export objects expire and require authorized access.
- no claim of SOC 2/ISO/GDPR certification merely because features exist; certification/evidence is separate.

## Acceptance

- DSAR export contains only one tenant/subject.
- deletion is idempotent and legal-hold aware.
- retention job cannot delete another tenant.
- audit is append-only to ordinary tenant admins.

---

# PHASE 12 — Corporate production certification: load, failover, security, tenant isolation

## Objective

Prove the completed platform is reliable and secure under expected corporate load and failure conditions.

## Certification environments

- isolated performance environment built from production-equivalent images/configuration.
- synthetic tenants/profiles/messages only for load testing.
- bounded real production canaries only after explicit gate approval.

## Required test suites

### API/load

Test at minimum:

- authenticated API read/write throughput.
- email submission.
- profile/event batch ingestion.
- segment preview/materialization.
- campaign planning/batching.
- journey wakeups.
- webhook dispatch.
- analytics queries.

Measure P50/P95/P99, RPS, errors, CPU, memory, DB connections, broker depth, oldest job age, Redis memory, worker utilization.

### Failure injection

- gateway node loss.
- worker loss during lease.
- Redis unavailable.
- broker node unavailable.
- PostgreSQL primary failover in non-destructive controlled test.
- Postal temporary outage.
- Middleware outage.
- webhook destination outage.
- analytics store outage.

Require no data loss and no duplicate logical business effect.

### Tenant isolation

Automated matrix for every tenant-scoped API/table:

- cross-tenant object ID -> 404/denied.
- forged tenant header -> denied/ignored.
- API key from tenant A -> cannot read/write tenant B.
- SMTP credential A -> cannot send as domain/sender B.
- webhook event A -> cannot be replayed into B.
- billing record A -> cannot be read by B.
- SAML/SCIM connection A -> cannot provision B.
- database RLS negative tests.

### Security

- SAST/secret scan.
- dependency/container scan.
- SBOM/provenance/signature.
- auth negative tests.
- IDOR.
- SSRF.
- CORS/CSRF where relevant.
- webhook replay.
- path traversal/upload/attachment handling.
- rate-limit bypass attempts.
- open relay denied.
- no public DB/Redis/RabbitMQ/admin ports.
- TLS policy.

### Deliverability

- SPF/DKIM/DMARC/PTR/TLS/HELO/return-path alignment.
- bounce and complaint processing.
- suppression.
- one real bounded canary per approved release/domain.
- no bulk activation as part of certification.

## Certification endpoints/evidence

- `GET /v1/admin/certification/status`
- `GET /v1/admin/certification/components`
- `GET /v1/admin/certification/evidence`

These endpoints expose safe status/identifiers only, never secrets or raw scanner credentials.

## Required release evidence

- source SHA.
- immutable image digest.
- signed release/attestation.
- SBOM.
- provenance.
- vulnerability results.
- migration state.
- backup checksum.
- restore evidence.
- load report.
- failure report.
- tenant isolation report.
- API/webhook security matrix.
- deliverability canary evidence.
- rollback plan.

## Final gates

Do not certify unless all are true:

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

Final terminal status:

`KLYROW_CORPORATE_EMAIL_SAAS_PRODUCTION_CERTIFIED`

---

# Cross-cutting scopes and permissions

Add/reuse explicit scopes; map roles to least privilege.

Recommended scopes:

- `mail.read`
- `mail.send`
- `mail.admin`
- `domain.read`
- `domain.manage`
- `sender.manage`
- `template.read`
- `template.manage`
- `profile.read`
- `profile.manage`
- `event.ingest`
- `segment.read`
- `segment.manage`
- `campaign.read`
- `campaign.manage`
- `journey.read`
- `journey.manage`
- `analytics.read`
- `deliverability.read`
- `deliverability.manage`
- `webhook.read`
- `webhook.manage`
- `billing.read`
- `billing.manage`
- `team.read`
- `team.manage`
- `enterprise.read`
- `enterprise.manage`
- `compliance.read`
- `compliance.manage`
- `audit.read`
- `support.manage`
- `platform.admin`

`platform.admin` is never grantable by a tenant admin, SAML group mapping, SCIM group, or ordinary API key.

# Migration and compatibility policy

- Discover current tables/routes before adding anything.
- Prefer additive forward migrations.
- Do not rename/remove a public route without a compatibility period.
- Do not create duplicate sources of truth for billing, canary gate, tenant membership, message state, suppression, or domains.
- When replacing an existing foundation, write a data migration + rollback + compatibility adapter.
- Every phase must include migration upgrade/reapply/rollback tests on disposable PostgreSQL.

# Implementation sequencing

Implement in this exact order unless a verified dependency requires a small preparatory change:

1. production handshake/reconciliation
2. distributed gateway/workers/rate limits
3. journey engine
4. campaign execution
5. scalable segmentation/profile events
6. HA/DR
7. entitlements/payment billing
8. SAML/SCIM enterprise identity
9. analytics/deliverability
10. product frontend
11. compliance/data governance
12. full certification

Each phase must produce source, migrations, API/OpenAPI updates, SDK updates where public, tests, operational docs, dashboards/alerts, rollback instructions, and evidence.
