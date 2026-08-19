# Backup and restore

`scripts/backup` creates consistent Klyrow PostgreSQL, Mautic MariaDB and Postal MariaDB dumps plus configuration, hashes every artifact, and defaults to a timestamped ignored directory. Encrypt and copy backups off-host with restricted retention. Signing keys and `.env` are sensitive; the archive must use approved encrypted storage.

Postal DKIM private keys live in the Postal database, so the Postal database dump is required for signing identity recovery. The configuration archive covers Postal configuration/signing material and application secrets; after SMTP TLS is enabled, separately preserve the Certbot account/renewal state and Postal certificate-copy procedure. RabbitMQ is persistent runtime state but is not a substitute for source-of-truth database/configuration backups.

Validate with a disposable environment. `scripts/restore BACKUP_DIR` verifies hashes and refuses to proceed unless `CONFIRM_RESTORE=RESTORE_KLYROW`; it overwrites only Klyrow databases. Stop writers before production restore, take a fresh backup, restore, restart, then test login, tenant isolation, campaign state, Postal queues and a safe-mode message.

The daily `klyrow-backup.timer` is enabled and active. A fresh pre-change backup was written to ignored local storage on 2026-08-15. Off-host encryption, retention, and a disposable full restore remain operational acceptance items.
