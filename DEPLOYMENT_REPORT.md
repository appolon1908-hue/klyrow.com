# Deployment report — SaaS P0/P1 foundation — 2026-08-15

## Implemented

P0 is implemented additively on the Mautic 7.1.3 → Postal 3.3.7 stack: unified profiles/events and identity merging; nested behavioral segmentation with suppression-aware preview; journey graph validation, version records, lifecycle and per-profile goal history; consent/preferences with marketing enforcement; onboarding wizard/UI; deliverability snapshots/alerts; real-event analytics; OpenAPI, idempotency, correlation IDs and latency metrics; safe personalization; TOTP MFA, recovery hashes and revocable sessions; audit/admin hardening; private middleware service authentication; and a two-part production gate.

Safe P1 foundations cover deterministic experiment assignment/results, disabled-by-default AI abstraction, connector records, provider-neutral plans/subscriptions/usage ledger, and admin operations. No billing or external AI call is active.

Existing hardening is preserved: private SMTP binding, private-vSwitch gateway listener, node-exporter, Postal worker/SMTP health checks, systemd stack/backup units, safer middleware networking, backup/restore refinements, and controlled smoke tools.

## Deployed and tested

- Live stack backed up to `backups/20260815T073357Z` before schema deployment.
- Gateway rebuilt and additive PostgreSQL tables created; node-exporter deployed.
- 14 automated tests pass: auth, isolation, idempotency, suppressions, profile resolution, event timeline, nested segmentation, consent/preferences, stream separation, journey lifecycle/goals, analytics, onboarding gate, OpenAPI, HTML safety, rate limiting, request IDs, MFA/session revocation, experiments, disabled AI, usage ledger and suspension.
- Controlled deployed smoke passes admin login, accepted safe send, no carrier submission, valid signed event, replay rejection and invalid-HMAC rejection.
- Mautic web/cron/worker remain healthy. Postal SMTP DSN is present and authenticated SMTP login passes without external delivery.
- Postal web/SMTP/worker and databases/RabbitMQ are healthy. SMTP is host-bound only to `127.0.0.1:2525`.
- Gateway health reports `safe_mode=true` and `production_gate_approved=false`.
- Databases/queues remain unexposed. Compose validation and pre-deploy backup pass.

## External launch blockers

- Publish and verify `mail` A, MX, SPF and deployed Postal DKIM. Review the existing DMARC record against the documented strict policy.
- Provider must replace PTR `Ubuntu-jammy-latest-amd64-base.zst` with `mail.klyrow.com`.
- Issue/mount trusted web and SMTP certificates; verify renewal and expiry monitoring.
- Restore authenticated middleware connectivity to `10.40.0.1:8443`; calls currently fail fast and log safely.
- Complete dedicated `klyrow-deploy` SSH account/authorized-key setup on the correct host.
- Owner must authorize a controlled external recipient and validate delivered/bounce/complaint flows.

Unrestricted delivery remains disabled. Do not set both `KLYROW_SAFE_MODE=false` and `KLYROW_PRODUCTION_GATE_APPROVED=true` until every blocker and the consent/suppression acceptance test passes.

## P1/P2 backlog

P1 foundations still need production UI/workers for statistical confidence, external AI with tenant opt-in/redaction, cohort/revenue attribution from real events, connector execution/retry, invoice/payment adapters, and expanded admin visualizations. P2 remains SSO/SAML/OIDC, distributed rate limiting, multi-node orchestration/HA databases, rolling migrations, advanced support access, and a separately permissioned Telnexa contract.
