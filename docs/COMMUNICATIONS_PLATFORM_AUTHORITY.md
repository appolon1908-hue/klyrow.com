# Communications Platform Email Authority

`appolon1908-hue/klyrow.com` is the principal email runtime authority for the Codestra communications platform.

## Klyrow owns

- Postal and Mautic runtime integration;
- tenant-isolated email operations;
- sender/domain onboarding;
- DKIM signing and email-domain configuration state;
- SMTP/API submission into the email runtime;
- templates/campaign execution that belongs to Klyrow/Mautic;
- message/provider IDs and delivery-state read-back;
- bounces, complaints and delivery events;
- suppressions and email preference enforcement where email-specific;
- email quotas and usage;
- deliverability/reputation data available from the email runtime;
- safe-mode and production-send gating;
- email-provider health and reconciliation;
- email-specific operator tooling.

Klyrow does not own the public cross-system API gateway, global identity system, cross-system command ledger or developer SDK authority.

## Required architecture

```text
Application
  -> SDK-repository client
  -> Caddy/Kong
  -> Middleware
  -> Klyrow governed API/adapter boundary
  -> Postal/Mautic

Postal/Klyrow events
  -> signed/private callback ingress
  -> Middleware durable event boundary
  -> canonical events
  -> SDK webhooks / dashboards / n8n / business consumers
```

## Related authorities

- `communication-platform-` — communications architecture/coordination
- `SDK-repository` — public/developer contracts and SDKs
- `Middleware-` — privileged command/idempotency/reconciliation authority
- `Kong` — gateway/security authority
- `Keycloak` — identity authority
- `Caddy` — TLS edge authority
- `Infustruction-repo` — shared infrastructure/deployment topology

## Provider boundary rule

Postal and Mautic administration APIs must not become the public Codestra communications API. Public/product-facing callers use the Codestra SDK and Middleware-governed contracts. Klyrow exposes only the restricted/provider contract necessary for Middleware and Klyrow-owned UI/operator functions.

## Email capability inventory target

The Klyrow contract should explicitly cover and test:

- transactional send;
- batch/bulk submission where supported;
- scheduling/cancellation semantics where supported;
- sender identity and domain verification;
- SPF/DKIM/DMARC status reporting where Klyrow can authoritatively observe it;
- templates and personalization;
- attachments and size limits;
- message status/read-back;
- bounces and bounce classification;
- complaints;
- suppressions;
- consent/preferences;
- inbound/reply handling where supported;
- webhook/delivery events;
- quotas/usage;
- deliverability/reputation snapshots;
- provider readiness/health;
- safe-mode/production gate state;
- reconciliation by provider/message identity.

If a capability is not owned or supported by Klyrow, the contract must say so rather than emulate it in another repository.

## Status mapping

Klyrow provider states must map deterministically into canonical communications states without discarding the original provider status/detail.

Canonical examples:

```text
accepted
queued
submitted
provider_accepted
delivered
bounced
complained
suppressed
failed
indeterminate
```

## Domain and deliverability model

Domain onboarding/reporting should distinguish:

- DNS record expected value;
- observed DNS state;
- SPF alignment/status;
- DKIM selector/status;
- DMARC status/policy;
- MX status where relevant;
- PTR/rDNS status where Klyrow can verify it;
- TLS capability;
- sending enabled/disabled state;
- safe mode;
- reputation/deliverability signals;
- BIMI/VMC readiness as informational state only unless separately implemented.

Never expose private DKIM keys or provider credentials through public APIs or dashboards.

## Webhook/event requirements

Outbound Klyrow events consumed by Middleware must support tenant binding, correlation IDs, stable event/message identifiers, authentication/signature verification, timestamp/replay defense and deterministic retry behavior.

## Production rule

No documentation or SDK integration may disable `KLYROW_SAFE_MODE` or equivalent production gates. Production sending activation remains a separately reviewed operational decision with DNS, abuse, provider, backup and monitoring evidence.
