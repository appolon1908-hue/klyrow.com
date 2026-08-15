# Deployment report — 2026-08-15

## Implemented

Branch `agent/production-email-platform` contains a validated Compose architecture for Klyrow, Mautic 7.1.3, Postal 3.3.7, isolated databases/RabbitMQ, Prometheus/Grafana, gateway/client portal, RBAC, tenant scoping, API keys, domain verification, safe sending, suppressions, quotas, signed webhooks, replay defense, backups, restore and operational scripts. Production secrets were generated locally with mode 0600.

## Host inventory

The host is `37.27.128.39` with private address `10.40.0.2`, Docker 29.7.2 and Compose 5.4.0. It has ample capacity. A shared host Nginx already owns ports 80/443; Klyrow web services therefore bind only to loopback and the proposed server blocks are staged, not silently installed over unrelated production configuration.

## Launch gates

- DNS: web A records pass; `mail` A, MX, SPF, DKIM and DMARC require owner/provider publication.
- PTR: provider must set `37.27.128.39 -> mail.klyrow.com`.
- TLS: obtain certificates after missing DNS is published; current shared proxy must be reviewed/backed up before installation.
- Middleware: `10.40.0.1:8443` is unreachable and referenced SSH files/account are absent on this host.
- Postal: admin, Klyrow organization, development-mode server, API/SMTP credentials, persistent signing key, web, SMTP and worker are operational. Production mode remains gated on DNS/PTR/TLS.
- Mautic: installed with a secured admin; web, cron and worker are operational, and authenticated SMTP handoff to Postal passes.
- External delivery: intentionally not attempted; safe mode remains enabled.

These are credential, DNS/PTR provider, or shared-production-change boundaries explicitly reserved for the owner. All non-blocked implementation and local validation results should be updated below during deployment.

## Validation record

- Docker Compose config: passes
- Gateway unit/integration tests: 5 passed (auth, tenant isolation, key revocation, suppression/safe send, signature/replay)
- Container health and persistence: all 13 services survived restart; gateway, Mautic, Postal web and databases report healthy
- Admin login: gateway passed; Mautic installed; Postal login route returns expected redirect
- Mautic-to-Postal: DSN verified and authenticated SMTP handshake passed without external delivery
- Signed webhook: valid event accepted; invalid and replay behavior covered by tests
- Backup/restore: all three database dumps created, checksums pass, PostgreSQL catalog and gzip streams validate; destructive production restore was not run
- Public routes/TLS: blocked by shared proxy change and missing DNS/certificates
- Middleware private connectivity: failed (timeout)
- External mail: not authorized and not attempted
