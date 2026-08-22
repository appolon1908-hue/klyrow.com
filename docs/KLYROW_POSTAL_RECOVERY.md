# Klyrow Postal Recovery

Backups include Postal database/configuration, Klyrow database, RabbitMQ definitions, routes, suppressions, mail keys/configuration, proxy/TLS configuration, and manifests. Archives are encrypted and checksummed.

Restore only into an isolated networkless environment first. Verify tenants, domains, senders, SMTP metadata, messages, suppressions, inbound routes, and outboxes. Production restore requires a maintenance window, a fresh pre-restore backup, exact target validation, and post-restore reconciliation.
