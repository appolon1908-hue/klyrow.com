# Customer event ingestion

`POST /v1/events` accepts an optional `Idempotency-Key` header or the legacy
`idempotency_key` JSON field. If both are supplied, they must match. Keys are
scoped to tenant and source. Retries return the original event ID; changed
semantic payloads return 409. The request hash includes profile, name, source,
properties and the optional occurrence timestamp. Equivalent UTC instants
compare equally; supplying or removing a timestamp changes the request.

`POST /v1/events/batch` returns 207 with independent accepted/rejected results.
Explicit item keys take precedence. For items without a key, an optional batch
header derives a key from the header plus item position. Preserve item order and
source when retrying. This is item-level replay protection, not an atomic batch
response cache: previously rejected items may succeed when retried. Without any
key, ingestion is intentionally non-idempotent for compatibility.

Concurrent inserts use an isolated savepoint and re-read the committed winner
before applying journey effects. PostgreSQL concurrency tests exercise identical
and conflicting requests with separate transactions. CI runs these tests against
its disposable PostgreSQL service.

Apply the additive migration before upgrading writers. The database default for
`received_at` supports parent-version inserts during rollout and rollback. Keep
new columns and the unique index during rollback; older writers omit event keys
and therefore cannot provide the new replay contract. No production migration
or delivery activation is implied by merging this source.
