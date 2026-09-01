# Hardened Mautic runtime

Production Mautic uses the protected, source-bound image
`ghcr.io/appolon1908-hue/klyrow-mautic@sha256:<digest>`. The protected workflow
builds it from an immutable Mautic base and a frozen Debian snapshot, applies
the reviewed Composer lock patch, runs Composer's advisory gate, removes Node
and its build caches, scans the final image, produces an SBOM and provenance,
signs the exact digest, and promotes it only after verification.

The production Compose contract persists only Mautic configuration, logs, and
uploaded media. It must never mount a volume over `/var/www/html`, because that
would hide the protected application and dependency bytes from the image.

## One-time legacy volume migration

Before replacing a deployment that currently mounts one legacy volume over
`/var/www/html`:

1. Complete and verify the encrypted database/application backup.
2. Stop the three Mautic containers without changing any other service.
3. Pull and independently verify the protected Mautic digest, signature,
   provenance, SBOM, source revision, and zero-high/critical scan.
4. Identify the exact legacy volume name read-only.
5. Run the reviewed migration with the backup recipient public key available:

   ```text
   CONFIRM_MAUTIC_VOLUME_MIGRATION=MIGRATE_PERSISTENT_DATA_ONLY \
     scripts/migrate-mautic-volumes \
     <legacy-volume> \
     ghcr.io/appolon1908-hue/klyrow-mautic@sha256:<digest> \
     /var/backups/klyrow/mautic-volume-migration
   ```

The utility refuses a mutable or noncanonical image, refuses running source or
destination volumes, creates an encrypted checkpoint before mutation, copies
only the four persistent paths, compares normalized content digests, and leaves
the legacy volume intact. A retry succeeds only when every existing destination
is byte-equivalent to its source.

Do not remove the legacy volume during activation. Rollback uses the encrypted
checkpoint and preserved legacy volume through the separately reviewed rollback
procedure. Delivery, campaign, bulk, and external-email flags remain false
through this migration.
