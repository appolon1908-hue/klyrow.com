# Mautic OAuth credential files

`scripts/migrate-runtime-secrets` now includes
`KLYROW_MAUTIC_API_CLIENT_ID_FILE` and
`KLYROW_MAUTIC_API_CLIENT_SECRET_FILE`, required by the Mautic worker's Compose
secret mounts. Legacy plaintext values are moved into root-owned 0600 files
and removed from `.env`. A repeated migration preserves values and references.

An existing absolute credential-file reference remains authoritative. Missing,
relative, directory, or symlink references are rejected without replacing
`.env`; repair the reference through the approved secret-management process.

When no OAuth credentials exist, the standard files are created empty. Client
IDs and client secrets are issued by the identity provider and are never
randomly invented here. The adapter remains unavailable until approved values
are supplied. This bootstrap does not register a client, obtain a token, run a
database migration, or activate delivery.

Back up the root-owned credential files through the existing encrypted backup
procedure. Restore the same file references and permissions before starting
the worker. For rollback, keep the files and their previous approved values;
do not restore plaintext credentials to `.env` or print them in logs.

The isolated bootstrap tests run the real migration twice, verify 0600 and
requested root ownership, check missing-credential behavior, preserve existing
authority, and reject invalid file references without exposing values.
