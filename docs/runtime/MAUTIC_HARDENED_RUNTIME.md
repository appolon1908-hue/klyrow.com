# Mautic 7.2.0 runtime candidate

Related: #84; source baseline `b7874a4863ff8df8d90da23e820db40e3bb6bcea`.
This is an independently tested candidate, not a production release or cutover.

## Requirement audit before editing

| Requirement on current main | Status | Evidence and action |
| --- | --- | --- |
| PostgreSQL hardening | IMPLEMENTED | #88; retain the independent runtime and CI. |
| Offline data migration and encrypted restore | IMPLEMENTED | #100; retain its data-only bundle, verification and rollback. |
| Mautic image and dependency reconciliation | MISSING | Add `docker/mautic.Dockerfile` using upstream 7.2.0. |
| Historical Guzzle alias | UNSAFE | Do not restore the #72 patch or its `7.15.2 as 7.10.99` alias. |
| Immutable code during volume cutover | UNSAFE | Existing Compose mounts the whole application. Candidate tests mount only data and temporary caches. Production cutover remains separate. |
| Non-root web/cron/worker, secret files, startup controls | PARTIAL | Replace upstream's root startup, automatic migrations and failed-queue consumer in this candidate. |
| Four custom production images and protected release authority | IMPLEMENTED | Keep `ci.yml`, production Compose, image validator and release verifier unchanged. |
| Installed-database/plugin upgrade, real backup/restore and RTO/RPO | MISSING | Requires the approved offline 7.1.3 to 7.2.0 staging rehearsal and separate release review. |

## Exact upstream authority

The historical Dockerfile blob `b3135a9e14180b940a912ceb02f68b8fd8ce2811`
and dependency patch blob `5ec264883255194c4f891717a8989154b2cfa510`
were inspected, not replayed. The former 7.1.3 base constrains Guzzle to
`~7.10.0`; renaming a patched release does not establish compatibility.

