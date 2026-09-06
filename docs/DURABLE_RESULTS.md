# Durable operation results and replay authority

Issue #82: dedicated result/replay encryption, attempt fencing, and bounded readback.
This change does not enable delivery or certify any running environment.

## Source contract

All new `Idempotency.response_json` writers use a dedicated AES-256-GCM keyring,
not the browser-session secret. IntegrationResult writers encrypt a versioned,
field-redacted result and a digest of the original semantic payload. A changed
payload still conflicts even when only a redacted field changes. Ciphertext is
bound to category, tenant, operation/resource, source, request hash and storage
identity as appropriate. Each write uses a new random nonce. Unknown key IDs,
invalid envelopes and authentication failures return a sanitized unavailable
error; they never turn a replay into a new provider submission.

The keyring schema is `schema_version: 1`, `active_key_id`, and a `keys` mapping
of stable IDs to base64-encoded 32-byte keys. At most eight IDs are accepted.
Duplicate fields, malformed key material, symlinks, non-regular files, relative
paths and group/world-writable files are rejected. Docker's read-only secret
projection is supported; the host copy is root-owned mode 0600. Key material,
file paths and key IDs are not exposed by `/dependencies`; it reports only
`durable_result_keys: configured|unavailable`.

`migrate-runtime-secrets` creates the keyring atomically exactly once and preserves
an existing approved file reference. It will not replace damaged authority or
use a browser secret as a substitute. It needs to be run through the existing
approved host-change process before deploying this candidate. Compose adds the
read-only secret only to gateway, scheduler and billing-api, the consumers of
these persistence paths. No generated secret is committed.

## Legacy compatibility and rotation

Existing plaintext JSON rows remain readable while
`KLYROW_DURABLE_RESULT_LEGACY_READ_ENABLED=true` (the rollout default). This is an
explicit transitional compatibility boundary, not authenticated legacy data.
New writes never use plaintext. The bounded `scripts/rewrap-durable-results`
tool handles both control rows and integration results, preserving original
semantic digests through repeated rotations. It does not submit work or delete
records. Backups must retain the complete keyring and encrypted data together.

Stage a reviewed keyring containing the new active key and every still-needed
previous key across all consumers. Retain the same stable ID for unchanged key
material. For each exact tenant and each table, run a dry-run batch with
`--tenant`, `--table control|integration`, `--expected-key-id`, optional
`--after-id` and `--limit` (1–1000). Apply additionally requires `--apply`,
`--confirm REWRAP_DURABLE_RESULTS_V1`, `--backup-file`, and `--backup-sha256`.
The CLI checks the backup file's checksum; it does **not** certify backup
cryptography or successful restore. The operator must first prove an isolated
restore using the separately approved encrypted-backup procedure.

The whole batch rolls back on a corrupt record, unavailable key, conflicting row
lock or changing keyring. Counters and an opaque continuation ID are returned;
no payloads, database URLs or key values are printed. The cursor is not a global
completion certificate: during mixed-version rolling deployments, repeat full
scans from the beginning after all writers use the new key. Verify every tenant
and both tables before disabling legacy reads. Retire an old key only after
all rows and every retained restorable backup no longer depend on it.

Rollback must retain this compatible reader and all required keys once encrypted
rows exist. Do not roll back to an old binary that blindly JSON-decodes ciphertext,
and do not restore plaintext browser/session secrets to recover durable results.
No key rotation, rewrap, database migration, purge or deployment runs on startup.

## Result readback and retention

Integration results are JSON objects bounded to 64 KiB, depth 12 and 1000 items
per list. Field-name redaction removes recognized secret/credential/token,
message-body, URL, recipient and personal-contact fields recursively; it is not
a general detector of arbitrary secrets hidden in free-form strings. Producers
must use their governed schema and never send credential-bearing free text.
Encryption is additional protection, not permission to transport secrets.

Readback is tenant + outbox + expected-source scoped. Metadata distinguishes
AVAILABLE, UNAVAILABLE, INVALID and EXPIRED. Default result access retention is
30 days, configurable from one hour to 90 days with
`KLYROW_RESULT_RETENTION_SECONDS`. This controls **read visibility**, not physical
deletion; legal-hold-aware storage purge remains a separate operator-controlled
retention process. Completed operations without usable results explicitly require
reconciliation. Correlation is taken from the durable envelope, never fabricated
from the idempotency/storage digest.

## Worker races and ambiguous outcomes

Only the current PROCESSING attempt with an unexpired lease can commit completion
or failure. Locks refresh ORM state. Delayed failures cannot alter a newer claim,
a cancellation or its circuit state. A delayed completion preserves current
state and stores a separate encrypted `MAUTIC_LATE` observation, reported as
RECONCILIATION_REQUIRED, not as a fabricated success. Late observations prevent
claiming/requeueing another attempt. Already-in-flight effects cannot be undone
by this guard; evidence and explicit provider readback are required.

Expired/ambiguous Mautic operations cannot be blindly requeued through the
reconcile endpoint. Cancellation after PROCESSING remains rejected. Safe transport
failures can retain the existing bounded retry policy. No automatic destructive,
financial, credential or identity repair is introduced.

## Verification

`test_durable_operation_results.py` covers browser-key independence, key rotation,
context/tamper rejection, result limits/redaction/retention, encrypted duplicate
replay, stale attempts, late completion, cancellation and tenant-bounded rewrap.
`test_mautic_secret_bootstrap.py` tests atomic file bootstrap and existing-authority
preservation using only isolated synthetic files. Required PostgreSQL contract CI
also runs the row-lock/cancel/claim test. Full repository, OpenAPI, browser, image,
security, signature, backup/restore and independent final-head review gates remain
required; source tests do not certify runtime bindings or delivery.
