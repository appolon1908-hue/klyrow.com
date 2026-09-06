# Klyrow repository memory

This file is a stable orientation map for maintainers and coding agents. It is
not deployment evidence, a substitute for current Git inspection, or authority
to enable email delivery.

For the dated API review and current Git snapshot, see
[`docs/audits/API_AUDIT_2026-08-27.md`](docs/audits/API_AUDIT_2026-08-27.md).
For the September 6 issue reconciliation and remaining release prerequisites,
see [`docs/audits/ISSUE_RECONCILIATION_2026-09-06.md`](docs/audits/ISSUE_RECONCILIATION_2026-09-06.md).

## Repository purpose

Klyrow is the tenant-isolated email control plane around a FastAPI gateway,
Postal, Mautic, PostgreSQL, MariaDB, SMTP relay/worker processes, and private
Codestra Middleware integrations.

The intended identity-security path is:

```text
Codestra Keycloak
  -> authenticated STARTTLS
  -> dedicated Klyrow SECURITY SMTP credential
  -> Klyrow governed SMTP relay
  -> SECURITY delivery worker
  -> Postal
  -> recipient inbox
```

Middleware, Odoo, n8n, Mautic, analytics, and application APIs must never
receive a password, reset token, complete reset URL, SMTP password, access token,
or refresh token.

## API implementation map

The production FastAPI composition root is:

```text
apps/gateway/app/platform.py
```

It owns or mounts the following implementation areas:

```text
apps/gateway/app/main.py
  health/readiness/version/metrics
  legacy/local authentication
  API keys
  basic domains
  message and email submission
  Postal lifecycle webhooks
  contacts and campaigns
  suppressions, audit, usage
  tenant administration
  Middleware event delivery helper
  generic Postal outbox workers

apps/gateway/app/saas.py
  profiles and timelines
  customer events
  consent and preferences
  segments
  journeys and runs
  onboarding
  MFA and sessions
  deliverability snapshots
  experiments
  integrations
  plans/subscriptions/usage
  developer OpenAPI and AI/rendering foundations

apps/gateway/app/provider.py
  provider-domain and sender registry
  tenant mail policy
  SMTP credentials and preflight
  DKIM rotation/verification
  provider messages/events/usage
  provider inbound processing
  provider worker/reconciliation

apps/gateway/app/messaging.py
  inbound routes and messages
  webhook endpoints and delivery attempts
  messaging support contracts

apps/gateway/app/billing.py
  invoices, payments, refunds, ledger/reconciliation

apps/gateway/app/tenancy.py
  OIDC identity links
  tenant memberships and roles
  invitations and tenant lifecycle

apps/gateway/app/agent_mailboxes.py
  campaign/agent mailbox authorization and sender policy

apps/gateway/app/delivery_controls.py
  domain/sender/stream delivery controls

apps/gateway/app/operations.py
  operational gates, queues, and integration operations

apps/gateway/app/preferences.py
  suppression and preference enforcement

apps/gateway/app/reseller.py
  reseller-oriented API contracts

apps/gateway/app/smtp_relay.py
  authenticated STARTTLS SMTP acceptance and durable queueing

apps/gateway/app/security_payload.py
  encrypted-at-rest SECURITY MIME envelope handling

apps/gateway/app/security_smtp_worker.py
  dedicated SECURITY submission to Postal and sensitive-payload purge

apps/gateway/app/service_worker.py
  background worker selection and delivery-mode wiring
```

Browser BFF, onboarding UI, invitation selection, tenant Postal provisioning,
and browser security corrections are now on the default branch. `platform.py`
composes them with the core `main.py` application and installs the current
runtime authority extensions. Inspect the actual composed routes before
changing captured helpers or adding a duplicate route.

## Test entry points

The root `pytest.ini` sets `pythonpath = .` and `testpaths = tests`.

The default CI entry point is:

```text
.github/workflows/ci.yml
```

The principal commands are:

```bash
python scripts/migrate
python scripts/migrate
python -m compileall -q apps/gateway
PYTHONPATH=. pytest -q tests
pip-audit --requirement apps/gateway/requirements.txt
```

CI also runs frontend lint/type/unit/build/Playwright checks, Gitleaks, and
gateway, SMTP, web, and PostgreSQL image builds and Trivy scans. Image checks
include SBOM and reproducibility evidence. PostgreSQL migration-twice and
concurrent command replay run in CI. Owned Middleware adapters are tested
against an immutable Middleware contract checkout. Source publication and
deployment readiness use the separately pinned shared infrastructure workflow.

Important focused test modules include:

```text
tests/test_api.py
tests/test_saas.py
tests/test_provider.py
tests/test_messaging.py
tests/test_billing.py
tests/test_tenancy.py
tests/test_agent_mailboxes.py
tests/test_delivery_controls.py
tests/test_event_mtls.py
tests/test_security_smtp_policy.py
tests/test_security_smtp_worker.py
tests/production_safe_smoke.py
```

Use the complete suite after every slice. Run focused modules first only to
shorten the feedback loop; they do not replace the full suite.

## Required safety rules

```text
KLYROW_SAFE_MODE=true until an approved activation window
LIVE_EMAIL_DELIVERY=false by default
EXTERNAL_EMAIL_DELIVERY=false by default
PRODUCTION_PROVIDER_ROUTING=false by default
KLYROW_SECURITY_SMTP_ENABLED=false by default
KLYROW_SECURITY_SMTP_LIVE_ENABLED=false by default
KLYROW_SECURITY_SMTP_PRODUCTION_APPROVED=false by default
```

Other binding rules:

1. Keycloak is the only human password and password-recovery authority in
   production.
2. Codestra Middleware is the only cross-system write boundary.
3. Every mutating API must be tenant-scoped, authorized, idempotent where
   retried, and auditable.
4. Postal API acceptance is not equivalent to recipient delivery.
5. SECURITY MIME must remain encrypted while queued and must be purged after
   provider submission, terminal failure, or retention expiry.
6. No browser token may be stored in localStorage or sessionStorage.
7. No feature branch or local test result is production authority.
8. Deploy the gateway and browser application atomically when the BFF release is
   introduced.

## Before changing code

Record the exact state first:

```bash
git status --short --branch
git rev-parse HEAD
git remote -v
git log --oneline --decorate -10
```

Then identify the owning module, nearest focused tests, cross-repository
contract, capability gate, migration impact, and rollback behavior.

Do not use “fix all” as a branch scope. Use dependency-ordered slices and keep
live delivery disabled while source correctness is being repaired.