[Mautic 7.2.0](https://github.com/mautic/mautic/releases/tag/7.2.0), released
2026-09-02, declares `~7.15.2` in its
[core package](https://github.com/mautic/core-lib/blob/7.2.0/composer.json).
The candidate preserves that real dependency resolution without a package fork,
alias, lock rewrite, or a build-time Composer update:

- Base index: `mirror.gcr.io/mautic/mautic@sha256:dea3bb71a5c5bf4c0c7d1764e58a32109898e7b2e6a710f14f50e2a913c03a0f`.
- Inspected Linux amd64 manifest: `sha256:39e967af9f154d50d1a7cbc12e6cfd5a847939c8abdcace98ab20e30570bdfda`.
- Mautic `7.2.0`, Guzzle `7.15.5`, Composer `2.10.3`, PHP `8.3.33`.
- `composer.json` SHA-256: `59ec10ac76c91171d4139dad05f70c1817022ce4ca068e9f9243e2189a5da9f4`.
- `composer.lock` SHA-256: `995c5149fa9cb76c750a32a19b9168aad1db74cc10d39a3aedc96cb1ff7928f9`.

Builds check those hashes, installed versions, absence of aliases, Composer
validation and actual PHP platform requirements. The immutable Debian snapshot
already reviewed on main supplies OS patches. PCNTL is compiled from the pinned
PHP source so Messenger can receive shutdown signals. Node tooling and generated
cache files are removed before flattening the final image, including its history.
No package vulnerability exception is added.

## Runtime contract

All three roles use the same image, UID/GID `33:33`, no capabilities, a read-only
root filesystem and `no-new-privileges`. Apache listens on port 8080. No port is
published by the rehearsal. The final image declares no anonymous volumes.

`docker/mautic-runtime/runtime.py` replaces upstream startup. It never installs
Mautic, migrates a database, loads fixtures, copies application code into a volume,
changes ownership, or runs commands supplied through container arguments. Startup
requires working installed configuration and a database read. Migration flags and
debug startup are rejected. Background roles additionally require
`KLYROW_MAUTIC_JOBS_ENABLED=true`; the default is false.

The worker runs bounded email and hit consumers. It never automatically consumes
the failed queue. A consumer exit fails the container; the deployment's bounded
restart policy and operator reconciliation handle recovery. Cron preserves the
upstream UTC segments/update/trigger ordering, limits a command to ten minutes,
and fails on command errors. Run one cron replica; this is not a distributed job
lease redesign. Mautic's command locks and the gateway's existing policy remain
necessary. Signal handling stops and reaps process groups, with a 25-second hard
deadline. Configure a container stop grace period of at least 35 seconds.

Health requires the web login endpoint or a fresh supervisor heartbeat with live
children, plus a successful database read. A stopped database is unhealthy. CLI
failure output is suppressed; use the approved private application logs to
investigate. No installation data or credential values are health output.

## Data and secret mapping

Mount the verified #100 offline bundle as follows. The config destination differs
from the legacy image: the image-owned `config/local.php` wrapper must stay intact.

| Bundle/configuration input | Candidate destination | Mode |
| --- | --- | --- |
| `config` | `/var/lib/klyrow-mautic/config` | Read only, operator-owned PHP configuration |
| `logs` | `/var/www/html/var/logs` | Writable by UID 33 |
| `media-files` | `/var/www/html/docroot/media/files` | Writable by UID 33 |
| `media-images` | `/var/www/html/docroot/media/images` | Writable by UID 33 |
| Temporary runtime storage | `/tmp`, `/var/www/html/var/cache`, `/var/www/html/var/tmp` | Per-container tmpfs owned by UID 33 |
| `MAUTIC_DB_PASSWORD_FILE` | One regular file under `/run/secrets/` | Read only |
| `MAUTIC_MAILER_DSN_FILE` | One regular file under `/run/secrets/` | Read only |
| `MAUTIC_SECRET_KEY_FILE` | Existing installation key under `/run/secrets/` | Read only |

Never mount `/var/www/html`, `vendor`, or the image-owned config directory over
the candidate. Review the migrated configuration as executable PHP before use.
Keep all three secret files readable only by the required runtime identity and
approved operators. The wrapper preserves installation settings but always
overrides legacy password, mailer and installation-key values with these files;
plaintext environment alternatives, empty/missing/oversized/multiline files and
symlink secrets fail. Do not generate a replacement installation key during an
upgrade: preserve the existing key and encrypted-data compatibility.

The isolated rehearsal uses `null://null` and an internal Docker network. It
cannot reach Postal, Middleware or the Internet. It creates only a disposable
synthetic database and explicitly initializes that database in an ephemeral
installer container. The long-running roles always use the restricted contract.

## Build and validation

On a clean checkout, supply the exact source SHA and commit timestamp:

```bash
docker buildx build --file docker/mautic.Dockerfile --target mautic-runtime \
  --build-arg SOURCE_COMMIT_SHA="$(git rev-parse HEAD)" \
  --build-arg SOURCE_DATE_EPOCH="$(git log -1 --pretty=%ct)" \
  --load --tag klyrow-mautic:local .
python3 -m pytest -q tests/test_mautic_runtime.py
python3 scripts/mautic-runtime-rehearsal --image klyrow-mautic:local \
  --source-sha "$(git rev-parse HEAD)"
```

The dedicated workflow checks the exact PR head, validates the image, audits the
locked Composer graph, rehearses all roles and secret overrides, checks database
failure and graceful restart, scans HIGH/CRITICAL findings without suppressing
unfixed findings, generates a CycloneDX SBOM, and compares two independent OCI
builds. It retains candidate evidence and has no registry publication permission.
Only the workflow's completed results establish those gates; this document is
not a claim that an unexecuted or failed gate passed.

## Release and rollback boundary

Production still uses its current approved digest and legacy volume. This change
does not select `KLYROW_MAUTIC_IMAGE`, publish a release, change the four-image
protected release ledger, or deploy any service. A subsequent reviewed release
must add Mautic authority additively after all candidate gates pass.

Before cutover, rehearse a real offline installed database and plugin inventory
from 7.1.3 to 7.2.0, including the Klyrow adapter, data bundle, installation key,
backup/restore and measured RTO/RPO. Take the encrypted data and database
checkpoints together. Database upgrades are separate, one-time, reviewed commands;
do not let three runtime roles race migrations. Rolling back an upgraded database
requires its matching pre-upgrade backup and old image/data/configuration set,
not merely selecting the old container tag. Neither source merge nor a synthetic
fresh-install rehearsal substitutes for that evidence.

No gateway API, tenant permission, browser authentication, Postal source, provider
delivery flag, Keycloak identity, Odoo/n8n contract or production data is changed.
