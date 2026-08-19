# Developer API and webhooks

All product APIs use `/v1` and bearer authentication. Email and campaign writes require `Idempotency-Key`; reuse with different content returns conflict. Every response includes `X-Request-Id`. OpenAPI is served at `/v1/developer/openapi.json`.

Key resources include profiles/timelines, event ingestion, consent/preferences, segments/preview, journeys/lifecycle/runs, safe email submission/status/events, deliverability checks, analytics, onboarding, MFA/sessions, and admin operations. P1 foundations live under experiments, integrations, AI and billing. Raw Mautic and Postal admin APIs are not the commercial surface.

Postal inbound webhooks sign `timestamp + "." + event_id + "." + exact_body` with HMAC-SHA256. Middleware outbound events sign `timestamp + "\n" + event_id + "\nklyrow\n" + canonical_json`, use bearer service authentication and fail fast when middleware is unavailable. Event IDs are persisted to reject replay.

Safe mode returns an accepted message ID but never invokes Postal delivery. AI is unavailable unless an administrator explicitly configures and enables a provider; results always require human confirmation and never send.
