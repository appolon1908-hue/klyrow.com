# Server 37 email platform read-first evidence — 2026-09-02

Scope: `37.27.128.39` (`Ubuntu-jammy-latest-amd64-base.zst`). This evidence is
sanitized: it records variable names and secret-file references only. It does
not contain credentials, private keys, tokens, authorization headers, message
bodies, recipients, or database data.

No service was restarted, replaced, or reconfigured while collecting this
inventory. No email was submitted. SSH configuration, ports, keys, and policy
were not changed.

## Git and source authority

- Canonical repository: `appolon1908-hue/klyrow.com`
- Remediation PR: `#65`
- Reviewed branch: `remediation/server37-production-cert-20260902`
- Inventory-start head: `eeaf604e0189dcb3c791ae3dcc001c8236883db6`
- Merged production activation base: `27c920957e116ae7fe998395393adc3c3dfdb6be`
- Recovered live snapshot: `cab2e2...` (detached comparison authority)
- Server-local source classification: `UNKNOWN=0`, `MISSING_FROM_GIT=0`,
  `OBSOLETE=32`, `LEGACY=4`, `RUNTIME_CONFIG_ONLY=1`.

The live gateway reports revision `9684fd55bdbc64a971a17a291ff293a178a2ebac`.
It is older than PR #65. The gateway, worker, web, and Postal provisioner use
mutable local tags and/or lack the required OCI source/revision labels; they are
not acceptable production release authority.

## Runtime inventory

All listed services were running at capture time. `unless-stopped` was the
restart policy for each listed container.

| Container | Compose project | Image authority | Health/readiness observation |
|---|---|---|---|
| klyrow-gateway-1 | klyrow-release | local image `7cb3769eceb3...`, no OCI revision | healthy; `/health`, `/readiness`, `/dependencies`, `/capabilities` absent in live image |
| klyrow-worker-1 | klyrow-release | local image `7cb3769eceb3...`, no OCI revision | healthy |
| klyrow-smtp-relay-1 | klyrow-release | local image `102d79b3ce37...`, revision `9684fd55...` | healthy; private `10.40.0.4:587` |
| klyrow-postal-provisioner-1 | klyrow-release | local image `2bd3c7123f26...`, no OCI revision | healthy |
| klyrow-billing-api-1 | klyrow-release | local image `b64e9364400e...`, revision `9684fd55...` | healthy |
| klyrow-billing-worker-1 | klyrow-release | local image `b64e9364400e...`, revision `9684fd55...` | healthy |
| klyrow-scheduler-1 | klyrow-release | local image `b64e9364400e...`, revision `9684fd55...` | healthy |
| klyrow-web-candidate | standalone | local image `dd4a20b1c80f...`; upstream Nginx label only | healthy; loopback `18004` |
| klyrow-postal-smtp-1 | klyrow | `ghcr.io/postalserver/postal:3.3.7`, local image `e54b4a7eb106...` | healthy; public `37.27.128.39:25`, loopback `2525` |
| klyrow-postal-web-1 | klyrow | `ghcr.io/postalserver/postal:3.3.7`, local image `e54b4a7eb106...` | healthy; loopback `18002` |
| klyrow-postal-worker-1 | klyrow | `ghcr.io/postalserver/postal:3.3.7`, local image `e54b4a7eb106...` | healthy |
| klyrow-mautic-1 | klyrow | local image `907879ba89f2...`, source PR revision `42628161...` | healthy; loopback `18001` |
| klyrow-mautic-cron-1 | klyrow | same Mautic image | no healthcheck |
| klyrow-mautic-worker-1 | klyrow | same Mautic image | no healthcheck |
| klyrow-postgres-1 | klyrow | `postgres:17.6-bookworm`, local image `f3bd19c606e4...` | healthy; private only |
| klyrow-postal-db-1 | klyrow | `mariadb:11.4.8`, local image `bc474f00629f...` | healthy; private only |
| klyrow-mautic-db-1 | klyrow | `mariadb:11.4.8`, local image `bc474f00629f...` | healthy; private only |
| klyrow-rabbitmq-1 | klyrow | `rabbitmq:4.1.3-alpine`, local image `a6dbb0d4e409...` | healthy; private only |
| klyrow-prometheus-1 | klyrow | `prom/prometheus:v3.5.0`, local image `63805ebb8d2b...` | no healthcheck |
| klyrow-grafana-1 | klyrow | local image `9b58461280b4...` | healthy; loopback `18003` |
| klyrow-node-exporter-1 | klyrow | `prom/node-exporter:v1.9.1`, local image `d00a542e409e...` | no healthcheck |

Networks: `klyrow_backend` is internal; `klyrow_frontend` is not internal.
Named volumes cover Klyrow PostgreSQL, both MariaDB-backed applications, Postal
assets/configuration, Mautic config/media/logs, RabbitMQ, Prometheus, Grafana,
and DKIM material.

Active Compose inputs and SHA-256 checksums:

