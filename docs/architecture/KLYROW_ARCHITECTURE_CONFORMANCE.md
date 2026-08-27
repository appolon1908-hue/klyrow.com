# Klyrow Architecture Conformance

This repository follows the Codestra platform architecture authority supplied
for the Klyrow repair and branch cleanup.

## Runtime boundaries

- Klyrow is the email product/control plane. It owns tenant isolation, domain
  onboarding, sender authorization, templates, campaigns, consent,
  suppressions, usage, billing, portal sessions, and the Postal/Mautic
  lifecycle boundary.
- Postal and Mautic are internal Klyrow provider engines. They do not write to
  Odoo and are not exposed as Klyrow's commercial API.
- Codestra Middleware is the only cross-system write boundary. Klyrow publishes
  signed lifecycle events to Middleware and accepts authenticated, idempotent
  commands through controlled APIs.
- n8n may orchestrate Middleware-validated events but does not authorize sends,
  mutate Klyrow/PostgreSQL directly, or become the durable event ledger.
- PostgreSQL is authoritative for Klyrow's durable records. Redis and
  provider-local RabbitMQ do not replace audit, inbox/outbox, idempotency, or
  reconciliation state.
- Human authentication uses the canonical Keycloak issuer, Authorization Code
  and PKCE S256. Browsers receive an opaque host-only session rather than
  access or refresh tokens.
- Public host routing, TLS, Kong policy, DNS, Keycloak desired state, and
  production activation remain outside this feature branch.

## Provider callback authority

Tenant-scoped Postal delivery must also have tenant-scoped lifecycle
attribution. The production gateway resolves a signed Postal callback against
durable local `EmailOutbox`, `Message`, or `ProviderMessage` records. In tenant
provisioning mode, an unresolved callback is rejected and cannot fall back to
the legacy global tenant setting. The legacy global tenant is accepted only
while tenant provisioning is disabled.

## Branch and release rules

- Work stays isolated in short-lived branches and pull requests.
- Branch names are not runtime integration mechanisms.
- Superseded branches are closed or deleted only after their commits are
  reachable from a protected merged branch or an intentional archive tag.
- The same immutable image digest must move from staging to production.
- Staging and initial production deployment keep live and external email
  delivery disabled.
- Production activation requires exact-head CI, independent review, protected
  merge, runtime read-back, backup/restore, rollback rehearsal, and explicit
  approval.

## Current integration stack

```text
main
  <- feat/klyrow-postal-provisioning
       <- fix/klyrow-auth-security-stabilization
```

The stabilization branch is limited to browser/session authority, invitation
correctness, backwards-compatible Postal worker selection, tenant-safe Postal
callback attribution, read-only runtime-domain evidence, tests, and branch/PR
cleanup. Dedicated SECURITY SMTP, Odoo, n8n, Kong, Caddy, and live deployment
work remain isolated.
