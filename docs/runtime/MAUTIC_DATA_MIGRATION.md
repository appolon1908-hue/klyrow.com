# Offline Mautic persistent-data migration and restore

Related: #84. This is a data-only preparatory tool, not a Mautic image release,
Docker-volume replacement, database migration, or permission to enable delivery.
It deliberately does not replace the current Compose or image authority.

## Scope and historical reconciliation

The historical `scripts/migrate-mautic-volumes` blob
`095ed2c84884d7af404fcb412ad550d160ae7a65` from stale PR #72 was reviewed, not
copied wholesale. Its persistent-data allowlist and encrypted-checkpoint intent
are retained. This implementation adds dry-run defaults, a required read-only
source mount, strict file/metadata checks, bounded data sizes, source-change
checks, exclusive checkpoint creation, atomic no-replace directory publication,
idempotent verification, and a separately executable encrypted restore.

Only these trees are copied from an offline legacy `/var/www/html` mount:

| Source subtree | New bundle subtree | Eventual container mount target |
| --- | --- | --- |
| `config` | `config` | `/var/www/html/config` |
| `var/logs` | `logs` | `/var/www/html/var/logs` |
| `docroot/media/files` | `media-files` | `/var/www/html/docroot/media/files` |
| `docroot/media/images` | `media-images` | `/var/www/html/docroot/media/images` |

Application code, vendor dependencies, executables, and generated caches outside
these trees are not copied. Missing directories, symlinks (including ancestors),
hard-linked files, devices, sockets, FIFOs, special modes, extended attributes/
ACLs, and nested mounts are rejected rather than silently normalized. Owners,
groups, ordinary modes, nanosecond modification times, and file bytes are preserved.
This is deliberately conservative; unsupported data needs a separately reviewed
migration, not a bypass flag. Limits are 100,000 entries, 100 GiB file data, and
a 32 MiB manifest. Free-space estimates include file/metadata headroom and both
checkpoint and copied data when they share a filesystem. Sparse files may expand.

## Preconditions

Use Linux with Python 3.11+ and `/usr/bin/gpg`. The CLI requires root. Destination
and backup parent directories must already exist, belong to root, and have no
group/other permissions (normally 0700). Do not use a live application's directory
as the destination. An isolated read-only source mount and an offline change
window are mandatory. Stop/fence all writers through the approved operator before
running the tool: a read-only mount does not prevent writes through other mounts.
The tool checks source contents repeatedly, but cannot itself prove service
quiescence. It never stops containers or changes mounts.

Provide the reviewed source revision, prior image digest and candidate image
digest. These are **declared rollback metadata**, not verified attestations: the
separate release process must verify image signatures, source labels, and allowed
release authority. No tag, branch name, guessed digest or superseded image should
be supplied. The target image remains subject to #84's unfinished image build,
Composer audit, runtime-role tests, scans, and protected review.

## Plan, apply, and verify again

Run `python3 scripts/migrate-mautic-volumes migrate --help` for arguments.
Supply `--source`, `--destination`, `--backup-file`, `--source-sha`, `--source-image`,
and `--target-image`. Without `--apply` the tool checks source structure, declared
image identity and available space, then returns `DRY_RUN` without creating files.
This plan does not verify recipient key availability or successful encryption.

Apply additionally requires `--apply --confirm OFFLINE_MAUTIC_DATA_V1`,
`--recipient-file` (an independent public encryption key) and
`--recipient-fingerprint` (its independently confirmed full uppercase fingerprint).
A private temporary GPG home imports only that public recipient; secret-key input,
multiple primary keys or a fingerprint mismatch fail closed. No private backup key
is needed for migration. Diagnostics contain no paths, file contents, keys, or
recipient names. The generic BLOCKED result must not be mistaken for success.

The tool copies into a private sibling staging directory, verifies bytes and
metadata, streams a tar checkpoint directly into GPG encryption, fsyncs it, and
creates the requested checkpoint without overwrite. Only ciphertext is written
to the backup directory. A checksum-bound receipt is stored in `migration.json`
inside the new data bundle. Linux `renameat2(RENAME_NOREPLACE)` publishes the whole
bundle atomically; an existing destination, including an empty one created by a
competing process, is never replaced. Re-running the same migration verifies both
the copied data and the original encrypted checkpoint and returns
`ALREADY_VERIFIED` without rewriting either.

A failed copy or authentication leaves no published destination. A failure after
checkpoint publication preserves that checkpoint for investigation. A host crash
may leave private `.mautic-data-*` staging directories: inspect and remove only
those positively attributed to this operation, through a separately approved
cleanup. Do not delete unrelated temporary files or an existing destination.

## Independent restore rehearsal

Retain the checkpoint checksum from the private receipt through your approved
evidence channel. Copy the encrypted checkpoint off-host under the existing backup
policy; this script does not itself certify off-host storage.

Use the `restore` subcommand with `--backup-file`, `--backup-sha256`, an existing
private `--gpg-home` capable of decrypting it, and a **new** `--destination`.
Without `--apply`, decryption and verification are streamed without creating a
destination; GPG may create locks or agent state in its key home. Restore apply
also requires `--confirm OFFLINE_MAUTIC_DATA_V1`.

The expected ciphertext checksum is checked before decryption. The archive must
start with the bounded manifest and then contain exactly its listed regular files
and directories, with matching types, sizes, ownership, modes and content hashes.
No general tar extraction API is used. Link/traversal/device/duplicate/extra-member
payloads are rejected. The complete GPG stream must authenticate before publication.
A changed or truncated ciphertext or decryption failure never publishes a restore.

Compare restored data against the recorded manifest, measure actual elapsed
backup/restore time and last quiesced write time, and record observed RTO/RPO.
The source tests do not manufacture production RTO/RPO values. Only after this
rehearsal, database backup verification, immutable-image acceptance and separate
approval may an operator change mounts. No mount cutover is performed here.

## Rollback and release gates

Until a separately approved cutover, the original legacy volume and running
configuration are untouched. Rollback before cutover therefore means retaining
the original volume/image tuple, not deleting new or old data automatically.
After any approved cutover with new writes, reverting to the old volume would lose
those writes: reconcile/checkpoint them first and use the service-specific rollback
plan. Database rollback is separate and is not implemented by this file tool.

The standard Python CI includes the unit, fault-injection and real-GPG round-trip
suite. `Mautic offline data rehearsal` additionally runs the suite as root on an
isolated hosted runner with a real temporary read-only bind mount. Both are source
rehearsals, not proof that production data or runtime has been migrated.

Upstream references: Mautic image persistent-storage contract
https://hub.docker.com/r/mautic/mautic and Python's tar security notes
https://docs.python.org/3/library/tarfile.html#extraction-filters .
