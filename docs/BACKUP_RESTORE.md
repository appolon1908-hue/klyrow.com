# Backup and restore

`scripts/backup` creates consistent Klyrow PostgreSQL, Mautic MariaDB and Postal MariaDB dumps plus configuration, hashes every artifact, and defaults to a timestamped ignored directory. Encrypt and copy backups off-host with restricted retention. Signing keys and `.env` are sensitive; the archive must use approved encrypted storage.

Validate with a disposable environment. `scripts/restore BACKUP_DIR` verifies hashes and refuses to proceed unless `CONFIRM_RESTORE=RESTORE_KLYROW`; it overwrites only Klyrow databases. Stop writers before production restore, take a fresh backup, restore, restart, then test login, tenant isolation, campaign state, Postal queues and a safe-mode message.