- `/root/klyrow.com/docker-compose.yml`: `19eb47fa...`
- `/root/klyrow.com/docker-compose.override.yml`: `e0d74068...`
- `/opt/klyrow/docker-compose.release.yml`: `d0c6673e...`
- `/opt/klyrow/docker-compose.mtls.yml`: `e9e2b697...`
- `/opt/klyrow/docker-compose.final.yml`: `24947a6b...`
- `/opt/klyrow/docker-compose.smtp-hotfix.yml`: `4321938f...`
- `/opt/klyrow/docker-compose.webmail-override.yml`: `09b2a668...`

## Environment variable names

Names were enumerated without values. Klyrow workloads use the `KLYROW_*`
delivery, identity, database, migration, callback, mTLS, metrics, canary, and
secret-file variables declared by Compose. Secret-capable names observed
include `KLYROW_DATABASE_URL`, `KLYROW_MIDDLEWARE_API_KEY`,
`KLYROW_POSTAL_API_KEY`, `KLYROW_POSTAL_API_KEY_FILE`,
`KLYROW_POSTAL_PROVISIONER_TOKEN_FILE`, `KLYROW_PROVIDER_CREDENTIAL_KEY_FILE`,
`KLYROW_SESSION_SECRET`, `KLYROW_SESSION_SECRET_FILE`,
`KLYROW_WEBHOOK_SECRET`, `KLYROW_SERVER_A_CLIENT_KEY_FILE`,
`KLYROW_POSTAL_WEBHOOK_PUBLIC_KEY`, `KLYROW_DKIM_KEY_DIR`, database password
names, the RabbitMQ password name, Postal signing/secret-key names, and Mautic
mailer/database variable names. No value was copied into this evidence.

## Read-only findings and current gates

- Existing live delivery gates are open on the gateway and worker. This was a
  pre-existing state. Postal has active credentials and an empty current queue.
- Fourteen managed Postal domains report enabled inbound/outbound. Current
  independent DNS and SMTP transport read-back is recorded in
  `SERVER37_DOMAIN_DNS_20260902.md`; active-selector exposure/rotation history
  still prevents mail-domain certification.
- Migration `2026090208_runtime_database_least_privilege.sql` was applied to the
  live database at `2026-09-02T17:08:45Z` and created `klyrow_runtime` with no
  superuser, role-creation, database-creation, replication, or RLS-bypass
  privileges. The old gateway and worker containers have not been replaced and
  still use legacy role `klyrow`, which remains cluster-privileged. Runtime
  least-privilege certification therefore remains `FAIL` until an immutable
  release switches the application role and current connection read-back
  proves it.
- A same-day local backup exists and its local manifest verifies, but the active
  backup job is the legacy plaintext workflow. The approved encrypted backup
  recipient is not installed and current off-host/restore evidence is absent.
- The live health surface and custom-image provenance do not meet the mission.
- Source/runtime deployment is held until PR #65 exact-head CI, immutable image
  digests, encrypted off-host backup, isolated restore, and safe staging tests
  pass.

Current non-claims:

`EMAIL_SENT_UNINTENTIONALLY=0`

`SSH_CHANGED=NO`

`SERVER37_EMAIL_PLATFORM=NOT_YET_PRODUCTION_READY`

## Repository remediation candidate (not runtime evidence)

PR #65's working candidate now closes the source-level findings without
changing the running host:

- the five-command Klyrow API stores the normalized request before returning
  acceptance and the mail worker reclaims interrupted commands;
- email submission, lifecycle callback, and provider-event outboxes use stable
  idempotency/correlation/operation identifiers, claim serialization, bounded
  retries, and `unknown_outcome` read-back rather than blind resubmission;
- Postal Hash inbound delivery requires its RSA SHA-256 body signature, a
  bounded provider timestamp, an exact enabled tenant route, replay/message
  deduplication, attachment/message limits, and quarantine because Hash does
  not provide trusted SPF/DKIM/DMARC results;
- Postal route reconciliation preserves foreign routes and accepts only exact
  reviewed addresses; mailbox storage enforces tenant ownership, role grants,
  byte quotas, and retrievable attachment authority;
- database owner/runtime credentials are file-backed, the migration runner
  provisions fixed role `klyrow_runtime`, and production startup rejects any
  unexpected or cluster-privileged application role;
- encrypted backup now includes the three databases, Mautic persistent files,
  drained RabbitMQ definitions/evidence, an atomic checksummed off-host copy,
  and an isolated no-network restore harness;
- every long-running production service has a functional or dependency-aware
  healthcheck; production launchers require protected release evidence, exact
  digest/OCI source identity, a reviewed configuration checksum, and a prior
  rollback digest set.

Local evidence at the candidate working tree:

- targeted contract/security tests: `93/93 PASS`, followed by focused
  database/release regressions `78/78 PASS`;
- PostgreSQL 17.6 ordered migration replay: `33/33 PASS` on two runs;
- application runtime role: `klyrow_runtime`, cluster privileges: `0`;
- rendered 23-service Compose: digest validation and healthcheck coverage
  `PASS`.

These results do not change the production-ready non-claim. Exact-head CI,
protected merge, published digests/attestations, approved backup recipient and
off-host mount, isolated restore of a fresh production backup, DNS/domain
read-back, and safe staging remain required.
