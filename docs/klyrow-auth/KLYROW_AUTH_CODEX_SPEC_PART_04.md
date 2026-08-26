# 8. Security requirements

The implementation is not complete unless all of these are satisfied:

- Exact OIDC issuer validation.
- RS256/JWKS signature validation using a maintained OIDC library.
- Audience and authorized-party validation.
- State, nonce, and PKCE S256 validation.
- One-time callback state consumption.
- Open-redirect prevention.
- Session fixation prevention.
- Secure, HttpOnly, SameSite cookie.
- CSRF protection for cookie-authenticated writes.
- No browser token persistence.
- No direct password grant.
- No secret in source, logs, exceptions, client bundles, or build output.
- Generic login/reset errors that prevent account enumeration.
- Brute-force/rate-limit controls.
- Email verification gate.
- Safe Google identity linking.
- Tenant authorization on every workspace-scoped operation.
- Audit events without sensitive values.
- Content Security Policy and clickjacking protection.
- HSTS at the TLS edge.
- Referrer policy that does not leak authentication query parameters.
- `Cache-Control: no-store` on authentication pages and responses.
- Dependency audit and secret scan in CI.
- No production deployment from this implementation task.

---

# 9. Accessibility requirements

Meet WCAG 2.2 AA for the authentication journey:

- Every input has a visible label.
- Error messages are associated with the relevant field.
- Use `aria-live` for async status messages.
- Keyboard order follows the visual order.
- Focus is visible and never removed.
- Google button has an accessible text label, not icon-only content.
- Password visibility control announces its state.
- Do not rely on color alone for errors or success.
- Minimum 44px interactive target height.
- Support 200% zoom without loss of content or horizontal scrolling at standard mobile widths.
- Respect reduced-motion preferences.
- Use semantic headings and landmarks.

---

# 10. Test requirements

## 10.1 Unit tests

Cover at minimum:

- PKCE verifier/challenge generation.
- State and nonce validation.
- Expired and consumed pre-auth sessions.
- Exact issuer validation.
- Audience/authorized-party validation.
- `return_to` allowlist and open-redirect attacks.
- Session-cookie attributes.
- CSRF validation.
- User upsert keyed by `(issuer, subject)`.
- First-login workspace bootstrap idempotency.
- Invite acceptance versus new-workspace creation.
- Logout idempotency.
- Audit redaction.

## 10.2 Integration tests

Use a test Keycloak realm/container or a deterministic OIDC test provider.

Required scenarios:

1. Email signup → verification required → verified login → workspace created.
2. Unverified email cannot enter the authenticated application.
3. Email/password login succeeds.
4. Incorrect credentials return a generic error.
5. Google first login creates or links the correct Keycloak identity and creates one Klyrow user.
6. Existing email account is not silently duplicated by Google sign-in.
7. Tampered state is rejected.
8. Wrong nonce is rejected.
9. Authorization-code replay is rejected.
10. Wrong issuer is rejected.
11. Wrong audience is rejected.
12. Logout revokes the local session, clears the cookie, and completes Keycloak logout.
13. Repeated logout is safe.
14. Postal provisioning failure leaves the identity/workspace valid in `provisioning` state and creates a retryable outbox event.
15. Cross-workspace access is denied.
16. CSRF attack is denied.

## 10.3 Browser tests

Use the repository's existing browser-test framework; otherwise use Playwright.

Test:

- desktop login
- mobile login
- signup
- Google-button redirect to Keycloak, using a controlled test provider in CI
- forgot password
- verify-email notice
- keyboard-only flow
- visible focus
- error announcements
- logged-out success banner
- session-expired redirect

Do not send live external email in ordinary CI. Capture SMTP locally or use a test mail sink. A controlled staging canary is a separate release step.

---

# 11. Implementation split

Deliver as separate reviewable changes rather than one unreviewable bundle.

## PR 1 — Klyrow authentication UI and Keycloak theme

Suggested branch:

```text
feat/klyrow-auth-theme-ui
```

Contents:

- Klyrow auth shell
- Keycloak login/email theme
- English and Spanish strings
- responsive/accessibility tests
- no backend session changes
- no deployment

## PR 2 — OIDC BFF session flow

Suggested branch:

```text
feat/klyrow-oidc-bff-session
```

Contents:

- login/signup/Google start routes
- callback validation
- secure server-side sessions
- logout and optional logout-all
- CSRF
- audit events
- tests and OpenAPI changes
- additive migration if required

## PR 3 — First-login tenant and Postal provisioning

Suggested branch:

```text
feat/klyrow-first-login-provisioning
```

Contents:

- user/workspace/membership bootstrap
- invite handling
- outbox event
- Postal provisioning adapter
- idempotent worker
- provisioning status UI
- tests

## PR 4 — Keycloak Google and optional Postal-admin OIDC configuration

Suggested branch:

```text
infra/klyrow-google-postal-oidc
```

Contents:

- declarative Keycloak client/identity-provider configuration
- secret names only, never secret values
- exact redirect/origin allowlists
- optional Postal admin OIDC configuration
- rollback instructions
- staging verification evidence
- no production activation

---
