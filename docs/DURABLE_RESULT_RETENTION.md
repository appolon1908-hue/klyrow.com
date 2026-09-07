# Operator-controlled result payload retention

Related: #82. This source implementation does not activate a production purge,
certify a running keyring, or close the release/restore acceptance issue.

## Scope and invariants

`scripts/retain-durable-results` is a root-only, PostgreSQL-only, explicit
maintenance CLI. No HTTP route, worker, scheduler, startup hook or migration
invokes a purge. Every command defaults to dry-run and rolls its transaction
back. Apply requires `--apply --confirm RETAIN_DURABLE_RESULTS_V1`.

Only the encrypted **IntegrationResult payload** of a COMPLETED operation without
a lease, ambiguous observation or preservation hold is eligible. Its creation
must be at or before a fixed UTC-aware cutoff, and that cutoff must be at least
`KLYROW_RESULT_RETENTION_SECONDS` old (default 30 days, supported one hour through
90 days). Fresh data, pending/processing/retry/dead-letter/cancelled operations,
unknown/mismatched sources and all `MAUTIC_LATE` evidence remain untouched.
Legacy plaintext results must be explicitly rewrapped/authenticated before
purging; missing/unknown encryption keys or malformed eligible records abort
and roll back the entire batch.

The result row, tenant/source/outbox ownership, original semantic digest,
result key, original timestamp, outbox state/payload and control-idempotency
rows remain. The replacement is an AES-GCM authenticated schema-v2 tombstone
containing the original semantic digest, purge time and policy checksum, not
the result body. Identical callbacks are still duplicates; a changed payload
still conflicts, including changes to fields redacted from the visible result.
Operation readback reports `result_metadata.availability=PURGED`, not INVALID or
fabricated provider output. This intentional removal alone does not mark a
successfully completed operation for reconciliation. Ambiguous observations
still do. Expired corrupt records now report INVALID after authentication;
expiry does not bypass ciphertext checks.

This removes payload data from the live logical result record. It is **not secure
physical erasure** of PostgreSQL pages, WAL, replicas, prior backups, outbox
commands, logs or other domain records. Those have separate retention policies.
No key is retired and no deduplication row is deleted by this tool.

## Holds, ordering and change authority

An ACTIVE operation hold blocks all result-payload purges for that tenant/outbox.
Multiple independent hold IDs coexist; releasing one never releases another.
Placement is idempotent only for the same identity and approved change hash.
Release requires the exact tenant/outbox/hold and a separate approved change
hash; a released hold ID cannot be reused. The audit retains each transition
and its change hash, without free-text sensitive reasons. The fixed audit actor
`offline-retention-operator` describes the maintenance channel, not a verified
human identity; OS access/change-management evidence identifies the operator.

Existing tenant-wide `AccountClosure.retention_policy=LEGAL_HOLD` is respected
regardless of closure state. Both the closure request and offline maintenance
lock the tenant row. Operation holds and purges then lock the tenant-owned
outbox before its results, matching callback ownership. NOWAIT conflicts fail
the batch: no busy row is skipped behind the continuation cursor. Hold placement
that commits first blocks a competing purge; a hold placed after a committed
purge cannot retroactively recover removed data. Direct/manual database writes
are not a substitute for these serialized interfaces.

The CLI validates hashes, not signatures or the legal sufficiency of a hold.
Independent approval, its change record and the maintenance window remain
external prerequisites. It grants no identity or provider permissions.

## Review then apply one bounded batch

First migrate the additive hold table through the standard reviewed schema
runner, deploy compatible readers to every consumer, prove an isolated encrypted
backup restore with all necessary keys, and place all applicable holds. Neither
schema migration nor application deployment starts deletion.

Use exact values from the reviewed operator change; examples are templates:

```sh
sudo python scripts/retain-durable-results hold \
  --tenant "$TENANT" --outbox-id "$OUTBOX_ID" \
  --hold-id "$HOLD_ID" --change-sha256 "$HOLD_CHANGE_SHA256"
# Apply the same reviewed hold with --apply --confirm RETAIN_DURABLE_RESULTS_V1.

sudo python scripts/retain-durable-results purge \
  --tenant "$TENANT" --before "$FIXED_UTC_CUTOFF" --limit 100
```

Record the returned `plan_sha256`. It binds tenant, fixed cutoff, retention
setting, batch size, cursor, and the exact eligible result IDs/ciphertext
checksums. Apply the *same* scope and cursor, not the returned next cursor:

```sh
sudo python scripts/retain-durable-results purge \
  --tenant "$TENANT" --before "$FIXED_UTC_CUTOFF" --limit 100 \
  --expected-plan-sha256 "$REVIEWED_PLAN_SHA256" \
  --backup-file "$ENCRYPTED_BACKUP" --backup-sha256 "$BACKUP_SHA256" \
  --apply --confirm RETAIN_DURABLE_RESULTS_V1
```

Backup checking accepts a private, root-owned, non-symlink single-link regular
file up to 1 TiB, bounds reads to the observed size, and rejects changed metadata
or bytes. This verifies a file checksum, **not** its encryption, authenticity,
coverage or restore quality. Those must be proven separately. Preserve the
backup change evidence with the purge plan outside application logs.

Rows changed or rewrapped, changed retention settings, and new applicable holds
require a fresh dry-run plan. Transactions roll back on keyring drift, invalid
records, lock conflicts or failed audit/flush. Reports contain counters, skips,
a checksum and an opaque cursor, never payloads, credentials or keys.

Continue with the returned `next_after_id` only after the reviewed batch has
committed, with a new dry-run plan for the next batch. Size is 1-1000 rows, not an
unbounded sweep. `more_may_exist` is not a completion certificate. Held or active
rows may become eligible later; repeat from the beginning after state/hold
changes. There is no automatic retry loop. Release a hold only through the
`release-hold` subcommand and the same explicit confirmation boundary.

## Compatibility, backup and rollback

Readers, operation APIs, key rewrap and isolated backup verification in this
change understand both schema-v1 results and schema-v2 tombstones. Roll readers
out everywhere before the first purge. Previous binaries cannot authenticate
schema-v2 as a usable result and must not be rolled back after tombstones exist.
Use a forward repair retaining compatible readers. Rewrap preserves tombstones
and the original digest; it never turns them back into empty schema-v1 results.

Restoring an older backup can reintroduce removed payloads and omit newer holds.
Reconcile the protected hold/change audit and cutoff history before resuming
any maintenance or delivery after restore. Keep backup/key retention and
purge/hold evidence together. Restoring live data is a separately approved
operation; this CLI never restores or deploys anything.

## Tests and release gates

`test_durable_operation_results.py` covers plan binding, holds, redaction-aware
replay, ciphertext corruption, rollback, key rotation, backup verification,
bounded batches and tenant isolation. The existing mandatory real-PostgreSQL CI
phase also runs competing hold/purge/callback/closure transactions and NOWAIT
lock conflicts. `test_durable_retention_cli.py` covers root/confirmation/backup
and PostgreSQL guards. Full application/browser/OpenAPI, migration-twice,
dependency/secret/image scans, reproducibility and independent final-head review
remain required. No source test constitutes production retention certification.
