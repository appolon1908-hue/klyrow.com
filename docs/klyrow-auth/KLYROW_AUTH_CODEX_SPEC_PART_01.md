# Klyrow.com SaaS Authentication and Onboarding

## Codex Implementation Specification

**Product:** Klyrow.com  
**Purpose:** Customer-facing authentication and first-login onboarding for a SaaS email-delivery platform  
**Mail engine:** Postal 3.3.7  
**Identity provider:** Existing Keycloak realm at `https://auth.codestra.co/realms/codestra`  
**Customer application:** `https://app.klyrow.com`  
**Public API ingress:** `https://api.codestra.co/v1/email/`  
**Status:** Implementation-ready specification. Do not deploy or activate production traffic as part of this task.

---

# 1. Product boundary

Klyrow is a SaaS email-delivery platform. Postal is the mail-delivery engine. Postal is not the public customer-registration authority.

Use these boundaries:

- **Keycloak** owns email/password registration, Google sign-in, email verification, password reset, MFA, identity linking, login sessions, and single logout.
- **Klyrow** owns workspaces, memberships, roles, onboarding, application sessions, tenant isolation, audit records, and Postal resource mappings.
- **Postal 3.3.7** owns message delivery, SMTP/API sending, delivery activity, domains, credentials, and related mail operations.
- The browser must never receive a Postal administrator credential, Keycloak client secret, Google client secret, Postal API secret, or SMTP password.
- Do not implement a custom password database in Klyrow.
- Do not use OAuth password grant or Keycloak Direct Access Grants.
- Do not modify Postal source code for this authentication feature.
- Do not write directly to Postal's database. Use a supported API or a dedicated provisioning adapter.

This scope assumes a SendGrid/Mailgun-style SaaS portal. It is not a Gmail-style IMAP mailbox or webmail implementation.

---

# 2. Required architecture

## 2.1 Browser authentication

Implement OpenID Connect Authorization Code flow with PKCE S256.

Preferred deployment pattern:

1. Browser visits `https://app.klyrow.com/login` or `/signup`.
2. Klyrow's same-origin BFF creates cryptographically random `state`, `nonce`, and PKCE verifier.
3. BFF stores those values in a short-lived server-side pre-auth session.
4. Browser is redirected to Keycloak.
5. Keycloak displays the Klyrow-branded login/registration theme.
6. Email/password authentication happens only on the Keycloak origin.
7. Google authentication is brokered by Keycloak using identity-provider alias `google`.
8. Keycloak returns an authorization code to `https://app.klyrow.com/auth/callback`.
9. The BFF validates `state`, exchanges the code using the original PKCE verifier, validates all tokens, creates the Klyrow application session, and redirects to an allowlisted relative path.
10. The browser receives only an opaque secure session cookie.

Do not store access tokens, ID tokens, or refresh tokens in `localStorage` or `sessionStorage`.

## 2.2 Session cookie

Use an opaque first-party cookie named:

```text
__Host-klyrow_session
```

Required attributes:

```text
Secure
HttpOnly
SameSite=Lax
Path=/
```

Additional requirements:

- Rotate the session identifier after login, privilege change, password change, MFA change, and account recovery.
- Store OIDC tokens server-side, encrypted at rest if persisted.
- Access-token lifetime must follow the existing short-lived Keycloak policy.
- Use refresh-token rotation and detect reuse where supported.
- Apply an idle timeout and an absolute session timeout from configuration, not hard-coded constants.
- Add `Cache-Control: no-store` to all authentication and session responses.
- Require CSRF protection for every cookie-authenticated state-changing request.

## 2.3 Canonical identity key

The immutable application identity is:

```text
(issuer, subject)
```

For this realm:

```text
issuer = https://auth.codestra.co/realms/codestra
subject = validated OIDC sub claim
```

Never use email address as the primary identity key. Email can change and can be shared across identity-provider transitions.

## 2.4 Postal integration

Postal does not become the public identity provider.

On first successful Klyrow login:

1. Upsert the Klyrow user using `(issuer, subject)`.
2. If the user has a valid pending invitation, join that workspace.
3. Otherwise, create a new Klyrow workspace and assign the user the `owner` role.
4. Write a provisioning request to the transactional outbox.
5. A background worker idempotently provisions or maps the corresponding Postal organization/resources.
6. Save only Postal identifiers and status in Klyrow's database.
7. If Postal is temporarily unavailable, login still succeeds and the workspace displays `Provisioning email workspace` until the worker completes.

Do not provision Postal synchronously inside the OIDC callback transaction.

---

# 3. Klyrow authentication UI

## 3.1 Visual direction

