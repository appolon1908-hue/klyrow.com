# Operations

Use `scripts/start|stop|restart|health|update`. `update` refuses a dirty worktree. Prometheus scrapes gateway request/mail metrics; Grafana is loopback-only behind the protected app proxy. Monitor API rate/status, accepted/queued/sent/delivered counts, bounces, complaints, Postal queue/worker, all databases, RabbitMQ, container health, host node metrics, disk, webhook failures and TLS expiry.

Before enabling delivery: bootstrap Postal admin and organization/server; save API/SMTP credentials in `.env`; install Postal's signing key; configure Mautic DSN to Postal SMTP on the backend network; simulate bounces/unsubscribes; verify restore; publish DNS and PTR; test only controlled recipients. Keep `KLYROW_SAFE_MODE=true` until all gates pass.

Run `scripts/mail-readiness` for public A/MX/SPF/DKIM/DMARC/PTR, local SMTP exposure, STARTTLS, certificate, container health, disk, RabbitMQ, and database checks. Prometheus currently scrapes gateway lifecycle/request metrics and node-exporter host/disk metrics; Docker health checks cover Postal SMTP/worker/web, RabbitMQ, PostgreSQL, and both MariaDB instances. Alerting for queue depth, deferred mail, bounce/complaint rate, DNS/DKIM drift, external SMTP reachability, and mail-certificate expiry must be connected to the existing monitoring destination before launch; no competing stack has been created.

Incident response: suspend the tenant, revoke API keys, preserve audit/event logs, stop the Postal worker if mail must halt, rotate affected secrets, investigate, then resume gradually. Do not delete unrelated shared-server containers or alter global firewall policy.

Deploy only a clean, committed tree with `sudo scripts/deploy`. Images are tagged with the exact 40-character Git commit and the active release is written to `/var/lib/klyrow/releases/current`. Use `sudo scripts/rollback-release <sha>` to restore previously built application images. Migrations are forward-only and must remain backward compatible; application rollback does not reverse data.

Multiple Postal servers are selected by sender domain through `/etc/klyrow/postal-transports.json`. The registry stores secret file references, never API keys. Each non-default transport must also declare its Klyrow `tenant_id` and its Postal signing public-key file so lifecycle and inbound requests cannot cross server boundaries. The default generator creates empty Beyvra API/signing-key files under `/etc/klyrow/postal-credentials`; live Beyvra traffic remains fail-closed until an operator installs both and maps its tenant. Set `KLYROW_PROVIDER_LIVE_DELIVERY_ENABLED=true` only after `GET /v1/admin/mail/readiness` shows transport and PTR readiness.

For Gmail placement checks, store one root-owned JSON secret beneath `KLYROW_SEED_SECRET_DIR` containing `client_id`, `client_secret`, and `refresh_token`, and register only a `secret://relative/path.json` reference. Grant the OAuth client read-only Gmail access. Access and refresh tokens are neither returned by the API nor persisted in Klyrow tables.

Monitor request latency, statuses, profile/event growth, journey failures, consent revocations, suppression growth and deliverability alerts. The gateway listens on loopback and private `10.40.0.2:18000`; Postal SMTP remains on `127.0.0.1:2525` until DNS/PTR/TLS pass. Replace in-process rate limiting with a shared store before gateway scaling.

Synthetic HMAC/replay tests use `scripts/test-webhook` and `tests/production_safe_smoke.py`; they do not submit carrier mail. Middleware at `10.40.0.1:8095` is healthy and accepts signed Klyrow events. Its n8n delivery and Odoo writes remain disabled pending approved credentials/workflow targets, and Klyrow never writes directly to Odoo PostgreSQL.
