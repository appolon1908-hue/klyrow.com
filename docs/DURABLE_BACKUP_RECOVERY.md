# Durable-result backup and restore

Issue #82 rollout acceptance after PR #97. This is not production certification.

## Backup and restore acceptance

`/readyz` and `/readiness` require both database access and a usable durable-result
keyring. Missing or invalid keys return a sanitized HTTP 503. `/healthz` remains
a separate liveness check, not release-readiness evidence. Bootstrap and verify
the key projection before introducing the encrypted writer.

The root-only `scripts/durable-keyring-backup` helper reads the exact literal
`KLYROW_DURABLE_RESULT_KEYRING_FILE` assignment from the generated root-owned `.env`;
it never evaluates shell text, uses a caller environment override, generates lost
keys, or prints key material. The host file must be regular, root-owned and private
(mode 0600 or stricter), with no symlink at the file itself. Stage directories must
be private. Duplicate assignments, relative paths, invalid keyrings and unexpected
ownership/modes stop the operation.

`scripts/backup` snapshots the complete active/previous keyring before database
dumps, checks that it has not changed after the dumps, and includes
`durable-result-keyring.json` in both `MANIFEST.sha256` and the GPG-encrypted archive.
Standard output remains only the final archive path. Existing off-host archive and
checksum receipts and tmpfs cleanup remain required. The keyring is never emitted
as a separate plaintext backup in the destination. Backup recipient/decryption
authority is separate from these durable keys.

An approved consistent-backup window must quiesce applicable writers and freeze
key rotation and rewrap across all consumers. Comparing the keyring before and
after a dump detects a persistent change, not every concurrent change-and-revert
or unrelated database mutation. This helper does not coordinate production
writers, prove a globally consistent snapshot, or authorize service changes.

`scripts/restore` requires the archive keyring and its checksum entry, then checks
that the configured live keyring contains every archived key ID with exactly the
same material before any database is overwritten. A live superset with a new active
key is accepted. Missing/replaced keys stop restore; the helper never overwrites
live keys or retires one. Recover missing keys only through the separately reviewed
secret-recovery procedure, and verify projections in all consumers before resuming
service. Archives predating the keyring entry fail this new gate and need a
separately reviewed legacy recovery procedure; no silent bypass is provided.

`scripts/restore-verify` uses the archived keyring in the isolated gateway, projected
read-only with mode 0400 for runtime UID/GID 10001. Its synthetic session and database
credentials have the same private runtime-readable ownership. The rehearsal runs
`python -m app.durable_backup` before reporting restore success. This streams and
decrypts all control-replay and integration-result records, including expired rows,
using their original tenant/operation/source bindings. On PostgreSQL the scan
requests a repeatable-read, read-only transaction and always rolls it back. It
invokes no ASGI startup, provider submission, rewrap or purge.

The scan emits counts only, separating authenticated encrypted records from legacy
plaintext. A legacy row is not authenticated evidence. Missing keys, invalid
ciphertext, broken bindings or unusable schemas stop the rehearsal with a fixed
sanitized error. Streaming bounds memory, not scan duration: size the isolated
rehearsal window for the complete retained dataset. Missing record tables fail
closed rather than reporting an empty successful scan.

Local regressions use synthetic keys, SQLite and real GPG with mocked Docker
commands. They prove guard behavior, encrypted packaging and fail-before-write
ordering, not a real PostgreSQL/MariaDB restore or production readiness. Exact-image
isolated restore, runtime UID projection checks, restore timing, rollback
compatibility, independent review and staging/canary evidence remain mandatory.
This repair does not implement legal-hold-aware physical retention or activate
email delivery.
