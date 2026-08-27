# Developer API and webhooks

All product APIs use `/v1` and bearer authentication. Email and campaign writes require `Idempotency-Key`; reuse with different content returns conflict. Every response includes `X-Request-Id`. OpenAPI is served at `/v1/developer/openapi.json`.

Key resources include profiles/timelines, event ingestion, consent/preferences, segments/preview, journeys/lifecycle/runs, safe email submission/status/events, deliverability checks, analytics, onboarding, MFA/sessions, and admin operations. P1 foundations live under experiments, integrations, AI and billing. Raw Mautic and Postal admin APIs are not the commercial surface.

Postal inbound webhooks sign `timestamp + "." + event_id + "." + exact_body` with HMAC-SHA256. Middleware outbound events sign `timestamp + "\n" + event_id + "\nklyrow\n" + canonical_json`, use bearer service authentication and fail fast when middleware is unavailable. Event IDs are persisted to reject replay.

Safe mode returns an accepted message ID but never invokes Postal delivery. AI is unavailable unless an administrator explicitly configures and enables a provider; results always require human confirmation and never send.

Reference clients are maintained in `sdk/python/klyrow.py` and `sdk/typescript/src/index.ts`. Both add bearer authentication, optional organization context, idempotency keys, structured error handling, message pagination, and webhook verification. They intentionally accept tokens or provider references only; neither client handles nor stores raw payment-card data.

## Production mail operations

| Purpose | Method and URL | Authority |
|---|---|---|
| Tenant readiness checks 1–10 | `GET /v1/mail/readiness` | authenticated tenant |
| Global or selected-tenant readiness | `GET /v1/admin/mail/readiness?tenant_id=...` | platform admin |
| Corporate role-address matrix | `GET /v1/mail/role-addresses` | authenticated tenant |
| Idempotent role provisioning | `POST /v1/admin/mail/role-addresses/provision` | platform admin |
| Attested route activation/deactivation | `POST /v1/admin/mail/inbound-routes/{id}/activate|deactivate` | platform admin |
| Provider inbox list/detail | `GET /v1/internal/email/inbound/messages[/{id}]` | authenticated tenant |
| Native Postal route delivery | `POST /v1/webhooks/postal-inbound` | Postal RSA signature |
| Provider-domain activation | `POST /v1/admin/mail/provider-domains/{id}/activate` | platform admin |
| Campaign-domain activation | `POST /v1/admin/mail/campaign-domains/{id}/activate` | platform admin |
| Tracking and placement summary | `GET /v1/mail/tracking/summary` | authenticated tenant |
| Gmail seed mailbox registration/list | `POST|GET /v1/mail/seed-mailboxes` | tenant manager / tenant |
| Connector placement result | `POST /v1/mail/placement-checks` | authenticated connector |
| Live Gmail placement lookup | `POST /v1/mail/placement-checks/run` | tenant manager or scoped service |

Klyrow-issued API keys use `Authorization: Bearer kly_live_...`. Service accounts use `Authorization: Bearer klys_...` together with `X-Klyrow-Client-Id`. The server derives the required scope from the route; a client-provided scope header is never trusted. The relevant scopes are `mail.send`, `mail.read`, `domain.read`, `domain.manage`, `sender.manage`, `template.manage`, `campaign.manage`, `webhook.manage`, `analytics.read`, and billing scopes.

Postal webhook ingress acknowledges with HTTP 202 once the signed event is durably stored. Failure of the middleware callback changes the local event to `retry`; Klyrow's own worker retries it. Postal is not asked to redeliver an already persisted event.
