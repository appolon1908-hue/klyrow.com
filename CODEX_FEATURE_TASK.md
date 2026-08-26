# Codex Feature Task — Provider Mesh and Configuration Portability

## Branch

`feat/klyrow-provider-mesh-portability`

## Planning baseline

`b4a8614c2dd703cf6bc021828ffd4d718002e39d`

This is an implementation scaffold, not completed code.

## Prerequisites

Use the latest reviewed baseline containing:

- `feat/klyrow-postal-provisioning`
- `feat/klyrow-deliverability`
- `feat/klyrow-developer-platform`
- `feat/klyrow-stream-separation`
- `feat/klyrow-decision-policy-ledger`
- `feat/klyrow-control-plane-events`

## Mandatory reading

Read all authoritative program files and the **Provider Mesh and Configuration Portability** mission and acceptance matrix completely.

## Objective

Keep Postal 3.3.7 as the primary engine while introducing a stable provider contract, health-aware routing, duplicate-safe ambiguous-outcome reconciliation, controlled failover foundations and signed configuration export/import. Extend the current provider adapter; do not replace Postal.

## Required delivery

- additive migrations and rollback;
- provider capability/account/secret-reference contracts;
- fully tested Postal 3.3.7 adapter;
- disabled-by-default future adapter interfaces/test doubles;
- immutable route versions and deterministic dry-run selection;
- provider health and circuit state;
- canonical Klyrow message ID across attempts;
- `OUTCOME_AMBIGUOUS` handling and status reconciliation;
- no blind failover after timeout;
- verified sender/domain requirement on every fallback;
- message-attempt and approval UI;
- signed export/import packages excluding secrets;
- validate, plan, apply and rollback APIs/CLI;
- OpenAPI, events, metrics, alerts and runbooks;
- provider, concurrency, ambiguity, callback race, tenant isolation, export security, signature, idempotency, browser and accessibility tests.

## Safety rules

Policy, consent, suppression, account suspension, sender/domain, quota, billing, attention and risk decisions apply identically across providers. Provider routing cannot be used for abuse, reputation or policy evasion.

## Integration boundaries

Provider credentials are approved secret references. Events use the shared control plane. Configuration packages never contain credentials, private keys or unrestricted provider data. Commands use Klyrow APIs, not direct databases.

## Hard restrictions

Do not deploy, merge, enable live multi-provider routing or failover, restart Postal, modify Postal source, commit provider credentials, change DNS/TLS, send live traffic, access external databases directly or bypass ambiguous-outcome reconciliation.

## Git delivery and report

Push only this branch and open/update one draft PR. Include exact Postal regression, routing determinism, timeout-before/after-submit, duplicate prevention, callback/status race, circuit, secret-reference, export/import, signature, rollback, tenant-isolation and no-live-routing evidence. Stop afterward.
