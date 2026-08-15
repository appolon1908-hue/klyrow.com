# Middleware integration

Klyrow uses the private vSwitch (`10.40.0.2:18000` to `10.40.0.1:8095`) and dedicated `KLYROW_MIDDLEWARE_API_KEY` and `KLYROW_WEBHOOK_SECRET`. Never reuse Kyqra/Telnexa credentials.

Sign the exact request body with HMAC-SHA256 over `timestamp + "\n" + event_id + "\n" + "klyrow" + "\n" + body`. Send `Authorization: Bearer <KLYROW_MIDDLEWARE_API_KEY>`, `X-Source-System: klyrow`, `X-Klyrow-Timestamp`, `X-Klyrow-Event-Id`, and `X-Klyrow-Signature: sha256=<lowercase hex>`. The receiver rejects timestamps outside five minutes, uses constant-time comparison, and persists event IDs to reject replay. Supported event names include queued, sent, delivered, bounced, complained, opened, clicked, unsubscribed, campaign started/completed/failed.

The deployment key fingerprint is `SHA256:UqRuMHXxxtSFH4evhm+GP5Qp1DNaPLpU3nYf+RfgOQA`. The `klyrow-deploy` account is installed. The private address currently presents an SSH host key different from the verified public host and must not be trusted until the vSwitch/provider conflict is corrected; management temporarily uses the verified public SSH endpoint. Never copy the private key into Git.
