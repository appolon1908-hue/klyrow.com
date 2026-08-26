# Codex Feature Task — Reconciliation and Governed Self-Healing

## Branch

`feat/klyrow-reconciliation-self-healing`

## Planning baseline

`b4a8614c2dd703cf6bc021828ffd4d718002e39d`

This is an implementation scaffold, not completed code.

## Prerequisites

Use the latest reviewed baseline containing:

- `feat/klyrow-postal-provisioning`
- `feat/klyrow-integrations`
- `feat/klyrow-billing-plans-usage`
- `feat/klyrow-enterprise-admin`
- `feat/klyrow-control-plane-events`
- `feat/klyrow-odoo-backoffice-sync`

## Mandatory reading

Read the complete authoritative program and the **Cross-System Reconciliation and Governed Self-Healing** mission plus acceptance matrix before editing.

## Objective

Implement continuous drift detection and governed repair across Keycloak, Klyrow, Postal, middleware, n8n and Odoo using supported APIs/connectors only. Klyrow owns findings, repair plans, approval state and evidence.

## Required delivery

- additive migrations and rollback;
- external-state adapter contracts without direct database access;
- normalized safe snapshots and staleness handling;
- deduplicated findings with severity and stable types;
- expected-versus-observed evidence;
- repair classifications: safe automatic, owner approval, financial approval, security review and manual only;
- immutable dry-run repair plans with preconditions, compensation and expiry;
- step-up approval for financial, identity, ownership, credential, suspension, route, deletion and cross-tenant changes;
- idempotent repair execution and partial-failure handling;
- no destructive automatic repair;
- System Integrity and Customer 360 UI;
- OpenAPI, events, metrics, alerts and runbooks;
- adapter, concurrency, retry, compensation, authorization, tenant-isolation, browser, accessibility, security and secret/PII tests.

## Minimum drift coverage

Cover documented Keycloak identity/membership, Postal provisioning/credential/domain/message, middleware/n8n outbox/execution/result, Odoo partner/subscription/usage/invoice/payment/credit/support/reseller and internal Klyrow ledger/approval/privacy/attention inconsistencies.

## Integration boundaries

Read external state only through approved authenticated APIs or existing connector contracts. Deliver Odoo/n8n repair commands through Codestra middleware. Never expose arbitrary remote command execution.

## Hard restrictions

Do not deploy, merge, restart services, execute production repairs, directly access Keycloak/Postal/Odoo databases, automatically perform financial/identity/credential/deletion/suspension changes, print secrets or bypass approval/step-up checks.

## Git delivery and report

Push only this branch and open/update one draft PR. Include exact adapter, finding deduplication, stale-state, plan precondition, concurrent repair, idempotency, compensation, no-destructive-auto-repair, tenant isolation, UI, migration, rollback and no-production evidence. Stop afterward.
