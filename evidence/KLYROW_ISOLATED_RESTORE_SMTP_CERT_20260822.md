# Klyrow isolated restore and SMTP certification — 2026-08-22

## Restore source

- Encrypted production backup: `/opt/klyrow/backups/saas-release-20260822T230000Z/klyrow.pgcustom.enc`
- Backup SHA-256: `a770aeb2d82be6f7c8f77ecbcdaefa3974393ec64228fd88c6d544aefe2cbf58`
- Restore target: ephemeral PostgreSQL `17.6` container on Server A
- Backup decrypted as a stream; no plaintext dump was persisted.

## Restore results

- Encrypted stream restore: PASS
- Production data before migration: 55 tables, 1 tenant, 12 messages, 1 provider message
- Current migration ledger: 14 checksummed migrations
- Schema after migration: 111 tables
- Migration rerun/idempotency: PASS
- Preserved after migration: 1 tenant, 12 messages, 1 provider message, 8 sender identities, 2 SMTP credentials
- Canary ledger restored/normalized to `reserved=0`, `claimed=0`
- Governed provider sender and SMTP tables preserved
- Separate SaaS sender and tenant-SMTP registries created

## Isolated SMTP results

- Synthetic tenant only; no customer identity used
- Ephemeral self-signed TLS certificate only
- SMTP authentication: PASS
- STARTTLS: PASS
- Internal sink acceptance: PASS
- Sandbox flag: `true`
- Provider message state: `QUEUED` in isolated database only
- Audit event: `smtp.message.queued:accepted`
- Exact Message-ID replay: PASS
- Duplicate provider messages: `0` (one total after two submissions)
- Forged From address: DENIED
- Internet delivery: `0`

## Result

`ISOLATED_RESTORE=PASS`

`SMTP_E2E_INTERNAL_SINK=PASS`
