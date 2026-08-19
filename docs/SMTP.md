# SMTP

See [POSTAL_SMTP.md](POSTAL_SMTP.md) for the audited production runbook and [MAIL_DNS.md](MAIL_DNS.md) for the exact live DNS contract.

Postal is the approved relay. Mautic connects to `postal-smtp:25` on the private Compose network; Klyrow clients use the gateway and never Postal internals. The host exposes Postal only on `127.0.0.1:2525` while launch gates are incomplete. Authentication was tested with a controlled session ending at `QUIT`; no message or carrier submission was made.

Create separate Postal credentials per customer/server, store them only in approved secret storage, apply tenant quotas and rate limits, and revoke on suspension. Never log SMTP passwords or full authorization headers. Public SMTP must remain closed until the mail A/MX/PTR, SPF, DKIM, SMTP certificate, STARTTLS, bounce processing, and abuse monitoring all pass. When approved, expose only the chosen SMTP ports and add narrow firewall rules; never expose Postal web/admin, MariaDB, or RabbitMQ.

Queue state resides in persistent RabbitMQ/Postal volumes. Monitor worker health, queue depth, deferrals, TLS failures, bounces, complaints, and per-tenant rates. Stop the Postal worker to halt delivery during an incident without deleting queued mail.
