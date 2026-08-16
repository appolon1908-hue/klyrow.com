# Middleware integration

Klyrow uses the private vSwitch (`10.40.0.2:18000` to `10.40.0.1:8095`) and dedicated `KLYROW_MIDDLEWARE_API_KEY` and `KLYROW_WEBHOOK_SECRET`. Never reuse Kyqra/Telnexa credentials.

Sign the exact request body with HMAC-SHA256 over `timestamp + "\n" + event_id + "\n" + "klyrow" + "\n" + body`. Send `Authorization: Bearer <KLYROW_MIDDLEWARE_API_KEY>`, `X-Source-System: klyrow`, `X-Klyrow-Timestamp`, `X-Klyrow-Event-Id`, and `X-Klyrow-Signature: sha256=<lowercase hex>`. The receiver rejects timestamps outside five minutes, uses constant-time comparison, and persists event IDs to reject replay. Supported event names include queued, sent, delivered, bounced, complained, opened, clicked, unsubscribed, campaign started/completed/failed.

The deployment key fingerprint is `SHA256:UqRuMHXxxtSFH4evhm+GP5Qp1DNaPLpU3nYf+RfgOQA`. The `klyrow-deploy` account is installed. The private address currently presents an SSH host key different from the verified public host and must not be trusted until the vSwitch/provider conflict is corrected; management temporarily uses the verified public SSH endpoint. Never copy the private key into Git.

Middleware calls Klyrow at `http://10.40.0.2:18000`, with `Authorization: Bearer ...`, `X-Klyrow-Tenant-Id`, and an `Idempotency-Key`. Available private operations include `/v1/email/send`, `/v1/email/bulk`, `/v1/campaigns`, `/v1/messages/:id`, `/v1/campaigns/:id`, and `/v1/health`. The firewall permits port 18000 only from `10.40.0.1`; the same port is not publicly bound.

Klyrow events enter middleware at `/api/v1/klyrow/events`; dedicated paths also exist for campaigns, contacts, bounces, complaints, and unsubscribes. Middleware validates and normalizes before invoking its Odoo service layer or internal n8n events. Klyrow never accesses Odoo PostgreSQL or arbitrary public n8n webhooks. At deployment time Odoo writes and n8n delivery remain explicitly disabled in middleware; enable them only after approved credentials and workflow targets are installed, then re-run the controlled contact/event tests.

Retries use bounded exponential backoff in the event delivery layer; receivers must return the prior resource for the same idempotency key/body and reject reuse with a different body. Rotate the API key and HMAC secret independently: install new values on both ends, restart the two integration services, run signed/invalid/replay tests, then revoke the old values. Logs include system, event/message/campaign/customer IDs but never credentials or authorization headers.

## Synthetic downstream certification — 2026-08-16

The intended status path is `Postal/Klyrow -> middleware -> n8n -> Odoo`. Klyrow emits `klyrow.email.delivered` through `/api/v1/klyrow/events` and `klyrow.email.bounced` through `/api/v1/klyrow/bounces`. The canonical HMAC-SHA256 input is `timestamp + "\n" + event_id + "\n" + "klyrow" + "\n" + exact_canonical_json`; the request also carries the dedicated bearer identity, `X-Source-System`, timestamp, event-ID, and signature headers. Event, correlation, message, and tenant identifiers are fields in the canonical payload and must be preserved unchanged downstream.

One explicitly synthetic `klyrow.email.delivered` event was submitted without SMTP or Postal involvement. Middleware returned HTTP 202 with `accepted=true` and `duplicate=false`. Replaying the exact event ID, timestamp, signature, and body returned HTTP 409 `replayed event id`, proving ingress replay rejection. The event remained queued and the live aggregate showed no new delivered event. Existing aggregate state also contained 87 Klyrow dead letters. Direct inspection of n8n execution and Odoo ORM state was unavailable from the Klyrow host, and the existing deployment documentation says those downstream targets are disabled pending approved configuration. Therefore this evidence proves signed middleware ingress and idempotent replay rejection only; it does **not** prove n8n receipt, an Odoo status update, or real email delivery.

Synthetic evidence identifiers:

- event ID: `klyrow-synthetic-event-741589cc-192e-4225-a8ac-d5d186bfc682`
- correlation ID: `klyrow-synthetic-e2e-9e0c9532-8380-454e-a08a-d993716b7145`
- message ID: `synthetic-message-de9da9cc-b998-4dc5-b691-3978a2186de2`
- ingress timestamp: `1786855683`
- initial response: HTTP 202, accepted, duplicate false
- exact replay response: HTTP 409, replay rejected

No safe synthetic-only downstream failure switch was identified, so retry injection was not run. Bounce mapping was not submitted because the delivery event already established that downstream certification is blocked before n8n; adding another live synthetic event would only add queue/DLQ state without proving a second mapping.
