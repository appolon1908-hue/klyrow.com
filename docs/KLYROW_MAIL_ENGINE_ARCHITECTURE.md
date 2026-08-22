# Klyrow Mail Engine Architecture

Server A is authoritative for identity, tenant, permission, entitlement, consent, and billing decisions. The private mTLS ingress on `10.40.0.4:18000` admits its machine identity; the gateway resolves the bearer through Server A and rejects client-supplied tenant authority. The provider API applies domain, sender, stream, suppression, quota, warm-up, reputation, size, sandbox, and idempotency policy before persisting work.

Sandbox messages move through `QUEUED → PROCESSING → DELIVERED` into a private capture store. Provider events and Klyrow billing-usage events are separate durable outboxes. Postal remains the external transport engine; provider acceptance never means delivery. PostgreSQL holds governed metadata, RabbitMQ remains Postal-owned, and no Klyrow usage enters Telnexa billing.

Telnexa, Jasmin, SMPP, SMS workers, and Telnexa billing are outside this stack's mutation boundary.
