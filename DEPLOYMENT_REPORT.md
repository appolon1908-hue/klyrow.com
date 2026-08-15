# Deployment report — SMTP and DNS production readiness — 2026-08-15

## Implemented

P0 is implemented additively on the Mautic 7.1.3 → Postal 3.3.7 stack: unified profiles/events and identity merging; nested behavioral segmentation with suppression-aware preview; journey graph validation, version records, lifecycle and per-profile goal history; consent/preferences with marketing enforcement; onboarding wizard/UI; deliverability snapshots/alerts; real-event analytics; OpenAPI, idempotency, correlation IDs and latency metrics; safe personalization; TOTP MFA, recovery hashes and revocable sessions; audit/admin hardening; private middleware service authentication; and a two-part production gate.

Safe P1 foundations cover deterministic experiment assignment/results, disabled-by-default AI abstraction, connector records, provider-neutral plans/subscriptions/usage ledger, and admin operations. No billing or external AI call is active.

Existing hardening is preserved: STARTTLS-enabled standard SMTP, private-vSwitch gateway listener, node-exporter, Postal worker/SMTP health checks, systemd stack/backup units, safer middleware networking, backup/restore refinements, and controlled smoke tools.

## Deployed and tested

- Live stack backed up to `backups/20260815T073357Z` before schema deployment.
- Gateway rebuilt and additive PostgreSQL tables created; node-exporter deployed.
- 14 automated tests pass: auth, isolation, idempotency, suppressions, profile resolution, event timeline, nested segmentation, consent/preferences, stream separation, journey lifecycle/goals, analytics, onboarding gate, OpenAPI, HTML safety, rate limiting, request IDs, MFA/session revocation, experiments, disabled AI, usage ledger and suspension.
- Controlled deployed smoke passes admin login, accepted safe send, no carrier submission, valid signed event, replay rejection and invalid-HMAC rejection.
- Mautic web/cron/worker remain healthy. Postal SMTP DSN is present and authenticated SMTP login passes without external delivery.
- Postal web/SMTP/worker and databases/RabbitMQ are healthy. Postal SMTP is published on standard port 25 with STARTTLS; loopback diagnostics remain available on `127.0.0.1:2525`.
- Gateway health reports `safe_mode=true` and `production_gate_approved=false`.
- Databases/queues remain unexposed. Compose validation and pre-deploy backup pass.

## Remaining launch control

- DNS, PTR, FCrDNS, trusted SMTP TLS, STARTTLS, automatic renewal/reload,
  outbound TCP/25, relay rejection, Mautic authentication, and the dedicated
  Odoo credential all pass host-local readiness.
- Preserve provider/firewall controls and the deployment identity's least privilege.
- The owner must authorize a controlled external recipient before validating
  delivered, bounce, and complaint flows.

Unrestricted delivery remains disabled. Do not set both `KLYROW_SAFE_MODE=false` and `KLYROW_PRODUCTION_GATE_APPROVED=true` until every blocker and the consent/suppression acceptance test passes.

## Mail readiness audit

- Postal 3.3.7 and Mautic 7.1.3 containers are healthy. The verified outbound IPv4 is `37.27.128.39`; IPv6 is not authorized for mail.
- The live Postal domain `klyrow.com` was created once in Development mode and generated selector `postal-QQaKrT`. The private key was not printed or committed.
- Public forward DNS, PTR, and identity-matched FCrDNS pass on authoritative
  servers and independent public resolvers. Postal reports SPF, DKIM, MX, and
  return path all `OK`.
- SMTP banner/HELO is `mail.klyrow.com`; STARTTLS uses a trusted matching
  certificate and modern TLS on public port 25.
- Forced-IPv4 outbound TCP/25 passes to two external MX providers. Mautic
  authenticated SMTP passes, unauthenticated relay and invalid authentication
  are rejected, and a dedicated Odoo credential is prepared outside Git.
- No controlled external delivery was authorized or attempted. Status is
  `READY-FOR-CANARY`.

### Postal SMTP TLS completion — 2026-08-15 20:28 CEST

- Public forward DNS, authoritative PTR (`mail.klyrow.com.`), and
  identity-matched FCrDNS pass.
- Some recursive resolver edges intermittently served the prior Hetzner PTR
  during its 86400-second cache lifetime; all authoritative reverse nameservers
  consistently serve the new PTR. Treat the authoritative result as current
  state and expect recursive caches to converge naturally.
- A dedicated trusted Let's Encrypt certificate for `mail.klyrow.com` is valid
  through 2026-11-13. Its SAN, issuer, full chain, and source permissions were
  verified without exposing private material.
- Postal 3.3.7 uses the supported `smtp_server.tls_enabled: true` configuration
  with `/config/smtp.cert` and `/config/smtp.key`. Only `postal-smtp` was
  recreated/restarted.
- Public port 25 and loopback port 2525 terminate at Postal. EHLO advertises
  STARTTLS; the banner is `mail.klyrow.com`; live validation passes hostname,
  trusted chain, TLS 1.3, and verification code 0.
