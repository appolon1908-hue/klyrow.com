# Customer data lifecycle API

The profile and event APIs are tenant-scoped and require the canonical
`contact.manage` capability. `GET /v1/profiles` is cursor-paged and orders by
`created_at DESC, id DESC` for stable traversal. Identity matches are resolved
under a tenant row lock; when multiple profiles match, the oldest profile is
the deterministic survivor and each moved profile is recorded in
`profile_merge_audits`.

## Import and export jobs

`POST /v1/profile-imports` accepts a checksum and an opaque `s3://` or `b2://`
object reference. The API records a `PENDING` job and never stores CSV content,
credentials, or arbitrary URLs. A repeated object/checksum or idempotency key
returns the existing job; a changed payload returns `409`.

`POST /v1/profile-exports` records a `PENDING` CSV export with an allow-listed
field/filter set and expiry. A worker may later materialize the object and
update the job; the API does not fetch objects or call Odoo/n8n directly.

## Retention and deletion scheduling

`GET/PUT /v1/customer-data/retention` stores tenant policy (30–3650 days).
`POST /v1/customer-data/deletions` schedules a future profile deletion and
`POST /v1/customer-data/deletions/{id}/cancel` cancels it. Scheduling is
audited, tenant-scoped, and idempotent for an already scheduled profile. No
automatic destructive execution is enabled by this API; an independently
authorized retention worker must perform a reviewed plan and preserve legal
holds.

The additive migration is `migrations/2026091001_customer_data_lifecycle.sql`.
Rollback is fail-closed: stop lifecycle workers, reconcile queued jobs, retain
audit evidence, then remove the tables only after the retention window.
