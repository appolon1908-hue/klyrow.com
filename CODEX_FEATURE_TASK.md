# Codex Feature Task — Decision and Policy Ledger

## Branch

`feat/klyrow-decision-policy-ledger`

## Planning baseline

`b4a8614c2dd703cf6bc021828ffd4d718002e39d`

This branch is an implementation scaffold, not completed code.

## Prerequisites

Do not implement until the latest reviewed versions of these prerequisites are available:

- `feat/klyrow-auth-bff-sessions`
- `feat/klyrow-tenancy-onboarding`
- `feat/klyrow-consent-preferences`
- `feat/klyrow-billing-plans-usage`
- `feat/klyrow-stream-separation`
- `feat/klyrow-control-plane-events`

Before editing, recreate or update this branch from the reviewed prerequisite baseline without rewriting unrelated history.

## Mandatory reading

Read completely:

1. `KLYROW_CODEX_EXECUTION_INDEX.md`
2. `KLYROW_MODERN_SAAS_PROGRAM.md`
3. `docs/implementation/KLYROW_FEATURE_MISSIONS.md`
4. `KLYROW_IDENTITY_AUTOMATION_ODOO_CONTROL_PLANE.md`
5. `KLYROW_DIFFERENTIATED_FEATURES_PROGRAM.md`
6. Mission **Communication Decision and Policy Ledger** in `docs/implementation/KLYROW_DIFFERENTIATED_FEATURE_MISSIONS.md`
7. `docs/implementation/KLYROW_DIFFERENTIATED_ACCEPTANCE_MATRIX.md`

## Objective

Implement the authoritative communication-intent, pre-send policy, approval, explanation and signed message-passport layer using the existing Klyrow architecture. Do not rebuild Keycloak, Postal, middleware, n8n, Odoo, billing, consent or the existing gateway.

Every release-scoped API, SMTP, campaign, journey, AI and administrative send path must be unable to enqueue provider work without an authoritative current Klyrow decision once enforcement is enabled.

## Required delivery

- domain modules, not further unrelated monolith expansion;
- additive PostgreSQL migration and rollback plan;
- communication intents;
- immutable policy versions;
- fail-closed evaluation and stable reason codes;
- consent/suppression/stream/sender/domain/entitlement/quota/billing/attention/risk/approval hooks;
- revalidation immediately before provider enqueue;
- immutable evidence and causal timeline;
- approval inbox with permission and step-up controls;
- signed privacy-safe message passports;
- tenant policy center and decision explorer;
- OpenAPI and domain events;
- metrics, alerts and runbooks;
- observe-only migration mode and explicit enforcement flag;
- unit, PostgreSQL, authorization, concurrency, worker, integration, browser, accessibility, security and secret-scan evidence.

## Integration boundaries

- Keycloak remains identity authority.
- Klyrow remains decision, usage and entitlement authority.
- Postal receives only approved provider work and correlation IDs.
- Feature code publishes through the shared control-plane event service.
- Odoo and n8n are reached only through Codestra middleware.
- n8n cannot approve or mutate a decision directly.
- No secrets or full message bodies in events, passports or logs.

## Hard restrictions

Do not deploy, merge, restart services, change DNS/TLS, rotate credentials, activate enforcement in production, modify Postal source, write directly to Keycloak/Postal/Odoo databases, enable live provider failover, enable real billing or bypass a failing policy/security test.

## Git delivery

Create logical commits, push this branch only, and open/update one independently reviewable draft PR. Do not start the next branch.

## Completion report

Provide every item required by the differentiated mission document, including host, directory, starting/final SHA, commits, files, requirement audit, migrations, rollback, exact tests/builds, decision-path coverage, bypass evidence, tenant isolation, message-passport verification, OpenAPI, events, metrics, blockers and all no-deployment/no-secret confirmations.
