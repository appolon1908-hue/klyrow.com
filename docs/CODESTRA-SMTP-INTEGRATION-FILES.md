# Codestra SMTP Integration Files

## Purpose

This branch prepares `klyrow.com` as the governed SMTP/email provider for the Codestra communications platform without enabling production delivery, public SMTP submission, metrics scraping or live provider writes.

## Files Added

- `codestra/integration/klyrow-smtp.integration.v1.json` - machine-readable integration manifest.
- `codestra/integration/smtp-provider-contract.v1.json` - SMTP provider command, webhook and reconciliation contract.
- `codestra/integration/openbao-secret-aliases.v1.json` - secret alias manifest without secret values.
- `codestra/integration/runtime.env.example` - disabled-by-default runtime template.
- `monitoring/klyrow-smtp-metrics-contract.v1.json` - bounded metrics contract for Prometheus and Grafana.
- `monitoring/prometheus-target.disabled.yml` - disabled private scrape target example.
- `docs/CODESTRA-SMTP-INTEGRATION-FILES.md` - operator handoff.
- `scripts/validate-codestra-smtp-integration.mjs` - fail-closed validation.
- `.github/workflows/validate-codestra-smtp-integration.yml` - CI for the integration files.

## Intended Integration Path

```text
Product backend or Codestra SDK
  -> Caddy
  -> Kong OIDC and scope enforcement
  -> Middleware command ledger
  -> Klyrow private gateway
  -> Postal private relay
  -> Postal signed webhook
  -> Klyrow provider event ledger
  -> Middleware signed event ingress
```

## Boundaries

- Browser code must not receive SMTP, Postal, Middleware, OpenBao or Keycloak confidential-client secrets.
- n8n and Odoo must not send SMTP directly or call Postal provider APIs.
- Governed email writes must go through Middleware command APIs.
- SMTP credentials are tenant/domain/sender/stream scoped and are not employee passwords.
- Public SMTP stays disabled until DNS, PTR, STARTTLS, certificate, bounce, complaint and abuse-monitoring gates pass.
- Metrics stay disabled until the private Prometheus target is approved.
- Indeterminate provider outcomes must reconcile from the message ledger, provider event ledger and Middleware operation read-back before any resend.

## Activation Gates

Before production activation:

1. Merge the canonical Communications API v1 SDK contracts.
2. Prove Keycloak and Kong route/scope matrix for `klyrow-email`.
3. Prove Middleware canary calls with valid, invalid, no-token and wrong-scope cases.
4. Prove Klyrow safe-mode canary returns an idempotent operation without Postal delivery.
5. Prove Postal canary only after DNS, PTR, SPF, DKIM, DMARC, STARTTLS and bounce handling are green.
6. Approve OpenBao secret aliases and install runtime secret files outside Git.
7. Approve the private Prometheus target inventory and Alertmanager route.
8. Confirm no direct SMTP, Postal, Odoo or public n8n provider-write path remains.
