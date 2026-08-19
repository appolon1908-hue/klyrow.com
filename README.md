# Klyrow Production Email Platform

Klyrow is a tenant-isolated email operations platform built around Mautic 7.1.3, Postal 3.3.7, and a public FastAPI gateway. It provides authenticated delivery submission, domain onboarding, RBAC, quotas, suppressions, webhook verification, an operator/client portal, metrics, backups, and a safe test mode.

The SaaS layer adds profiles/events, consent/preferences, nested behavioral segmentation, journey graphs and runs, deliverability snapshots, internal-event analytics, onboarding, TOTP MFA/session revocation, OpenAPI/idempotency/correlation, and safe foundations for experiments, AI providers, integrations and billing. See [SaaS P0](docs/SAAS_P0.md) and [API/webhooks](docs/API.md).

## Quick start

```bash
scripts/generate-env
scripts/deploy
scripts/health
```

The generator creates `.env` with mode 0600 and prints the one-time admin password. Store it in an approved password manager. Production submission remains disabled while `KLYROW_SAFE_MODE=true`. Do not change that setting until Postal is bootstrapped, DNS/PTR is complete, abuse handling is staffed, and the Postal server API key is stored in `.env`.

Delivery remains forced safe unless the independent `KLYROW_PRODUCTION_GATE_APPROVED=true` control is also set after every launch gate is verified.

Public traffic is terminated by the existing host Nginx. The gateway, Mautic and Grafana bind only to `127.0.0.1`; databases and RabbitMQ have no host ports. Copy `docker/proxy/klyrow.conf` only after backing up and reviewing the shared Nginx configuration.

## Components

- `app.klyrow.com`: client/admin portal; Mautic under `/mautic`; Grafana under authenticated `/ops`.
- `api.klyrow.com`: Klyrow API, never raw Mautic/Postal admin APIs.
- `track.klyrow.com`: tracking ingress routed to the controlled gateway.
- `mail.klyrow.com`: SMTP identity and MX target.
- Mautic: contacts, templates, segments and campaign orchestration through Postal.
- Postal: SMTP/API submission, DKIM, queue workers and delivery events.
- PostgreSQL: Klyrow tenant/application state; MariaDB: isolated Mautic and Postal stores.

See [deployment report](DEPLOYMENT_REPORT.md), [architecture](docs/ARCHITECTURE.md), and [operations](docs/OPERATIONS.md).

Production sending is intentionally launch-gated. See [DNS and deliverability](docs/DNS_AND_DELIVERABILITY.md), [SMTP](docs/SMTP.md), and [middleware integration](docs/MIDDLEWARE_INTEGRATION.md).
