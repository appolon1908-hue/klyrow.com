# Klyrow hardened PostgreSQL runtime

Status: repository-only candidate for issue #84  
Image publication: **disabled**  
Database or volume mutation: **not authorized**

## Historical source review

The preserved aggregate identified historical
`docker/database-runtime.Dockerfile` blob
`a54b14ff1eb74ae21069c72a5e9fd57347563f9b`.
Its useful bounded inputs were:

- Go builder manifest
  `sha256:e401dae1bf814e29204a8cb7915682e1780951e609ca0dd8865ee1937f510c48`;
- PostgreSQL manifest
  `sha256:051f7b7b3abdd564d5d1bd1e8c4b9c1b6e77087d1dd22020ede611c096a272e0`;
- gosu 1.19 source archive checksum
  `sha256:cd9719b775dbfedae53923c9b0dc792b66d42c51e0b36652ed6f747fbadc0164`.

The old file also contained a MariaDB target. That target is deliberately not
ported here: PostgreSQL and Mautic/MariaDB have different runtime, migration,
backup, and rollback boundaries and must be reviewed independently.

No old Compose file, frontend APK, image validator, aggregate CI workflow,
release test, or gitleaks exception is copied.

## Candidate construction

`docker/database-runtime.Dockerfile`:

- pins both base images by immutable manifest digest;
- downloads exactly gosu 1.19 with BuildKit `ADD --checksum`;
- builds gosu statically with `CGO_ENABLED=0`, `-trimpath`, disabled VCS
  stamping, and an empty Go build ID;
- normalizes the output timestamp from `SOURCE_DATE_EPOCH`;
- copies only the resulting binary into the final PostgreSQL image;
- records the exact source commit as an OCI revision label;
- verifies PostgreSQL 17 compatibility, the expected gosu version, and the
  non-root postgres account during the build;
- deliberately inherits the official PostgreSQL entrypoint, command,
  stop-signal, and new-volume initialization behavior.

The immutable base digest is the patch-level authority. The repository does
not duplicate the digest's patch release as a mutable text assertion. Build
and runtime checks require the supported PostgreSQL 17 major line, while any
patch update requires a reviewed digest change and fresh scan, SBOM,
reproducibility, backup/restore, and rollback evidence.

The final image does not add a package manager transaction, shell download
client, compiler, source archive, registry credential, or application secret.
It does not force a final `USER postgres`, because the inherited entrypoint
must be able to initialize and correct ownership on a new persistent volume
before it uses gosu to execute PostgreSQL as the non-root postgres account.

## Exact-head CI

`.github/workflows/database-runtime-ci.yml` is a non-publishing pull-request
workflow. It:

1. checks out the exact PR head without persisted credentials;
2. validates the source/Compose contract;
3. builds only the `postgres-runtime` target with source and epoch binding;
4. verifies inherited entrypoint/command, PostgreSQL 17, and OCI revision
   readback;
5. creates an isolated throwaway volume with a file-backed password;
6. proves readiness, non-root PID 1, data-directory ownership, and a write;
7. stops PostgreSQL with its normal signal path, verifies exit code zero,
   restarts the same container/volume, and verifies persisted data;
8. scans HIGH/CRITICAL vulnerabilities fail-closed and retains SARIF evidence;
9. generates a CycloneDX SBOM;
10. performs two no-cache OCI exports with rewritten timestamps and requires
    byte equality.

The workflow has no package-write permission, registry login, registry output,
or publish job. It does not publish an image.

## Compose and release boundary

Current protected Compose already requires:

```text
KLYROW_POSTGRES_IMAGE=<registry/name>@sha256:<64 lowercase hex>
```

This candidate intentionally does not change `KLYROW_POSTGRES_IMAGE`, add a
Compose `build:` directive, retag a running image, or record an unbuilt digest.
A future protected-main publication change must build once, scan the exact
registry digest, generate final SBOM/provenance/signing evidence, and then
update a separately approved immutable release tuple.

No database volume is migrated, initialized, mounted, copied, renamed, or cut
over by this repository change. Production data work requires the separate
root-only migration/backup/restore rehearsal and approved change window
preserved by issue #84.

## Merge conditions

Before this candidate can leave draft:

- both repository-wide exact-head workflows must remain green;
- the dedicated PostgreSQL contract and image jobs must pass;
- the fresh-volume, signal-stop, restart, scan, SBOM, and byte-reproducibility
  evidence must all be successful on the same unchanged head;
- every review thread must be resolved;
- a fresh independent approval must certify the final head.

Merging source alone authorizes no image publication, database mutation,
volume migration, Mautic cutover, provider activation, customer email, or
runtime deployment.
