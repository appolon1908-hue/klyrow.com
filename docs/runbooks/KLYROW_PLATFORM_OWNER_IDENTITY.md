# Klyrow platform-owner identity

Issues: `klyrow.com#21`, `klyrow.com#22`, `klyrow.com#83`

## Security invariant

A Klyrow database role never grants platform-owner authority by itself. A
browser request made by a session that carries `platform_admin` must satisfy
both controls before any `/app/api/` handler runs:

1. Klyrow authorization data already identifies the session, user or active
   tenant membership as `platform_admin`; and
2. the active Keycloak identity is the exact configured `(issuer, subject)`
   pair, with the configured mailbox verified, MFA present and authentication
   no older than the configured freshness window.

Email is secondary evidence only. Matching an email address cannot create,
retain or recover platform-owner authority. Exact identity is an additional
gate and never self-promotes an account.

The browser-wide `/app/api/` boundary deliberately exceeds the current admin
path list so credits, payment confirmation, entitlement overrides, suspension,
role elevation, sync-conflict overrides, replay and future browser-owner
operations cannot escape the exact-owner check merely by using another path.
Each handler must still enforce its own operation-specific capability.

## Protected deployment values

Configure these values through the protected runtime environment. Do not put a
real subject, mailbox, token, password, private key or recovery code in Git:

```text
KLYROW_PLATFORM_OWNER_ISSUER=https://auth.codestra.co/realms/codestra
KLYROW_PLATFORM_OWNER_SUBJECT=<exact Keycloak sub>
KLYROW_PLATFORM_OWNER_EMAIL=<exact verified mailbox>
KLYROW_PLATFORM_OWNER_STEP_UP_MAX_AGE_SECONDS=300
KLYROW_PLATFORM_OWNER_REQUIRED_ACR_VALUES=
KLYROW_PLATFORM_OWNER_ACR_MFA_EVIDENCE_APPROVED=false
KLYROW_PLATFORM_OWNER_STEP_UP_ACR_VALUES=
```

The gateway fails closed with `503 platform_owner_not_configured` when a
platform administrator reaches a browser API before the complete exact binding
is present. A noncanonical issuer is rejected.

### MFA evidence

AMR evidence is accepted when Keycloak records either `mfa` or both a knowledge
factor (`pwd`/`pin`) and a possession factor such as TOTP or WebAuthn. An ACR
label is **not** MFA evidence by default.

ACR may be enabled only after protected evidence proves that each configured
label maps to an actual canonical-realm authentication flow that enforces the
required independent factors. Then set both values in the protected runtime:

```text
KLYROW_PLATFORM_OWNER_REQUIRED_ACR_VALUES=<reviewed exact labels>
KLYROW_PLATFORM_OWNER_ACR_MFA_EVIDENCE_APPROVED=true
```

Setting approval to true with an empty label list, or using any value other than
literal `true`/`false`, fails closed. Keep the approval false when realm mapping
is unknown or changes.

## Enrollment and verification

1. In the canonical Codestra realm, locate the intended owner account and copy
   its immutable user ID/`sub`. Do not derive it from email or username.
2. Confirm the exact mailbox is verified in Keycloak.
3. Enroll at least two independent MFA methods. Prefer two WebAuthn/FIDO2
   authenticators; retain a TOTP method only as a controlled fallback.
4. Confirm the realm emits reviewed AMR values. If ACR will be used, capture the
   realm flow mapping and approval separately before enabling ACR evidence.
5. Put the binding values into protected Klyrow deployment configuration, not
   `.env` in a checkout.
6. Assign `platform_admin` through the controlled Klyrow authorization process.
   Exact identity matching does not grant the role.
7. Verify fail-closed behavior for blank configuration, wrong subject, wrong
   issuer, matching email with wrong subject, unverified email, password without
   a second factor, unapproved ACR-only tokens, stale `auth_time`, expired token,
   disabled Klyrow user, and disabled/mismatched OIDC identity.

Only sanitized result codes may be captured as evidence. Do not record ID
tokens, access tokens, cookies, credentials or recovery codes.

## Step-up prerequisite

`/auth/step-up` intentionally returns
`503 platform_owner_step_up_flow_binding_required` in this foundation. Starting
a fresh authorization transaction before it is bound to the initiating browser
would leave it open to login-CSRF/session-swap attacks.

Issue #83 must first add the secure, host-only
`__Host-klyrow_oidc_flow` binding with one-time state, PKCE, nonce, origin/host,
expiry, replay, concurrent-tab and successful-clear coverage. After that lands,
a focused PR may enable the fresh-login redirect and configure only realm-
evidenced ACR values.

## Recovery / break glass

- Recovery changes the Keycloak factor set; it does not change the configured
  subject and does not grant a role by email.
- Require two-person approval, an incident/change record, a bounded maintenance
  window and immediate audit review.
- Use an offline recovery method held outside the application host. Rotate any
  exposed factor, revoke all browser sessions, perform a fresh authentication
  and verify the exact subject before restoring access.
- If the owner account must be replaced, treat it as a protected deployment
  change: record the old and new subjects, revoke the old account and sessions,
  update the protected binding, test fail-closed negatives, and rehearse
  rollback. Never keep two active platform-owner subjects.

## Activation boundary

Source merge does not activate the owner. Real subject/mailbox values remain
blank in Git, the step-up redirect remains disabled, and issue #22 remains open
until protected staging proves the exact identity, MFA/step-up behavior,
recovery procedure, all browser and non-browser privileged-operation coverage,
and redacted evidence. No production effect follows from merging this source.
