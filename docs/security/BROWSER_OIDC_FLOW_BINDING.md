# Klyrow browser OIDC flow-binding and invitation-authority contract

Status: source implementation candidate for issue #83  
Runtime activation: **not authorized**

## Security boundary

Every browser-initiated OpenID Connect transaction is bound to the browser
that started it. Each newly started transaction receives an authoritative,
state-specific host-only cookie named:

```text
__Host-klyrow_oidc_flow-<sha256(state)>
```

The cookie name contains only a SHA-256 digest, never the unpredictable state
itself. Its value is a domain-separated HMAC of that state. Each exact cookie
is `Secure`, `HttpOnly`, `SameSite=Lax`, has path `/`, has no `Domain`
attribute, and expires no later than the corresponding server-side
transaction.

The root path is intentional. The `__Host-` prefix requires `Secure`, no
`Domain` attribute, and `Path=/`; a narrower path would cause conforming
browsers to reject the cookie instead of enforcing the host boundary.

One authoritative cookie per transaction prevents response-order races. A
callback that started before a newer tab can delete only its own cookie name;
it cannot rewrite or expire the newer tab's binding.

## Bounded rollout compatibility

During the transition from the historical shared cookie, a new flow also emits
a capped, short-lived `__Host-klyrow_oidc_flow` compatibility mirror. It uses
the same HMAC bindings and flow TTL and retains at most eight live bindings.
This allows transactions and clients that straddle the application update to
complete without losing browser binding.

The compatibility mirror is deliberately non-authoritative whenever the exact
state-specific cookie is present:

- an incorrect exact cookie is rejected even when the shared mirror contains a
  matching value;
- callbacks for new flows delete only the exact per-state cookie and leave the
  shared mirror to expire naturally;
- an older callback response therefore cannot delete a newer flow's exact
  binding;
- requests that contain no exact cookie may use the mirror only while their
  existing server-side transaction remains live and unused.

A later, separately reviewed cleanup may stop emitting the mirror after the
maximum rollout window has elapsed. Its removal is not required for the race
fix and must not strand in-flight transactions.

The callback validates the canonical browser host, server-side state,
expiration, exact browser binding, callback prerequisites, authorization-code
exchange, PKCE, ID-token issuer/audience/signature, and nonce **before**
atomically consuming the one-time transaction.

The compare-and-set that consumes state is evaluated by the database with ORM
session synchronization disabled. This preserves one-row atomicity on
PostgreSQL and avoids Python-side comparison between timezone-aware bound
values and SQLite's naive test representation.

## Safe failure behavior

| Condition | Result | State and cookie behavior |
|---|---|---|
| Missing or wrong exact cookie and no valid mirror | `403 oidc_flow_cookie_mismatch` | Transaction remains unused; no session is created |
| Incorrect exact cookie with matching mirror | `403 oidc_flow_cookie_mismatch` | Exact binding wins; no fallback |
| Unknown or already-used state | `410 oidc_state_invalid_or_used` | No new mutation |
| Expired state | `410 oidc_state_expired` | Transaction remains unused |
| Code exchange, PKCE, token, or nonce failure | Existing fail-closed error | Transaction remains unused |
| Provider cancellation or failed required action | Redirect to `/service-error` | Transaction is consumed once; its exact cookie is cleared |
| Successful callback | Opaque browser session and safe local redirect | Transaction is consumed once; its exact cookie is cleared |
| Concurrent tabs | Each live transaction has its own exact cookie | Callback response ordering cannot invalidate another tab |
| Replay after success or terminal cancellation | `410 oidc_state_invalid_or_used` | No session duplication |

Recovery, password update, email verification, invitation acceptance, normal
login/signup/Google login, and platform-owner step-up all use the same binding.

## Platform-owner step-up identity

Step-up proves freshness for the browser session that initiated it. The
initiating session is selected with `FOR UPDATE`, and its replacement session
and parent revocation are committed atomically. One parent session can
therefore produce at most one successful replacement even when two callbacks
arrive concurrently.

After the new ID token passes issuer, audience, signature, nonce, and browser-
flow checks, Klyrow resolves only:

- the unrevoked, unexpired initiating browser session;
- the exact already-enabled `(issuer, subject)` identity bound to that session;
- the same enabled Klyrow user;
- the same active tenant membership and enabled tenant.

A missing or different Keycloak subject returns
`403 step_up_identity_mismatch`. Disabled users, inactive memberships,
suspended tenants, expired sessions, and revoked sessions fail closed with
sanitized errors. The step-up resolver never calls first-login identity
creation, starter-workspace creation, invitation auto-selection, Postal
provisioning, or any other account-provisioning path.

## Invitation authority

The selected invitation ID is stored inside the bound OIDC transaction.
Acceptance revalidates the exact invitation, verified email, expiry,
revocation status, tenant availability, and target membership under row locks.

- No membership: create the invited role.
- Inactive membership: explicitly reactivate it with the invited role.
- Active membership with the same role: accept without changing authority.
- Active membership with a different role: return
  `409 invitation_existing_member_role_change_denied`; preserve the membership
  and leave the invitation unaccepted.
- Expired, revoked, already accepted, wrong-email, or unavailable-tenant
  invitations fail closed.
- A token selects one invitation exactly; multiple other invitations for the
  same mailbox do not alter selection.

The legacy token-acceptance endpoint applies the same active-role stability
rule so it cannot bypass the browser control.

## Browser send capability

`POST /app/api/email/send` checks the current membership role against the
existing central `ROLE_PERMISSIONS` map and requires `mail.send` (or the
existing `*` owner capability) before calling the canonical send path.

The existing browser-session, same-transaction role lock, tenant isolation,
CSRF, idempotency, sender/domain policy, suppression/consent, canary, outbox,
and fail-closed delivery controls remain unchanged.

## Test isolation

The browser-security tests use `https://app.klyrow.test` as a development
origin. A repository-level autouse fixture scopes that value to the relevant
test module and removes it before unrelated tests. This prevents collection-
time environment state from changing the canonical logout-origin assertion.

## Authentication assets

The historical residual also changed `/auth-assets`. Current protected source
already mounts the built web distribution root, and the edge/image contract
owns that behavior. This implementation intentionally makes **no asset-path
change** without new runtime/image evidence.

## Release gates

Before merge:

1. migrations must apply twice;
2. backend, browser, frontend, and Playwright suites must pass;
3. OpenAPI, dependency, secret, and source-readiness checks must pass;
4. every immutable image build and HIGH/CRITICAL scan must pass;
5. SBOM, provenance, source labels, and reproducibility checks must pass;
6. all review threads must be resolved against the final exact head;
7. a fresh independent approval must certify the final exact head.

This source change does not configure Keycloak, activate an owner, mutate a
runtime database, enable Postal/Mautic, enable customer email, publish images,
change DNS/TLS, deploy a server, or authorize production traffic.
