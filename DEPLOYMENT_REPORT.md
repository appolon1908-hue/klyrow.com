# Deployment report — 2026-08-15

## Deployed

Klyrow is deployed on `37.27.128.39` (`10.40.0.2`) from branch `agent/production-email-platform`. The stack includes the tenant-scoped FastAPI gateway and portal, PostgreSQL, Mautic 7.1.3, Postal 3.3.7, isolated MariaDB instances, RabbitMQ, Prometheus, Grafana, node-exporter, cron/workers, backup tooling, and systemd boot/timer units. Secrets exist only in root-readable environment/storage files.

Nginx serves valid Let's Encrypt TLS for `klyrow.com`, `app.klyrow.com`, `api.klyrow.com`, `track.klyrow.com`, and `bounce.klyrow.com`. Existing Kyqra/Telnexa routes were preserved. Databases, RabbitMQ, Postal administration, Docker, Prometheus, and internal workers have no public host ports. The private API binds `10.40.0.2:18000`; Postal SMTP is deliberately loopback-only at `127.0.0.1:2525` until its launch gates pass.

## Verified

- Gateway tests: 6/6 pass, including tenant isolation, API-key rejection, HMAC rejection, replay defense, and idempotency.
- Controlled production smoke: login, safe send, signed middleware event, replay rejection, and bad-HMAC rejection pass. No carrier submission occurred.
- Middleware to Klyrow: private send, idempotent repeat, and invalid-key rejection pass.
- Klyrow to middleware: signed events reached `10.40.0.1:8095` over the vSwitch.
- Mautic, Postal web/worker/SMTP, databases, RabbitMQ, gateway, and monitoring containers are running; health-checked services report healthy.
- SMTP authentication was validated without sending a message. Queue/application data persist across a controlled service restart.
- HTTPS routes return 200. The systemd stack unit and daily backup timer are enabled; a complete database/config backup with checksums was created.

## External launch gates

Production delivery remains disabled with `KLYROW_SAFE_MODE=true`. `mail.klyrow.com` A, MX, SPF, Postal DKIM, SMTP TLS, and provider PTR are not fully published/verified. The currently observed PTR is not the mail hostname. See `docs/DNS_AND_DELIVERABILITY.md` for exact records.

Odoo and n8n writes are correctly routed through middleware, but production execution is disabled there (`ODOO_AUTOMATION_WRITES_ENABLED=false`, `N8N_EVENT_DELIVERY_ENABLED=false`, and `N8N_PRODUCTION_WORKFLOWS_ENABLED=false`). Credentials/workflow targets and owner approval are required before contact-sync and workflow tests can truthfully pass.

Private application traffic works. Private SSH to `10.40.0.2` presents a host identity that does not match the verified server and no packets arrive at that server; it was not trusted. Management used the verified public host key. The provider/vSwitch SSH route must be corrected before using `ssh klyrow-server` privately.
