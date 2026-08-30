# 4. Keycloak requirements

## 4.1 Klyrow application client

Create or update a dedicated OIDC client, conceptually named:

```text
klyrow-web
```

Required client behavior:

- Authorization Code flow enabled.
- PKCE method restricted to S256.
- Implicit flow disabled.
- Direct Access Grants disabled.
- Device flow disabled unless separately approved.
- Exact redirect URI allowlist; do not use broad wildcards.
- Exact post-logout redirect URI allowlist.
- Exact web origins; do not use `*`.
- Client authentication enabled for a confidential BFF.
- Client secret stored only in the server-side secret store.
- Scopes limited to `openid profile email` plus explicitly approved Klyrow roles/tenant claims.
- Require email verification for local email/password registration.
- Keep existing required actions such as `VERIFY_EMAIL`, `UPDATE_PASSWORD`, and `CONFIGURE_TOTP` according to the deployed policy; do not remove them.
- Brute-force detection enabled.
- A production password policy enabled.
- Terms and Conditions required action enabled for new users.

Use `prompt=create` on the standard authorization endpoint when `/signup` should open registration directly. Do not use the deprecated `/registrations` path for new implementation.

## 4.2 Google identity provider

Configure Google in Keycloak, not directly in the Klyrow frontend.

Required settings:

```text
Alias: google
Enabled: true
Default scopes: openid profile email
Store Tokens: false
Stored Tokens Readable: false
Hosted Domain: blank unless a future policy intentionally restricts sign-in
```

In Google Cloud, use the exact Redirect URI displayed by Keycloak. Do not guess or manually construct it in code.

Account-linking requirements:

- Do not auto-link an existing local account solely because an unverified email string matches.
- Require a safe first-broker-login flow that confirms or re-authenticates the existing account before linking.
- Never manually set `emailVerified=true` in application code.
- Only rely on verification state produced and validated by Keycloak's configured identity flow.
- Do not request Gmail, Drive, Contacts, Calendar, or other Google API scopes. Klyrow needs identity scopes only.
- Do not persist Google access or refresh tokens because the product does not need to call Google APIs.

The Google button may initiate the same OIDC authorization request with an identity-provider hint for alias `google`; it must still include state, nonce, PKCE, and the normal callback validation.

## 4.3 Klyrow Keycloak theme

Build a version-controlled Klyrow login/email theme compatible with the deployed Keycloak version.

Do not assume the parent theme name. Inspect the deployed Keycloak image/version and extend its supported base login theme.

Theme must cover:

- login
- registration
- password reset request
- password reset completion
- email verification notice
- resend verification
- terms and conditions
- OTP/TOTP setup
- required-action pages
- identity-provider linking/confirmation
- expired action link
- general error
- logout confirmation/success, if enabled

Add English and Spanish message bundles. Keep strings out of templates where Keycloak localization supports message keys.

Do not fork or rewrite Keycloak's authentication engine. Override presentation and approved flow configuration only.

---

# 5. BFF/API contract

Adapt names to the existing repository, but preserve the behavior below.

## 5.1 Public routes

```http
GET  /auth/login?return_to=/app
GET  /auth/signup?return_to=/onboarding
GET  /auth/google?return_to=/app
GET  /auth/callback
POST /auth/logout
GET  /auth/session
```

Optional authenticated route:

```http
POST /auth/logout-all
```

All `return_to` values must be relative paths from a strict allowlist. Reject scheme-relative URLs, encoded absolute URLs, backslashes, control characters, and host changes.

## 5.2 `GET /auth/login`

- Create pre-auth state.
- Generate PKCE verifier/challenge with S256.
- Generate nonce.
- Persist the verifier, state, nonce, creation time, and allowlisted `return_to` server-side.
- Redirect to Keycloak authorization endpoint.

## 5.3 `GET /auth/signup`

Same requirements as login, plus request direct registration using the supported `prompt=create` authorization parameter.

## 5.4 `GET /auth/google`

Same requirements as login, plus request the configured Google identity provider through Keycloak.

Do not redirect directly to Google from Klyrow.

## 5.5 `GET /auth/callback`

Required sequence:

1. Reject missing or mismatched `state`.
2. Reject expired or already-consumed pre-auth sessions.
3. Exchange authorization code server-side using the exact redirect URI and PKCE verifier.
4. Validate ID/access token signature using cached JWKS with safe key rotation.
5. Validate exact issuer.
6. Validate audience and authorized party/client.
7. Validate expiration, not-before, nonce, and token type.
8. Require the needed identity claims.
9. Upsert Klyrow user by `(issuer, subject)`.
10. Apply email-verification policy.
11. Resolve invite or create initial workspace idempotently.
12. Create application session and rotate session ID.
13. Record an authentication audit event without token contents.
14. Mark the pre-auth record consumed.
15. Redirect to the saved allowlisted relative path.

The callback must be replay-safe and idempotent around application bootstrap.

## 5.6 `GET /auth/session`

Return only the minimum UI session view:

```json
{
  "authenticated": true,
  "user": {
    "id": "application-user-id",
    "email": "user@example.com",
    "emailVerified": true,
    "displayName": "Example User"
  },
  "workspace": {
    "id": "workspace-id",
    "name": "Example Workspace",
    "role": "owner",
    "provisioningStatus": "ready"
  },
  "csrfToken": "opaque-csrf-token"
}
```

Do not return raw OIDC tokens or Postal credentials.

## 5.7 `POST /auth/logout`

Required sequence:

1. Validate CSRF.
2. Load the server-side application session.
3. Mark the local session revoked.
4. Revoke refresh token when supported.
5. Clear `__Host-klyrow_session` using matching cookie attributes.
6. Redirect through Keycloak's OIDC logout/end-session flow using the stored ID-token hint when appropriate.
7. Use only the pre-registered post-logout redirect URI.
8. Record an audit event.

The endpoint must be safe to repeat and must not fail just because the local session has already expired.

## 5.8 `POST /auth/logout-all`

- Require recent re-authentication or MFA for high-risk accounts.
- Revoke all Klyrow sessions for the user.
- Terminate the corresponding Keycloak user sessions through an approved server-side integration.
- Never expose Keycloak administrative credentials to the browser.

---
