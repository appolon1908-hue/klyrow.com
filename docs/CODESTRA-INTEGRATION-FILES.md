# Klyrow Codestra Integration Files

## Purpose

This branch prepares the files needed to connect `klyrow.com` to the Codestra platform and SMTP system without enabling production traffic.

## Files Added

- `codestra/integration/klyrow.integration.v1.json` - machine-readable integration manifest.
- `codestra/integration/middleware-command-contract.v1.json` - Middleware command and event contract for governed email automation.
- `codestra/integration/n8n-orchestration.v1.json` - `CP-KLYROW-*` workflow import contract, inactive by default.
- `codestra/integration/openbao-secret-aliases.v1.json` - secret alias manifest without secret values.
- `codestra/integration/runtime.env.example` - non-secret runtime environment template.
- `monitoring/klyrow-metrics-contract.v1.json` - bounded metrics contract for Prometheus and Grafana.
- `monitoring/prometheus-target.disabled.yml` - disabled Prometheus scrape target example.
- `monitoring/klyrow-recording-rules.yml` - email-specific recording rules for Grafana.
- `scripts/validate-codestra-integration.py` - fail-closed validation.
- `.github/workflows/validate-codestra-integration.yml` - CI for the integration files.

## Intended Integration Path

```text
Product / website / CRM event
  -> Caddy
  -> Kong
  -> Middleware
  -> n8n orchestration when coordination is required
  -> Middleware
  -> Klyrow gateway
  -> Postal private SMTP relay
  -> email destination
```

Status events return through the same authority path:

```text
Postal / Klyrow delivery event
  -> Middleware
  -> n8n orchestration when coordination is required
  -> Middleware
  -> Odoo or other approved destination state
```

## Boundaries

- n8n may claim jobs and coordinate commands only through Middleware automation endpoints.
- n8n must not call Klyrow private APIs, Postal, SMTP, Odoo, PostgreSQL, Redis or OpenBao directly.
- Browser code never receives Keycloak confidential-client secrets, Middleware credentials, SMTP passwords, Postal API keys or provider tokens.
- SMTP credentials are tenant scoped, stored as hashes, returned once and controlled by Klyrow policy.
- Public SMTP delivery, marketing delivery and SECURITY SMTP live delivery remain disabled until the production gates pass.
- Metrics are disabled until Prometheus target approval.
- Metrics must use bounded infrastructure and service labels only; tenant, user, recipient, sender, message and SMTP credential identifiers are forbidden.

## Prepared Workflow Lane

The prepared n8n lane is `CP-KLYROW-*`:

- `CP-KLYROW-COMMON-ERROR`
- `CP-KLYROW-EMAIL-SEND`
- `CP-KLYROW-DELIVERY-STATUS-SYNC`
- `CP-KLYROW-SMTP-CREDENTIAL-LIFECYCLE`
- `CP-KLYROW-DOMAIN-DELIVERABILITY`
- `CP-KLYROW-DLQ-REPLAY`

All workflow exports must remain inactive by default, hash-versioned in Git and free of credential material. Runtime credentials belong in n8n's credential store, backed by OpenBao aliases where applicable. SMTP credentials are tenant scoped.

## Activation Gates

Before production activation:

1. Prove Keycloak and Kong route/scope matrix for `klyrow-backend`.
2. Prove Middleware canary calls with valid, invalid, no-token and wrong-scope cases.
3. Import inactive `CP-KLYROW-*` workflows into staging n8n.
4. Run `CP-KLYROW-EMAIL-SEND` against staging Middleware with live delivery disabled.
5. Confirm no unexpected DLQ, replay conflict or idempotency drift.
6. Verify SPF, DKIM, DMARC, PTR, SMTP TLS, STARTTLS, bounce and complaint handling.
7. Approve private Prometheus target inventory and Alertmanager routing.
8. Enable live delivery only through an immutable release manifest and rollback runbook.
