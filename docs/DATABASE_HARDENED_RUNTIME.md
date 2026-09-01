# Hardened database runtimes

Production PostgreSQL and MariaDB use protected, source-bound images:

- `ghcr.io/appolon1908-hue/klyrow-postgres@sha256:<digest>`
- `ghcr.io/appolon1908-hue/klyrow-mariadb@sha256:<digest>`

The database servers remain the unmodified PostgreSQL 17.11 and MariaDB
11.4.13 official-image payloads. The protected build replaces only `gosu`, the
privilege-drop helper embedded in both upstream images. It builds gosu 1.19
from a checksum-bound source archive with a digest-pinned Go 1.25.13 toolchain,
disables CGO, strips build paths and the build ID, and verifies the resulting
helper before copying it into either final image.

The protected workflow boots both final candidates on disposable storage,
requires their native readiness probes to pass, scans the exact final images,
generates SBOM and provenance records, compares two no-cache OCI exports, and
signs and promotes only the verified digests. Production Compose validation
accepts only the canonical protected repositories and requires the Mautic and
Postal database services to share one exact MariaDB digest.

## Activation boundary

Changing either production database image is a separate reviewed host change.
Before activation:

1. Verify the exact image signature, source revision, provenance, SBOM, and
   zero-high/critical scan independently.
2. Create and restore-test encrypted logical and volume-level backups.
3. Record the current image digest, database version, volume identity, and
   rollback owner.
4. Stop only the dependent database and application services covered by the
   approved maintenance plan.
5. Start the exact protected digest against the preserved volume and run only
   the approved database readiness and schema checks.

Do not delete or rewrite the pre-activation volumes during the validation
window. A failed readiness, schema, or application compatibility gate requires
the reviewed database rollback procedure; it never authorizes an unreviewed
binary downgrade against a volume already opened by a newer server. Email,
campaign, bulk, and external-delivery flags remain disabled through database
activation and rollback certification.
