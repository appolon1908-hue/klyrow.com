# Klyrow Email — Codestra Integration Fabric v2

## Authority

Klyrow owns email workspaces, memberships, sender domains, sender identities, templates, message streams, consent, suppression, Postal mappings, message state, delivery lifecycle, usage and deliverability. Postal and Mautic remain internal engines.

Klyrow does not own cross-platform identity, CRM truth, n8n state, or gateway policy. Middleware is the only cross-system write boundary.

## Communication path

```text
Odoo/product request -> Middleware policy -> Klyrow API -> Postal
Postal lifecycle event -> Klyrow durable inbox -> Klyrow state/outbox -> Middleware
n8n -> Middleware only -> Klyrow adapter
```

n8n receives no Postal administrator credential, Mautic credential, SMTP password, sender-domain secret, Keycloak token for a human user, or Klyrow database access.

## Security email

Keycloak SECURITY email uses the dedicated Klyrow SECURITY relay/worker path. It does not wait synchronously on Middleware, Odoo, n8n or Mautic. n8n may receive sanitized delivery-failure alerts after Klyrow has durably accepted and normalized the provider result, but it must never change Keycloak verification/reset state.

## Email facade

The public and service API supports:

- domains and DNS verification;
- sender identities and approval;
- templates and preview;
- transactional/CRM message submission and status;
- campaign readiness and scheduling requests;
- suppressions and preferences;
- inbound email and quarantine state;
- lifecycle events, usage and deliverability.

Every send request requires an exact tenant, approved stream, authorized sender, verified domain, consent/suppression evaluation, quota, idempotency, and durable outbox. A timeout is an unknown submission outcome and must be reconciled before retry.

## Streams

```text
SECURITY
TRANSACTIONAL
CRM
MARKETING
BULK
```

Credentials, rate limits, policy and reputation controls are stream-specific. SECURITY credentials cannot send marketing or bulk mail.

## Capability defaults

```text
EMAIL_DELIVERY=false
EMAIL_CAMPAIGN_SEND=false
EMAIL_INBOUND_WRITEBACK=false
ODOO_WRITE=false
DEAD_LETTER_REPLAY=false
```

## Branch program

```text
feat/klyrow-postal-provisioning
  -> integration/codestra-email-fabric-v2
       -> integration/middleware-email-api-v1
       -> automation/email-event-outbox-v1
       -> feature/email-domain-sender-policy-v1
       -> feature/email-consent-suppression-v1
       -> feature/email-inbound-triage-v1
       -> test/email-fabric-contracts-v1
```

No branch activates live email or changes Postal, Mautic, DNS, DKIM, Keycloak, Caddy or production runtime.