- Certbot's staging renewal simulation passed. The root-owned, certificate-specific
  deploy hook refreshes Postal's copy and restarts only `postal-smtp`; a live hook
  invocation left the service healthy.
- Outbound TCP/25 passes to Google and Microsoft MX hosts. Invalid credentials
  are rejected with 535, unauthenticated relay is rejected with 530 at RCPT,
  and Mautic authentication plus NOOP passes. No DATA or external message was sent.
- A separate Postal SMTP credential named `odoo-production` was created and is
  distinct from Mautic. Its secret is stored outside Git in a root-only file;
  the Odoo handoff is documented in `docs/ODOO_SMTP.md`.
- Postal remains in Development mode. Klyrow remains in safe mode with its
  production gate disabled. Status is **READY-FOR-CANARY**; CANARY remains
  pending an explicitly approved recipient.

### Odoo credential handoff control — 2026-08-15

The root-owned mode-0755 helper
`/usr/local/sbin/export-odoo-postal-credential` reads only the fixed root-owned
mode-0600 Odoo credential file. It accepts no arguments and strictly emits the
five approved SMTP fields. The only added sudo permission is that exact helper
for `klyrow-deploy`; direct `/etc/klyrow` traversal, arbitrary arguments, and
arbitrary sudo remain denied. Local piped validation passed without displaying
or writing secret values, and no secret marker appears in Git or system logs.

Remote completion is pending because this host cannot authenticate to the Odoo
server at `65.109.65.169` and private-vSwitch SSH to `10.40.0.1` times out. The
middleware operator must pipe the helper directly into its approved root-owned
Odoo secret importer, then run only STARTTLS, AUTH, NOOP, and QUIT. No canary was
sent.

### Controlled Odoo canary release — 2026-08-15 21:02 CEST

Postal contained exactly one held outgoing message: message database ID 1,
submitted with the dedicated `odoo-production` credential and carrying
correlation ID `klyrow-odoo-canary-ad53bfce26504919907e4fe14eef10c4`.
There were no unrelated held or queued messages. A verified backup was captured
at `backups/20260815T185955Z` before mutation.

Postal 3.3.7 supports `Development` and `Live`; the existing `Klyrow Production`
server was changed from Development to Live without recreation, key rotation,
DKIM changes, or send-limit changes. Before promotion, all existing credentials
were placed in Postal hold mode. The original stored message alone was released
through Postal's native manual-release queue path; no second SMTP submission or
DATA command occurred.

The first worker attempt soft-failed because `postal-worker` had only the
internal Docker network and could not resolve external MX hosts. Only that
worker was attached to the existing egress-capable frontend network. Its DNS and
TCP/25 checks then passed, and the same queue item retried. Gmail permanently
rejected it with 550-5.7.26 because SPF and DKIM did not pass. Postal recorded
the original message as HardFail and removed it from the queue. It was not
resent or reconstructed.

No Postal webhook is configured, no matching Klyrow event exists, and no
middleware/n8n/Odoo terminal-status round trip occurred. Postal remains Live
with every credential held; Klyrow remains `safe_mode=true` and
`production_gate_approved=false`. Queue depth is zero. Final canary status:
**FAIL**.

### First-canary SPF/DKIM repair — 2026-08-15

Retained message 1 shows that Postal's stale `Missing` DNS state caused the
delivery return path and DKIM signature to fall back to `bounce.klyrow.com` and
selector `postal`. Neither fallback identity was published, producing Gmail
550-5.7.26. The live `klyrow.com` key itself is valid and exactly matches
`postal-QQaKrT._domainkey.klyrow.com`; it was not rotated.

Refreshing Postal's DNS state restored SPF/DKIM/MX/return-path `OK`. A local
synthetic signature verifies with `d=klyrow.com; s=postal-QQaKrT`, and the next
envelope domain will be aligned `psrp.klyrow.com`. Owner DNS action remains:
publish `bounce.klyrow.com TXT "v=spf1 include:spf.klyrow.com -all"` and wait for
public resolution. No second message was created or sent.

The worker's frontend+backend network attachment is persisted in Compose. A
dedicated RSA-authenticated Postal webhook feeds the Klyrow adapter, which
persists idempotency/retry/DLQ state and signs the existing middleware HMAC
contract. Historical HardFail metadata for message 1 was accepted by middleware
as `email.bounced` with the original correlation ID and no duplicate Klyrow
event. n8n/Odoo completion is not yet evidenced. Status is **BLOCKED-DNS**.

## P1/P2 backlog

P1 foundations still need production UI/workers for statistical confidence, external AI with tenant opt-in/redaction, cohort/revenue attribution from real events, connector execution/retry, invoice/payment adapters, and expanded admin visualizations. P2 remains SSO/SAML/OIDC, distributed rate limiting, multi-node orchestration/HA databases, rolling migrations, advanced support access, and a separately permissioned Telnexa contract.
