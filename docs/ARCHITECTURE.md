# Architecture

Internet HTTPS reaches the existing host Nginx, then loopback-only Klyrow services. The gateway owns authentication, tenant scoping, sender verification, suppressions, rate limits, quotas, audit events and commercial APIs. It submits approved messages to Postal; Mautic also uses Postal SMTP. Postal workers deliver and return signed events to the gateway, which relays authenticated events to middleware at `10.40.0.1` without writing to Odoo databases.

The `frontend` Compose network contains routable application containers. The `backend` network is internal and contains PostgreSQL, both MariaDB databases, RabbitMQ and monitoring. No datastore exposes a host port. Persistent named volumes cover all state.

Roles are `platform_admin`, `tenant_admin`, `tenant_user`, and optionally `read_only`. Every tenant-owned query includes `tenant_id`; API keys store only SHA-256 digests and are shown once. Sessions are signed, eight-hour JWTs. Production should place a revocation/session store in front of long-lived sessions if requirements expand.

Safe mode accepts validated mail into the Klyrow database without external delivery. Production mode calls Postal only after verified domains, suppression and quota checks.
