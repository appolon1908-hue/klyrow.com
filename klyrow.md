# Codex Mission — Klyrow Production Email Platform

You have full autonomy to build, install, configure, test, harden, document, and prepare production deployment for **klyrow.com** as an open-source email platform.

## Environment

Public server IP:
- `37.27.128.39`

Primary domain:
- `klyrow.com`

Existing DNS shown by the owner already points these A records to `37.27.128.39`:
- `@`
- `api`
- `app`
- `bounce`
- `track`

The repository is:
- `https://github.com/appolon1908-hue/klyrow.com`

Middleware server:
- public IP `65.109.65.169`
- private vSwitch IP `10.40.0.1`

Shared application server private vSwitch IP:
- `10.40.0.2`

Use private vSwitch communication for middleware integration where practical.

## Primary objective

Deliver a production-ready, Dockerized email platform using:

- **Mautic** for campaigns, contacts, segments, marketing automation, templates, journeys, and campaign orchestration
- **Postal** for outbound mail delivery, SMTP/API submission, delivery events, queues, tracking hooks, and mail-server functions appropriate to the selected Postal version
- **SMTP delivery layer** configured correctly for Postal
- PostgreSQL/MariaDB/MySQL only as required by the chosen current versions
- Redis where required
- Nginx or Traefik reverse proxy
- TLS/Let's Encrypt
- background workers/queues
- monitoring and health checks
- backups and restore tooling
- client-facing application layout
- admin-facing operational controls
- middleware API/webhook integration

Do not build a disposable demo. Build a maintainable production stack.

## Required public service layout

Prepare these hostnames:

- `klyrow.com` — main website/landing entry
- `www.klyrow.com` — website alias
- `app.klyrow.com` — authenticated customer/admin application entry
- `api.klyrow.com` — customer/API integration entry
- `track.klyrow.com` — tracking domain
- `bounce.klyrow.com` — bounce/return-path processing domain
- `mail.klyrow.com` — mail host / SMTP identity where appropriate

Do not expose internal databases, Redis, Docker socket, or private admin services publicly.

## DNS work

Inspect actual DNS and current application requirements before declaring DNS complete.

Prepare/document exact records required for production mail delivery, including where applicable:

- A/AAAA
- MX
- SPF
- DKIM
- DMARC
- bounce/return-path records
- tracking-domain records
- autodiscovery only if actually needed
- PTR/rDNS requirements for the server IP

Do not invent DKIM values. Generate them from the deployed mail system and report the exact DNS records the owner must publish.

Do not claim PTR/rDNS is configured unless it has actually been changed through the hosting provider.

## Dockerization

Run the platform with Docker Compose where practical.

Suggested repository structure:

```text
/
├── apps/
│   ├── gateway/
│   ├── portal/
│   └── middleware-adapter/
├── docker/
│   ├── mautic/
│   ├── postal/
│   └── proxy/
├── config/
├── docs/
├── scripts/
├── tests/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
└── DEPLOYMENT_REPORT.md
```

Use persistent named volumes or explicit data volumes.

Use Docker health checks and restart policies.

## Mautic

Install and configure a current stable Mautic release compatible with the selected PHP/database stack.

Configure:
- production database
- cron/background jobs
- email transport through Postal
- campaign processing
- queue processing
- contacts
- segments
- campaigns
- templates
- unsubscribe handling
- suppression where appropriate
- tracking
- bounce handling integration where supported
- secure admin bootstrap

Do not leave default passwords.

## Postal

Install and configure a current stable Postal release.

Configure:
- web/admin interface where appropriate
- mail server/service
- worker processes
- queues
- SMTP credentials
- API credentials
- domain/sending server configuration
- DKIM signing
- delivery status/event processing
- bounce processing
- webhook/event delivery
- tracking integration where appropriate
- persistent data

Do not use floating `latest` tags where a stable pinned version is available.

Do not commit real secrets.

## SMTP and deliverability

Prepare the system for compliant opt-in and transactional sending.

Implement and document:
- SPF
- DKIM
- DMARC
- PTR/rDNS requirement
- HELO/EHLO identity
- TLS
- bounce handling
- complaint/suppression handling
- unsubscribe processing
- per-customer quotas
- sending-rate controls
- domain verification
- sender authorization

Do not configure features intended to evade spam controls or provider abuse protections.

Do not send unsolicited bulk mail.

## Middleware integration

Connect Klyrow to middleware at private address:
- `10.40.0.1`

Use a dedicated service identity and separate secret from Kyqra/Telnexa.

Create:
- `KLYROW_MIDDLEWARE_API_KEY`
- `KLYROW_WEBHOOK_SECRET`

Store secrets only in `.env` or approved secret storage.

Do not commit secrets.

Use authenticated API calls and HMAC-SHA256 signed webhooks.

Suggested headers:
- `X-Klyrow-Timestamp`
- `X-Klyrow-Event-Id`
- `X-Klyrow-Signature`

Implement replay protection and constant-time signature verification.

## Middleware event model

