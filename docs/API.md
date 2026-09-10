# Developer API and webhooks

All product APIs use `/v1` and bearer authentication. Email and campaign writes require `Idempotency-Key`; reuse with different content returns conflict. Every response includes `X-Request-Id`. OpenAPI is served at `/v1/developer/openapi.json`.

Key resources include profiles/timelines, event ingestion, consent/preferences, segments/preview, journeys/lifecycle/runs, safe email submission/status/events, deliverability checks, analytics, onboarding, MFA/sessions, and admin operations. P1 foundations live under experiments, integrations, AI and billing. Raw Mautic and Postal admin APIs are not the commercial surface.

Postal inbound webhooks sign `timestamp + "." + event_id + "." + exact_body` with HMAC-SHA256. Middleware outbound events sign `timestamp + "\n" + event_id + "\nklyrow\n" + canonical_json`, use bearer service authentication and fail fast when middleware is unavailable. Event IDs are persisted to reject replay.

Safe mode returns an accepted message ID but never invokes Postal delivery. AI is unavailable unless an administrator explicitly configures and enables a provider; results always require human confirmation and never send.

Reference clients are maintained in `sdk/python/klyrow.py` and `sdk/typescript/src/index.ts`. Both add bearer authentication, optional organization context, idempotency keys, structured error handling, message pagination, and webhook verification. They intentionally accept tokens or provider references only; neither client handles nor stores raw payment-card data.

## Platform-owner authority

`GET /v1/admin/security/platform-owner` and
`GET /app/api/admin/security/platform-owner` provide a redacted readback of
the current caller's verified owner authority. They do not grant access or
activate production. Both require exact owner identity, current Klyrow
authorization, verified mailbox and fresh MFA; responses are not cacheable.

Platform-admin bearer requests require canonical signed OIDC proof even when
a tenant resolver authorizes the request. A resolver role, API key, service
identity or legacy local HMAC session cannot substitute for that proof.
Other tenant and service permissions keep their existing contracts.

See [the owner API contract and acceptance record](KLYROW_OWNER_API_COMPLETION_20260910.md)
and [owner enrollment/recovery](runbooks/KLYROW_PLATFORM_OWNER_IDENTITY.md).
