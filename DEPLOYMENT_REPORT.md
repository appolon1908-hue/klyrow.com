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

- DNS provider work is complete: exact A, MX, SPF, live Postal DKIM, Postal verification, return-path CNAME, and single staged DMARC records all pass publicly.
- Provider must replace PTR `static.39.128.27.37.clients.your-server.de.` with `mail.klyrow.com.`.
- Outbound TCP/25 is verified; preserve provider and firewall controls.
- After PTR correction, issue/mount the trusted mail SMTP certificate, enable STARTTLS, and verify renewal/reload.
- Supply or authorize access to the Odoo SMTP configuration so its Postal credentials can be verified; no Odoo service or configuration is present on this host and private-host SSH authentication is unavailable.
- Preserve the dedicated deployment identity's least-privilege access; do not broaden it casually.
- Owner must authorize a controlled external recipient and validate delivered/bounce/complaint flows.

Unrestricted delivery remains disabled. Do not set both `KLYROW_SAFE_MODE=false` and `KLYROW_PRODUCTION_GATE_APPROVED=true` until every blocker and the consent/suppression acceptance test passes.

### Latest access and public-DNS recheck

On the latest 2026-08-15 run, the dedicated `klyrow-deploy` identity connected successfully to `37.27.128.39`. Connection-only probes to the primary Gmail and Outlook MX hosts both returned `220` banners, so `OUTBOUND_TCP25=PASS`; no mail command or message was sent. The identity is intentionally least-privilege and cannot perform DNS/PTR, Certbot/Nginx, backup, firewall, Docker-configuration, or secret changes. No server configuration, certificate, listener, or SMTP credential was changed.

Cloudflare, Google, and both authoritative GoDaddy nameservers now return the complete required mail record set. PTR still answers `static.39.128.27.37.clients.your-server.de.`, not `mail.klyrow.com`; identity-matched FCrDNS fails. No approved canary recipient is available. No delivery or bounce message was sent. Status remains **BLOCKED-EXTERNAL**.

## Mail readiness audit

- Postal 3.3.7 and Mautic 7.1.3 containers are healthy. The verified outbound IPv4 is `37.27.128.39`; IPv6 is not authorized for mail.
- The live Postal domain `klyrow.com` was created once in Development mode and generated selector `postal-QQaKrT`. The private key was not printed or committed.
- Public forward DNS passes on both authoritative servers and independent resolvers. Postal reports the domain verified with SPF, DKIM, MX, and return path all `OK`. PTR is still incorrect, so identity-matched forward-confirmed rDNS fails.
- SMTP banner/HELO is `mail.klyrow.com`; STARTTLS and a mail-host certificate are absent. SMTP remains loopback-only, and the firewall exposes no SMTP ports.
- Forced-IPv4 outbound TCP/25 passes to two external MX hosts. Mautic authenticated SMTP login passes and an unauthenticated relay attempt is rejected. Odoo → Postal is not verifiable without Odoo access/configuration. No controlled external delivery was authorized or attempted.
- The required outcome remains `BLOCKED-EXTERNAL`.

## P1/P2 backlog

P1 foundations still need production UI/workers for statistical confidence, external AI with tenant opt-in/redaction, cohort/revenue attribution from real events, connector execution/retry, invoice/payment adapters, and expanded admin visualizations. P2 remains SSO/SAML/OIDC, distributed rate limiting, multi-node orchestration/HA databases, rolling migrations, advanced support access, and a separately permissioned Telnexa contract.
