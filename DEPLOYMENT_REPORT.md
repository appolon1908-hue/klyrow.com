# Deployment report — SMTP and DNS production readiness — 2026-08-15

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

- Publish and verify the exact A, MX, SPF, live Postal DKIM, Postal verification, return-path CNAME, and staged DMARC records in `docs/MAIL_DNS.md`.
- Provider must replace PTR `Ubuntu-jammy-latest-amd64-base.zst` with `mail.klyrow.com`.
- Confirm the hosting provider permits outbound TCP/25; direct probes currently time out.
- After DNS propagation, issue/mount the trusted mail SMTP certificate, enable STARTTLS, and verify renewal/reload.
- Enable approved n8n/Odoo middleware targets and credentials; middleware itself is healthy at `10.40.0.1:8095`.
- Complete dedicated `klyrow-deploy` SSH account/authorized-key setup on the correct host.
- Owner must authorize a controlled external recipient and validate delivered/bounce/complaint flows.

Unrestricted delivery remains disabled. Do not set both `KLYROW_SAFE_MODE=false` and `KLYROW_PRODUCTION_GATE_APPROVED=true` until every blocker and the consent/suppression acceptance test passes.

### Latest access and public-DNS recheck

On the latest 2026-08-15 run, the dedicated `klyrow-deploy` key and all locally available administrative SSH identities were rejected by `37.27.128.39`. The reported Hetzner TCP/25 policy change therefore could not be verified from the source server, and no server configuration, backup, certificate, listener, or SMTP credential was changed.

Cloudflare public DNS and both authoritative GoDaddy nameservers still return no mail A, apex/bounce MX, SPF/helper SPF, live DKIM, Postal verification, or PSRP CNAME. PTR now answers `static.39.128.27.37.clients.your-server.de.`, not `mail.klyrow.com`; FCrDNS fails. No DNS-provider credential or approved canary recipient is available locally. No delivery or bounce message was sent. Status remains **BLOCKED-EXTERNAL**.

## Mail readiness audit

- Postal 3.3.7 and Mautic 7.1.3 containers are healthy. The verified outbound IPv4 is `37.27.128.39`; IPv6 is not authorized for mail.
- The live Postal domain `klyrow.com` was created once in Development mode and generated selector `postal-QQaKrT`. The private key was not printed or committed.
- Public DNS is missing mail A, apex/bounce MX, SPF, live DKIM, Postal verification, and return-path CNAME. Existing DMARC is conflicting with the staged monitoring contract. PTR is incorrect and forward-confirmed rDNS fails.
- SMTP banner/HELO is `mail.klyrow.com`; STARTTLS and a mail-host certificate are absent. SMTP remains loopback-only, and the firewall exposes no SMTP ports.
- Mautic-style authenticated SMTP login passes. An unauthenticated relay attempt is rejected. Synthetic safe send, signed webhook, replay rejection, and invalid-HMAC rejection pass; no controlled external delivery was authorized or attempted.
- The required outcome remains `BLOCKED-EXTERNAL`.

## P1/P2 backlog

P1 foundations still need production UI/workers for statistical confidence, external AI with tenant opt-in/redaction, cohort/revenue attribution from real events, connector execution/retry, invoice/payment adapters, and expanded admin visualizations. P2 remains SSO/SAML/OIDC, distributed rate limiting, multi-node orchestration/HA databases, rolling migrations, advanced support access, and a separately permissioned Telnexa contract.
