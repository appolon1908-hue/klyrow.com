# Klyrow encrypted Backblaze backups

The Backblaze backend stores the existing public-key encrypted backup format.
Set `KLYROW_BACKUP_OFFHOST_BACKEND=b2` in the backup process environment to
select it through `scripts/archive-offhost`. The default `mounted` backend is
unchanged. An unknown backend stops the backup.

Install AWS CLI v2 on the archive host. Set `KLYROW_RELEASE_SHA` to the exact
source revision represented by the backup. The uploader requires a full commit
SHA and limits a single archive to 5,000,000,000 bytes; larger archives stop
before upload and need a reviewed multipart implementation.

`KLYROW_BACKUP_B2_CONFIG_DIR` defaults to `/etc/codestra/backup`. It must contain
these root-owned regular files, accessible only to root (mode 0600 or 0400):

| File | Content |
| --- | --- |
| `b2-access-key-id` | Backblaze application key ID |
| `b2-secret-access-key` | Matching application key |
| `b2-region` | Backblaze region, for example `us-east-005` |
| `b2-endpoint` | Exact HTTPS endpoint matching that region |
| `b2-bucket` | Existing private backup bucket |

Use a standard application key scoped to the backup bucket and Klyrow prefix,
with write and read capabilities for upload and exact-version verification.
The default prefix is `codestra/klyrow`; Odoo's `codestra/odoo19` prefix is
separate. Provision credentials through the secure server configuration, never
Git or chat. The uploader uses explicit file credentials and ignores ambient
AWS profiles, proxy settings and alternate endpoints. TLS verification remains
enabled. See [Backblaze application keys](https://www.backblaze.com/docs/cloud-storage-application-keys).

The archive and its checksum must exist before invocation. The uploader rejects
plaintext/legacy symmetric headers, mismatched checksums, archive symlinks and
unavailable credentials. It requests AES256 server-side encryption in addition
to the archive's OpenPGP encryption. These are separate from storage credentials;
see [Backblaze server-side encryption](https://www.backblaze.com/docs/cloud-storage-server-side-encryption).

Objects use `prefix/source-sha/archive-sha256/archive-name`. Archive, checksum
and receipt are each downloaded by the returned object version and checked byte
for byte with SHA256. An ETag alone is not accepted as integrity proof. Missing
versions, wrong encryption metadata, changed source files and readback mismatch
all fail. Partial attempts may leave encrypted objects without a successful
receipt; this script does not delete versions or change bucket lifecycle/Object
Lock settings. A sanitized local receipt is written only after all three
readbacks pass. CLI errors are reduced to fixed error codes.

The recovery private key can stay on a separate recovery/archive host. Transfer
only ciphertext and its checksum to that host and run `archive-offhost` there
with the same release SHA and B2 configuration. Keep the producing backup job
failed until the off-host receipt is obtained; disabling
`KLYROW_BACKUP_OFFHOST_REQUIRED` does not meet the production gate. The uploader
does not establish a transfer route, authorize a production migration, decrypt
backups, or certify their contents. Full isolated restore remains required.

## Production evidence — 2026-09-10

The following observations describe this date, not a standing certification:

| Check | Evidence |
| --- | --- |
| Public recipient installed | `37.27.128.39:/etc/klyrow/backup-recipient-public.asc`, root-owned mode 0600 |
| Full fingerprint | `94E0D73CF47E6FD06C411E3EF2AAF5BE2E5AA8B5` |
| Existing recovery custody | `65.109.65.169:/etc/codestra/backup-gpg`; private material was not copied to Klyrow |
| Recovery-key probe | Fresh random bytes encrypted using the public file and decrypted with the core keyring matched exactly |
| B2 endpoint/bucket | `https://s3.us-east-005.backblazeb2.com`, `Codestra` |
| B2 credential verification | A read-only request under `codestra/klyrow/` failed with `InvalidAccessKeyId`; no backup upload occurred |
| Current live source | `da9d85891a4e313748e309aed86662d6c03d26bb` |
| Fresh legacy backup | `/var/backups/codestra-operators/klyrow/20260910T111836Z` |
| Recipient-encrypted archive | `klyrow-legacy-20260910T111836Z.tar.gz.gpg`, 15,885,616 bytes |
| Archive SHA256 | `179ada8bb0736a19299d336d7cbf01eedd405a2ae72099702a26744906eeb76d` |

The existing restricted backup operator captured PostgreSQL, Mautic and Postal
database dumps, configuration and runtime recovery files and passed its archive
validation. Its symmetric output was streamed directly into encryption for the
public recipient; no plaintext file was created during that conversion. This
is the **legacy operator payload**, not the current canonical durable-keyring
backup format. The recovery-key probe does not constitute a full restore of
this archive. Mautic files, drained RabbitMQ state, writer quiescence and the
new durable-result keyring contract remain prerequisites for the canonical
pre-migration backup and exact-image isolated restore. Existing backup timers
and production applications were not changed by this repair.

Protected build [34428610486](https://github.com/appolon1908-hue/klyrow.com/actions/runs/34428610486)
published the signed four-image release for merged source
`28e466f535365045054bb80c81c59fcf1b191895`; all five jobs passed. The upgrade adds
three database migrations. No production migration or application cutover was
performed. Restore certification, usable Backblaze credentials and the other
release/review gates remain required.

Replace the invalid application key in the secure files on the archive host,
then validate the scoped upload/readback with an encrypted fixture before
capturing and restoring the canonical pre-migration backup. Do not replace the
working recovery key to repair a storage-authentication failure.
