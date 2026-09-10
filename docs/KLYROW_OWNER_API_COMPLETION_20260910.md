# Platform-owner API completion — issues #21 and #22

## Baseline and requirement audit

Repository: appolon1908-hue/klyrow.com  
Starting source: 40866af8db9567a1f89ae44f1ce22ead9d52dbe7  
Branch: feat/platform-owner-certification-20260910

This is one owner-security completion change in the #21 implementation program.
It does not close the other product missions or certify production.

| Requirement | Before this change | Source after this change |
| --- | --- | --- |
| Exact owner issuer and subject for browser administration | IMPLEMENTED | Retained, with exact issuer comparison |
| Complete canonical mailbox configuration | PARTIAL: only an at-sign/length check | Complete mailbox syntax validation without external DNS calls |
| Canonical owner/MFA/freshness for bearer administration | MISSING | Required for every platform-admin bearer context, including resolver decisions |
| Resolver authorization | IMPLEMENTED | Preserved; additionally verifies the same signed token and local owner authority |
| Current role and identity during the handler transaction | PARTIAL: browser guard present | Bearer guard refreshes and locks user, membership and identity in compatible order |
| Owner verification API | MISSING | Read-only bearer and browser status APIs; no subject, mailbox or tokens in response |
| Privileged operation coverage | PARTIAL | Effective-route inventory and fresh-MFA denials across every existing administrative write |
| Owner recovery procedure | IMPLEMENTED documentation | Retained and updated to describe the current browser-bound step-up flow |
| Real owner binding, MFA enrollment and recovery rehearsal | MISSING runtime evidence | Remains a release blocker |

## API contract

- GET /v1/admin/security/platform-owner
- GET /app/api/admin/security/platform-owner

Both routes return only the successfully checked authority, issuer/subject
binding method, verified-mailbox/MFA/fresh-authentication flags and configured
authentication freshness limit. Responses use Cache-Control: no-store. They
do not assign roles, enroll factors, alter configuration or authorize a release.

The bearer endpoint requires a signed canonical OIDC token, a registered human
identity, an active local platform-admin user and platform-admin membership,
the exact configured owner, verified mailbox and fresh MFA. When a tenant
resolver is configured, its permission/tenant decision must pass first; the
gateway then independently verifies the same token and local owner mapping.
A resolver role alone, service identity, tenant API key or local HMAC session
cannot establish owner authority.

The browser endpoint uses the existing opaque-session, exact-owner and
transaction-bound role-stability guards. The existing /auth/step-up flow
remains the way to obtain fresh authentication for browser administration.

## Persistence, integration and rollback

No schema change or migration is needed: the change uses existing identity,
user and membership tables. The dedicated PostgreSQL regression exercises
concurrent role demotion against the request's shared authority locks.

No business state changes and no new domain events are introduced by the
status APIs. Existing command/audit/outbox handling stays in the owning
handlers. Existing HTTP status, request-ID, latency and error instrumentation
covers the new responses without identity labels.

Rollback is an application artifact rollback with the database unchanged.
An older artifact lacks the new bearer-owner gate. If rollback is necessary,
keep administrative bearer ingress unavailable until equivalent reviewed
protection is restored; the browser owner boundary remains independently
protected. Do not remove owner binding or MFA to regain access.

## Runtime readback, 2026-09-10

A read-only inspection of klyrow-gateway-1 on 37.27.128.39 found:

- KLYROW_PLATFORM_OWNER_ISSUER: absent;
- KLYROW_PLATFORM_OWNER_SUBJECT: absent;
- KLYROW_PLATFORM_OWNER_EMAIL: absent;
- tenant resolver: configured;
- deployed source label: da9d85891a4e313748e309aed86662d6c03d26bb.

No owner subject or mailbox was inferred from that absence. The gateway was
not changed. Actual canonical identity verification, MFA enrollment,
browser/staging acceptance and an independent recovery rehearsal remain
necessary before issue #22 can close.

## Validation

The PR records final-source test and CI evidence. Coverage includes real RSA
signature validation against a test JWKS boundary, current database authority,
verified email, MFA/freshness, invalid configuration, service/legacy denial,
resolver composition, tenant mismatch, admin-write coverage, OpenAPI, and the
PostgreSQL concurrency contract. Business tests now use signed test identities
instead of legacy local-owner tokens.
