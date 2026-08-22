# Klyrow Delivery Events

Provider events include queued, sent, delivered, deferred, bounced, complained, failed, and inbound received. Postal signatures, timestamp windows, provider identity, event IDs, correlation, and tenant mapping are verified.

Events are persisted before delivery to Server A. Retries use bounded exponential backoff and dead-letter after eight attempts. Replay does not recreate delivery, usage, or suppression records. Delivery to Server A uses bearer/HMAC today; production mTLS egress must be configured before external event readiness is certified.
