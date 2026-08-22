# Klyrow production release evidence — 2026-08-22

## Release

- Source: `0ffa0e064635dcca808218e56c8ed6316d42ab5a`
- Protected PR: https://github.com/appolon1908-hue/klyrow.com/pull/11
- Gateway image: `klyrow-gateway:0ffa0e0`
- Migrator image: `klyrow-migrate:0ffa0e0`
- Production host: `37.27.128.39` (`10.40.0.4`)
- Encrypted backup: `/opt/klyrow/backups/saas-release-20260822T230000Z/klyrow.pgcustom.enc`
- Backup decryption key: root-only Server A file `/etc/codestra/secrets/klyrow-release-20260822-backup.key`
- Encrypted backup SHA-256: `a770aeb2d82be6f7c8f77ecbcdaefa3974393ec64228fd88c6d544aefe2cbf58`

## Verification

- Automated tests: `81 passed`
- PostgreSQL production migrations: `14` tracked checksums
- Combined legacy and SaaS schema: `112` expected tables after registry separation (provider tables preserved)
- Gateway `/healthz`: PASS
- Gateway `/readyz`: PASS (`safe_mode=true`)
- Gateway `/version`: `0ffa0e0`
- SMTP relay health: PASS
- `api.klyrow.com/healthz`: HTTP 200
- Canonical Keycloak discovery: HTTP 200
- Gitleaks: no leaks found
- pip-audit: no known vulnerabilities
- Trivy gateway/migrator: 0 HIGH, 0 CRITICAL (unfixed excluded by policy)
- Active email outbox rows: `0`
- Active provider queue rows: `0`

## Safety gates

- `KLYROW_SAFE_MODE=true`
- `KLYROW_PRODUCTION_GATE_APPROVED=false`
- `LIVE_EMAIL_DELIVERY=false`
- `EXTERNAL_EMAIL_DELIVERY=false`
- `PRODUCTION_PROVIDER_ROUTING=false`
- `MARKETING_DELIVERY=false`
- `LIVE_SMS_DELIVERY=false`
- `EXTERNAL_SMS_DELIVERY=false`
- Customer email sent during release: `0`

## Shared-host regression

- Telnexa billing API image unchanged and healthy.
- Telnexa billing worker image unchanged.
- Jasmin image unchanged and healthy.
- Telnexa RabbitMQ image unchanged and healthy.
- Telnexa PostgreSQL and billing PostgreSQL images unchanged and healthy.
- No SMS, SMPP, Jasmin, or Telnexa billing configuration was modified.

## Release events and remediation

The first upgrade attempt failed closed on a legacy-schema mismatch. Its transaction rolled back. A compatibility migration was tested against a schema-only PostgreSQL 17 clone. A later replacement exposed provider modules present in the production image but absent from protected source and an SMTP UID-specific secret mount. The prior image was restored, the provider modules were incorporated into source, SaaS registries were separated from provider tables, the full suite was rerun, and SMTP received a dedicated mode-0400 UID-999 secret file. Both final containers are healthy.

## Open certification gates

- `https://klyrow.co` does not resolve in public DNS; the customer application hostname is unavailable.
- PR #11 requires independent review and CI is still running at evidence creation time.
- Live external delivery remains intentionally disabled; no live transactional, SMTP, campaign, or inbound external E2E is claimed.
- A current isolated restore exercise and disaster-recovery timing certification remain required.

## Truthful status

`FINAL_STATUS=PRODUCTION_DEPLOYED_SAFE_MODE_CERTIFICATION_PENDING`
