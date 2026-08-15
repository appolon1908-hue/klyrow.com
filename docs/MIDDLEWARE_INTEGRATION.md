# Middleware integration

Klyrow uses the private vSwitch (`10.40.0.2:18000` to `10.40.0.1:8095`) and dedicated `KLYROW_MIDDLEWARE_API_KEY` and `KLYROW_WEBHOOK_SECRET`. Never reuse Kyqra/Telnexa credentials.

Sign the exact request body with HMAC-SHA256 over `timestamp + "\n" + event_id + "\n" + "klyrow" + "\n" + body`. Send `Authorization: Bearer <KLYROW_MIDDLEWARE_API_KEY>`, `X-Source-System: klyrow`, `X-Klyrow-Timestamp`, `X-Klyrow-Event-Id`, and `X-Klyrow-Signature: sha256=<lowercase hex>`. The receiver rejects timestamps outside five minutes, uses constant-time comparison, and persists event IDs to reject replay. Supported event names include queued, sent, delivered, bounced, complained, opened, clicked, unsubscribed, campaign started/completed/failed.

The deployment key fingerprint is `SHA256:UqRuMHXxxtSFH4evhm+GP5Qp1DNaPLpU3nYf+RfgOQA`. The `klyrow-deploy` account is installed. The private address currently presents an SSH host key different from the verified public host and must not be trusted until the vSwitch/provider conflict is corrected; management temporarily uses the verified public SSH endpoint. Never copy the private key into Git.

Middleware calls Klyrow at `http://10.40.0.2:18000`, with `Authorization: Bearer ...`, `X-Klyrow-Tenant-Id`, and an `Idempotency-Key`. Available private operations include `/v1/email/send`, `/v1/email/bulk`, `/v1/campaigns`, `/v1/messages/:id`, `/v1/campaigns/:id`, and `/v1/health`. The firewall permits port 18000 only from `10.40.0.1`; the same port is not publicly bound.

Klyrow events enter middleware at `/api/v1/klyrow/events`; dedicated paths also exist for campaigns, contacts, bounces, complaints, and unsubscribes. Middleware validates and normalizes before invoking its Odoo service layer or internal n8n events. Klyrow never accesses Odoo PostgreSQL or arbitrary public n8n webhooks. At deployment time Odoo writes and n8n delivery remain explicitly disabled in middleware; enable them only after approved credentials and workflow targets are installed, then re-run the controlled contact/event tests.

Retries use bounded exponential backoff in the event delivery layer; receivers must return the prior resource for the same idempotency key/body and reject reuse with a different body. Rotate the API key and HMAC secret independently: install new values on both ends, restart the two integration services, run signed/invalid/replay tests, then revoke the old values. Logs include system, event/message/campaign/customer IDs but never credentials or authorization headers.