Support events such as:
- email.accepted
- email.queued
- email.sent
- email.delivered
- email.deferred
- email.bounced
- email.failed
- email.unsubscribed
- email.complaint
- campaign.started
- campaign.completed

Middleware should be able to route relevant events to Odoo/n8n without Klyrow writing directly to Odoo PostgreSQL.

## API gateway

Do not expose raw Postal or Mautic administrative APIs as the public commercial product API.

Build a Klyrow API layer in front of them.

Suggested API endpoints:

```text
POST /v1/email/send
POST /v1/email/batch
GET  /v1/email/:id
GET  /v1/email/:id/events
POST /v1/campaigns
GET  /v1/campaigns/:id
POST /v1/webhooks
GET  /v1/domains
POST /v1/domains
POST /v1/domains/:id/verify
GET  /v1/health
```

Use:
- API keys
- tenant IDs
- RBAC
- idempotency keys
- per-tenant rate limits
- audit logging
- standardized error responses

## Client dashboard

Build a usable client dashboard under `app.klyrow.com`.

Required flows:
- login
- logout
- forgot password
- reset password
- session management
- account profile
- organization/tenant selection where applicable
- API key creation/revocation
- sending-domain setup
- sender identity management
- DNS verification status
- campaigns
- contacts/lists/segments
- email templates
- message history
- delivery status
- bounce/complaint visibility
- suppression list visibility
- webhook configuration
- usage/quota view
- basic analytics

## Admin dashboard

Provide an admin role and admin UI for:
- customers/tenants
- user management
- account enable/disable
- quotas
- API keys
- sending domains
- DKIM/domain verification status
- rate limits
- message volume
- bounce rates
- complaint rates
- provider/server health
- queue health
- worker health
- webhook failures
- audit logs
- suspension/abuse controls

Bootstrap the first admin securely.

Do not hard-code a production password in Git.

## RBAC and tenant isolation

Implement at least:
- platform_admin
- tenant_admin
- tenant_user
- read_only/support role if useful

Prove tenant isolation with tests.

A tenant must never see another tenant's contacts, campaigns, messages, domains, API keys, analytics, or webhooks.

## Google integration

Prepare optional Google integration through OAuth 2.0 and supported Google APIs for legitimate connected-account functions.

Possible supported features:
- connect a Google Workspace/Gmail account for authorized mailbox workflows
- import/sync approved contacts if requested
- authorized mailbox actions where product requirements call for them

Do not design bulk delivery to bypass Gmail sending limits.

Postal remains the primary bulk/transactional delivery layer unless explicitly changed.

Document required Google OAuth credentials/scopes but do not invent credentials.

## Reverse proxy and TLS

Configure host-based routing for the Klyrow domains.

Use **free publicly trusted TLS certificates from Let's Encrypt** for every public web/API hostname that resolves to this server, including all applicable Klyrow services such as `klyrow.com`, `www.klyrow.com`, `app.klyrow.com`, `api.klyrow.com`, `track.klyrow.com`, `bounce.klyrow.com`, and any additional production hostname that is actually enabled.

Install and configure Certbot, Traefik ACME, Caddy ACME, or another maintainable ACME client appropriate to the selected reverse proxy. Do not use self-signed certificates for normal public production endpoints.

Automate certificate issuance and **automatic renewal**. Renewal must not depend on a human manually running a command.

Configure:
- ACME account/registration
- HTTP-01 or DNS-01 challenge as appropriate
- persistent certificate storage
- automatic scheduled renewal or proxy-native ACME renewal
- safe reverse-proxy reload after renewal if required
- HTTPS redirects
- secure TLS defaults
- certificate expiry monitoring
- renewal failure alerting/logging

Test certificate renewal using the ACME client's supported dry-run/staging mechanism where possible. Verify that renewal survives container and server restarts.

Do not issue certificates until DNS for the hostname resolves correctly. If DNS is not ready, continue the deployment and report the exact DNS blocker instead of generating self-signed replacements.

For SMTP/mail TLS, configure the mail services to use the appropriate publicly trusted certificate for `mail.klyrow.com` or the actual mail hostname, and ensure certificate refresh/reload is automated without interrupting mail queues unnecessarily.

**SSH is separate from HTTPS/TLS:** continue using SSH public-key authentication for server administration. Do not attempt to use Let's Encrypt certificates as a replacement for SSH keys.

Do not expose internal container ports unless required.

## Networking

Prefer private communication to middleware over:
- `10.40.0.2` shared app server
- `10.40.0.1` middleware

Do not invent a second private IP for Klyrow if it shares the application server.

Use narrow firewall rules.

Do not disable UFW/nftables globally.

## Rate limiting and abuse controls

Implement:
- per-tenant API rate limits
- per-tenant send quotas
- per-domain limits where useful
- suppression list enforcement
- unsubscribe enforcement
- bounce thresholds
- complaint thresholds
- account suspension controls
- admin alerts for abnormal spikes

Do not allow arbitrary anonymous email submission.

## Observability

