# Klyrow Architecture Conformance

This repository follows the Codestra platform architecture authority supplied for the Klyrow repair and branch cleanup.

## Runtime boundaries

- Klyrow is the email product/control plane and owns tenant isolation, domain onboarding, sender authorization, templates, campaigns, consent, suppression, billing/usage, portal sessions, and the Postal/Mautic lifecycle boundary.
- Postal and Mautic are internal Klyrow provider engines. They do not write to Odoo and are not exposed as the commercial API.
- Codestra Middleware is the only cross-system write boundary. Klyrow emits signed lifecycle events to Middleware and accepts authenticated, idempotent commands through its controlled API.
- n8n may orchestrate validated events but does not authorize sends, mutate Klyrow/PostgreSQL directly, or become the durable event ledger.
- PostgreSQL is authoritative for Klyrow durable records. Redis and provider-local RabbitMQ are not substitutes for audit, inbox/outbox, idempotency, or reconciliation state.
- Human authentication uses the canonical Keycloak issuer with Authorization Code and PKCE S256. The browser receives an opaque host-only session rather than access or refresh tokens.
- Public host routing and TLS remain edge responsibilities. This repository does not make live Caddy, Kong, DNS, TLS, Keycloak, Postal, or server changes.

## Branch and release rules

- Work remains isolated in short-lived branches and pull requests.
- A branch name is not a runtime integration mechanism.
- Superseded branches are closed or deleted only after their commits are proven reachable from a protected merged branch or an intentional archive tag.
- The same immutable image digest must move from staging to production.
- Deployment starts with live and external email delivery disabled.
- Production activation requires exact-head CI, independent review, protected merge, runtime read-back, backup/restore, rollback rehearsal, and explicit approval.

## Current stack

```text
main
  <- feat/klyrow-postal-provisioning          # consolidated application PR
       <- fix/klyrow-auth-security-stabilization
```

The stabilization branch is limited to browser-session authority, backwards-compatible Postal worker selection, read-only runtime-domain inventory, tests, and branch/PR cleanup. Dedicated SECURITY SMTP work remains isolated rather than being bundled into this branch.
