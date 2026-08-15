# Operations

Use `scripts/start|stop|restart|health|update`. `update` refuses a dirty worktree. Prometheus scrapes gateway request/mail metrics; Grafana is loopback-only behind the protected app proxy. Monitor API rate/status, accepted/queued/sent/delivered counts, bounces, complaints, Postal queue/worker, all databases, RabbitMQ, container health, host node metrics, disk, webhook failures and TLS expiry.

Before enabling delivery: bootstrap Postal admin and organization/server; save API/SMTP credentials in `.env`; install Postal's signing key; configure Mautic DSN to Postal SMTP on the backend network; simulate bounces/unsubscribes; verify restore; publish DNS and PTR; test only controlled recipients. Keep `KLYROW_SAFE_MODE=true` until all gates pass.

Incident response: suspend the tenant, revoke API keys, preserve audit/event logs, stop the Postal worker if mail must halt, rotate affected secrets, investigate, then resume gradually. Do not delete unrelated shared-server containers or alter global firewall policy.

Monitor request latency, statuses, profile/event growth, journey failures, consent revocations, suppression growth and deliverability alerts. The gateway listens on loopback and private `10.40.0.2:18000`; Postal SMTP remains on `127.0.0.1:2525` until DNS/PTR/TLS pass. Replace in-process rate limiting with a shared store before gateway scaling.