Add monitoring for:
- API request rate
- mail accepted
- mail queued
- mail sent
- delivery rate
- bounce rate
- complaint rate where available
- queue depth
- worker health
- database health
- container health
- CPU/RAM/disk
- webhook failures
- TLS expiry
- certificate renewal failures

Use Prometheus/Grafana if practical, or another maintainable open-source equivalent.

## Backups

Create automated backup and restore procedures for:
- Postal database/configuration
- Mautic database/configuration
- application database
- templates/configuration
- reverse proxy config
- ACME/Let's Encrypt certificate state where appropriate
- generated DKIM/private signing material

Do not commit signing private keys to Git.

Test restore procedures where practical.

## Git workflow

Use GitHub repository:
- `appolon1908-hue/klyrow.com`

Do not work directly on `main` for substantial implementation.

Create a branch named:
- `agent/production-email-platform`

Commit logically grouped changes.

Push the branch.

Open a pull request to `main` with:
- implementation summary
- architecture
- security notes
- DNS requirements
- tests performed
- remaining blockers

Do not merge into `main` until tests pass and the branch is production-ready.

## Required docs

Create/update:
- `README.md`
- `DEPLOYMENT_REPORT.md`
- `docs/ARCHITECTURE.md`
- `docs/DNS.md`
- `docs/MIDDLEWARE_INTEGRATION.md`
- `docs/GOOGLE_INTEGRATION.md`
- `docs/DELIVERABILITY.md`
- `docs/BACKUP_RESTORE.md`
- `docs/OPERATIONS.md`
- `docs/SECURITY.md`

## Scripts

Create safe operational scripts under `/scripts`, including where appropriate:
- bootstrap
- generate-env
- deploy
- update
- start
- stop
- restart
- health
- backup
- restore
- generate-dkim
- verify-dns
- test-smtp
- test-webhook
- test-tls
- test-certificate-renewal

Scripts must fail safely and avoid printing secrets.

## Testing

Do not declare completion merely because containers start.

Test:
1. Docker Compose validates
2. all containers become healthy
3. reverse proxy works
4. publicly trusted TLS works when DNS is ready
5. automatic certificate renewal dry-run/staging test succeeds where supported
6. certificate state persists across restart/reboot
7. Mautic login works
8. Postal admin/login works where configured
9. Klyrow client login/logout works
10. admin login works
11. RBAC works
12. tenant isolation works
13. API key creation/revocation works
14. domain onboarding works
15. DNS verification logic works
16. DKIM generation works
17. authenticated API send request is accepted into a safe test/mock path
18. unauthorized API request is rejected
19. middleware webhook signature validation works
20. bad webhook signature is rejected
21. replayed webhook is rejected
22. middleware private connectivity works
23. Mautic can hand mail to Postal in a safe test environment
24. Postal queue/worker path works
25. bounce event processing works using test/simulated events
26. unsubscribe enforcement works
27. suppression enforcement works
28. restart/reboot persistence works
29. backup succeeds
30. restore procedure is validated where practical
31. internal databases/Redis are not exposed publicly
32. public service URLs route to the correct applications
33. SMTP/mail TLS uses the intended certificate and reloads safely after renewal

Do not send production bulk mail during testing.

Use test recipients/accounts only if real external delivery testing is explicitly authorized.

## Production launch checks

Before declaring launch-ready, report the state of:
- DNS A records
- MX
- SPF
- DKIM
- DMARC
- PTR/rDNS
- TLS on every enabled public hostname
- automatic certificate renewal
- certificate-expiry monitoring
- SMTP identity
- middleware connectivity
- webhooks
- app login
- admin login
- backups
- monitoring

If a DNS or hosting-provider change must be done manually, provide the exact record/value and continue all work that is not blocked.

## Working rules

Work autonomously.

Diagnose and repair normal build/deployment failures yourself.

Do not stop after each command.

Do not overwrite unrelated Kyqra/Telnexa production data on the shared server.

Back up existing config before changing shared reverse-proxy/firewall settings.

Do not expose secrets.

Do not weaken security controls simply to make a test pass.

Do not claim email delivery is production-ready until deliverability DNS and PTR/rDNS requirements are satisfied.

## Definition of done

The mission is complete when:
- production branch exists
- Dockerized Mautic is operational
- Dockerized Postal is operational
- Mautic routes mail through Postal
- Klyrow API layer is operational
- client dashboard is operational
- admin dashboard is operational
- login/logout/reset flows work
- RBAC/tenant isolation works
- domain verification flow works
- middleware integration works over the private network
- signed webhooks work
- free publicly trusted TLS is active on all enabled public Klyrow endpoints
- certificate renewal is fully automatic and tested
- SMTP/mail TLS renewal/reload is automated
- backups/restore are documented and tested
- monitoring exists
- DNS requirements are fully documented/generated
- GitHub branch is pushed
- PR to main is opened
- deployment report is complete

Proceed continuously to completion.

Only stop when blocked by a credential, provider-level DNS/PTR change, or a destructive action affecting unrelated production data.