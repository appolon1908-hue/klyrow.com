# Klyrow Provider API

The versioned API is rooted at `/v1/internal/email`. It provides `send`, `preflight`, message readback, suppression checks, domain registration/DNS checks, DKIM rotation, sender management, SMTP credential lifecycle, inbound receipt, webhook tests, reputation status, and restricted operations.

Ingress requires the private mTLS boundary plus Server A machine authorization. Mutations require correlation and idempotency where applicable. `/healthz`, `/readyz`, and `/version` expose non-secret status. Error responses do not disclose foreign tenant resources.