Use the current Klyrow brand tokens if they exist. If no design system exists, create tokens rather than scattering literal values.

Temporary fallback tokens:

```text
Background:     #F8FAFC
Surface:        #FFFFFF
Text primary:   #0F172A
Text secondary: #475569
Primary:        #4F46E5
Primary hover:  #4338CA
Border:         #E2E8F0
Success:        #15803D
Warning:        #B45309
Danger:         #B91C1C
Focus ring:     #818CF8
Radius card:    20px
Radius input:   10px
Card width:     420px to 460px
```

Typography should use the existing Klyrow typeface. Otherwise use a locally available modern sans-serif stack; do not add a font download dependency solely for this feature.

## 3.2 Desktop layout

Use a responsive two-column authentication shell.

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ KLYROW                                                                  │
│                                                                          │
│  Left brand panel, 42%                Right authentication area, 58%     │
│  ─────────────────────                ───────────────────────────────     │
│  Reliable email infrastructure        ┌────────────────────────────┐     │
│  built for growing teams.             │ Welcome back               │     │
│                                       │ Sign in to Klyrow          │     │
│  ✓ Send through SMTP or API           │                            │     │
│  ✓ Track delivery activity            │ [ G Continue with Google ] │     │
│  ✓ Manage domains and teams           │ ─────── or ─────────────── │     │
│                                       │ Email address              │     │
│  Small privacy/security note          │ Password             Show │     │
│                                       │ Keep signed in   Forgot?   │     │
│                                       │ [ Sign in ]                │     │
│                                       │ New? Create an account     │     │
│                                       └────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────┘
```

The card must remain vertically centered when practical, but the page must scroll naturally on smaller-height screens.

## 3.3 Mobile layout

At mobile widths:

- Hide the large left panel.
- Show the Klyrow logo, one-line value proposition, and authentication card in a single column.
- Use 20px page padding and full-width controls.
- Keep every tap target at least 44px high.
- Do not use modal login on mobile.

## 3.4 Login page copy

Heading:

```text
Welcome back
```

Supporting text:

```text
Sign in to manage your sending, domains, activity, and team.
```

Controls in order:

1. `Continue with Google`
2. Divider: `or continue with email`
3. `Email address`
4. `Password` with accessible show/hide control
5. `Keep me signed in`, only if the Keycloak realm policy enables Remember Me
6. `Forgot password?`
7. Primary button: `Sign in`
8. Footer: `New to Klyrow? Create an account`
9. Links: `Terms of Service` and `Privacy Policy`

## 3.5 Signup page copy

Heading:

```text
Create your Klyrow account
```

Supporting text:

```text
Start with one secure workspace for your email operations.
```

Controls in order:

1. `Continue with Google`
2. Divider: `or create an account with email`
3. `First name`
4. `Last name`
5. `Work email`
6. `Password`
7. `Confirm password`, if required by the current Keycloak registration policy
8. Required acceptance of Terms and Privacy Policy through the Keycloak registration flow/required action
9. Primary button: `Create account`
10. Footer: `Already have an account? Sign in`

Do not request a company/workspace name on this page. Collect it after identity verification during onboarding.

## 3.6 Verify-email page

Heading:

```text
Check your inbox
```

Body:

```text
We sent a verification link to {masked_email}. Open the link to finish creating your Klyrow account.
```

Actions:

- `Resend verification email`
- `Use a different email`
- `Return to sign in`

Requirements:

- Mask the displayed email where appropriate.
- Use a resend cooldown and rate limit.
- Never display or log the raw verification token or complete verification URL.
- Do not activate the application account until Keycloak reports a verified email according to the configured policy.

## 3.7 Forgot-password page

Heading:

```text
Reset your password
```

Body:

```text
Enter your email address and Klyrow will send password-reset instructions when an eligible account exists.
```

Always show the same completion message regardless of whether the account exists:

```text
Check your email for the next step.
```

This prevents account enumeration.

## 3.8 Logged-out page

After complete logout, redirect to:

```text
/login?logged_out=1
```

Show a non-dismissible success banner:

```text
You’re signed out. Your Klyrow session has ended.
```

Do not attempt to sign the user out of their entire Google account. End the Klyrow application session and Keycloak session only.

## 3.9 Required error states

Use generic, non-enumerating messages:

```text
Email or password is incorrect.
Verify your email before continuing.
Google sign-in could not be completed. Try again.
Your session expired. Sign in again.
Too many attempts. Try again later.
This account is disabled. Contact your administrator.
Klyrow authentication is temporarily unavailable.
```

Never expose raw Keycloak errors, stack traces, token values, client IDs not intended for public use, or internal hostnames.

---
