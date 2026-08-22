# Klyrow failure recovery certification

Date: 2026-08-22

## Scope

This certification covers software-controlled recovery behavior for Postal/provider delivery, n8n automation, Odoo synchronization, and Klyrow billing. All tests used isolated databases or the internal SMTP sink. Internet delivery remained disabled.

## Postal/provider outage

- Provider messages use durable states, worker leases, bounded retry/backoff, and dead letter.
- Expired worker leases recover to `DEFERRED`, or `DEAD_LETTER` at the attempt ceiling.
- Middleware event and usage outboxes retain records while Server A is unavailable.
- After recovery, the same event and usage rows transition to `DELIVERED`.
- Provider usage rows remain unique by message; retry does not create a second billable event.
- Audited operator retry is restricted to the platform administrator.

Result: `POSTAL_OUTAGE_RECOVERY=PASS`.

## n8n and Odoo outage

- n8n and Odoo integrations use `integration_outbox`, not direct database writes.
- Delivery failure increments attempts, records a bounded error, and transitions to `RETRY` or `DEAD_LETTER`.
- Payload and idempotency key remain durable while the downstream is unavailable.
- Recovery is an explicit audited platform-admin operation and returns the item to `PENDING`.
- Tenant administrators cannot invoke failure/recovery operations.

Results:

- `N8N_OUTAGE_ISOLATION=PASS`
- `ODOO_OUTAGE_ISOLATION=PASS`

## Billing-worker failure

- Usage ingestion is immutable and idempotent by tenant and event key.
- Altering an existing usage event under the same key is denied.
- Invoice creation now accepts an `Idempotency-Key` and stores a tenant-scoped request key.
- Repeating the worker request returns the original invoice with `duplicate=true`.
- A database uniqueness constraint prevents duplicate invoices under concurrency.
- Replay creates no duplicate invoice lines.
- No raw payment-card data is accepted or stored.

Result: `BILLING_FAILURE_RECOVERY=PASS`.

## Verification

- Focused operations tests: 5 passed.
- Focused billing tests: 6 passed.
- Full suite: 83 passed, 0 failed.
- Fresh PostgreSQL 17.6 migration run: 15/15 migrations applied.
- Second migration run: no changes and no errors.
- `klyrow_invoices.request_key`: present.
- Partial unique index `uq_klyrow_invoice_request_key`: present.
- Isolated PostgreSQL instance: removed after verification.
- Customer email sent: 0.
- SMS sent: 0.
- Telnexa billing/SMS configuration changed: no.

## Result

`EMAIL_FAILURE_RECOVERY=PASS`

`FINAL_STATUS=PASS`
