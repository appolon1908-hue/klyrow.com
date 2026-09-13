# Klyrow staging build and certification

Status: **SOURCE READY / RUNTIME NOT YET CERTIFIED**.

This repository now supplies a fail-closed staging topology and operator gates. It does not claim that Keycloak, OpenBao, Middleware, Odoo, DNS, TLS, or a server was changed merely because these files exist.

## Release inputs

Use only the exact digests produced by protected `main` after tests, HIGH/CRITICAL scanning, SBOM generation, provenance and signature verification pass. Copy `deploy/staging/staging.env.example` to a root-owned `staging.env` outside Git and replace every placeholder. `scripts/staging-preflight` rejects tags and non-exact source revisions.

The public edge exposes only TCP 80/443. PostgreSQL, search, Prometheus and Grafana remain on internal Docker networks. Grafana has no Caddy route and no native monitoring or search port is published; operators must use the approved private access path.

## External authority gates

These gates are owned by their respective repositories and must be proven before `scripts/staging-deploy` is run:

1. Apply `deploy/staging/keycloak/kyyow-realm.json` through the reviewed Keycloak deployment path. Verify authorization-code flow with PKCE S256, exact redirects, MFA policy, realm roles and disabled Direct Access Grants.
2. Provision the files listed by the staging Compose secret declarations with the OpenBao agent. Apply `deploy/staging/openbao/klyrow-staging.hcl` to the Klyrow workload identity. Prove that Middleware can read its Odoo writer credential and Klyrow/telemetry identities are denied.
3. At the exact `KLYROW_MIDDLEWARE_SOURCE_SHA`, prove migration `0061` is present in the Middleware ledger and applied once to staging.
4. At the exact `KLYROW_ODOO_SOURCE_SHA`, install or upgrade `codestra_klyrow_observability`, restart only the staging Odoo workers through the governed deployment, and read back the installed module version.
5. Create the staging DNS record, verify it resolves to the intended edge, then allow Caddy to obtain TLS. Do not publish Grafana, Prometheus, Alertmanager, Loki, Tempo, OpenBao, PostgreSQL, Redis or search native ports.

## Deploy

```bash
sudo KLYROW_STAGING_CONFIRM=DEPLOY-KLYROW-STAGING \
  scripts/staging-deploy /etc/klyrow/staging/staging.env
```

The deployment remains in safe mode with live/external delivery and production provider routing disabled.

## Certification matrix

Every result must include UTC timestamp, environment, exact Klyrow/Middleware/Odoo SHAs, image digests, correlation ID where applicable, sanitized request/response hashes and PASS/FAIL. Never capture tokens, cookies, email bodies, passwords, raw PII or secret values.

| Area | Required proof |
| --- | --- |
| Identity | OIDC discovery; authorization-code + PKCE; invalid state/nonce/verifier denial; logout; MFA/step-up; human and service identity separation |
| Isolation | tenant A cannot read/write tenant B; workspace A cannot read/write workspace B; missing membership and wrong role denied before data access |
| KPI flow | collector emits synthetic KPI → Middleware authenticates and durably enqueues → Odoo upserts once → API read-back matches semantic hash |
| Incident flow | Alertmanager firing and resolved events retain one incident identity through Middleware queue and Odoo read-back |
| Ordering | exact duplicate returns prior result; changed duplicate conflicts; concurrent duplicates create one mutation; stale event rejected; newer-before-older leaves newest state |
| Security | PII and secret canaries rejected and absent from logs, traces and durable evidence; Klyrow and observability identities cannot obtain Odoo writer credentials |
| Recovery | restart API and worker mid-flight; recover durable queue; restart Odoo; drain backlog exactly once; stop/restart observability without blocking application work |
| Observability | targets healthy; alerts fire and resolve; dashboards query private data sources; no native monitoring ports reachable from the public network |
| Capacity | portal/API/search workload at configured VUs; publish p50/p95/p99, throughput, errors, saturation and queue depth against declared SLOs |

Certification is PASS only when all rows pass against the same immutable release. Any missing external evidence is FAIL, not `N/A`. Production remains blocked until backup/restore and rollback rehearsals also succeed and an explicit owner go/no-go is recorded.

## Rollback

Keep the previous digest set and database backup. On failure, stop admission at Caddy, disable workers, capture sanitized queue/ledger state, restore only through the reviewed restore runbook, redeploy the prior digest set, and verify identity, readiness, queue and read-back before reopening staging. Never delete a failed-event queue to make certification green.
