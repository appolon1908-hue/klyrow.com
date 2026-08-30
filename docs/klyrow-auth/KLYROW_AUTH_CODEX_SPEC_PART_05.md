# 12. Required configuration names

Use the repository's established configuration system. Suggested names:

```text
KLYROW_APP_ORIGIN=https://app.klyrow.com
KLYROW_API_BASE=https://api.codestra.co/v1/email
OIDC_ISSUER=https://auth.codestra.co/realms/codestra
OIDC_CLIENT_ID=klyrow-web
OIDC_CLIENT_SECRET=<secret-store-only>
OIDC_REDIRECT_URI=https://app.klyrow.com/auth/callback
OIDC_POST_LOGOUT_REDIRECT_URI=https://app.klyrow.com/login?logged_out=1
OIDC_SCOPES=openid profile email
SESSION_COOKIE_NAME=__Host-klyrow_session
SESSION_SIGNING_KEY=<secret-store-only>
SESSION_ENCRYPTION_KEY=<secret-store-only>
CSRF_SIGNING_KEY=<secret-store-only>
POSTAL_PROVISIONING_ENABLED=false
POSTAL_SMTP_USERNAME=<secret-store-only>
POSTAL_SMTP_PASSWORD=<secret-store-only>
POSTAL_IDENTITY_FROM=identity@klyrow.com
```

Keep `POSTAL_PROVISIONING_ENABLED=false` until the staging adapter and rollback path are independently reviewed.

Never print secret values in the final report.

---

# 13. Definition of done

This task is complete only when:

1. Users can register with email/password through the Klyrow-branded Keycloak page.
2. Users can sign in through Google via Keycloak.
3. Local and Google identity flows resolve to one canonical Keycloak/Klyrow identity where correctly linked.
4. Email verification and password reset use Keycloak and Postal transactional SMTP.
5. Klyrow stores no password.
6. The browser stores no OIDC token in local/session storage.
7. Secure application session creation and CSRF protection are implemented.
8. Logout clears the Klyrow session and completes Keycloak logout.
9. First login creates or joins exactly one workspace idempotently.
10. Postal provisioning is asynchronous, idempotent, tenant-mapped, and safe to retry.
11. All targeted and full tests pass.
12. Secret scanning passes.
13. The final report states explicitly that no production deployment or activation occurred.

---

# 14. Copy/paste Codex task

```text
You are working on Klyrow.com, a SaaS email-delivery platform backed by Postal 3.3.7.

Implement the authentication and first-login onboarding specification in KLYROW_AUTH_CODEX_SPEC.md.

Hard rules:
- Inspect the repository, current branch, architecture, tests, and deployment files before changing anything.
- Preserve the existing framework and repository conventions. Do not replace the stack.
- Use the existing canonical Keycloak issuer: https://auth.codestra.co/realms/codestra.
- Use Authorization Code flow with PKCE S256.
- Email/password and Google sign-in must be handled by Keycloak.
- Do not implement a Klyrow password database.
- Do not use Direct Access Grants/password grant.
- Do not store OIDC tokens in localStorage or sessionStorage.
- Prefer a same-origin BFF using an opaque Secure, HttpOnly, SameSite=Lax __Host-klyrow_session cookie.
- Validate state, nonce, PKCE, issuer, audience, authorized party, signature, exp, and nbf.
- Use (issuer, subject) as the canonical user identity.
- Require safe email verification and safe Google account linking.
- Never auto-link solely on an unverified email match.
- Do not store Google tokens or request Gmail API scopes.
- Klyrow owns users/workspaces/memberships. Postal owns email-delivery resources.
- Do not modify Postal source or write directly to Postal's database.
- Postal provisioning must be asynchronous through an idempotent outbox-backed adapter.
- Use the existing dedicated SMTP-only Postal credential and identity@klyrow.com for Keycloak identity email.
- Do not expose secrets in code, logs, tests, screenshots, commits, or the final report.
- Do not deploy, restart Postal/Keycloak, rotate credentials, enable production provisioning, or activate live traffic.

Implementation workflow:
1. Print current directory, repository, branch, clean/dirty status, and starting SHA.
2. Inventory the current auth code, Keycloak configuration/theme, session handling, Postal adapter, migrations, tests, and CI.
3. Compare the current implementation to the specification and list gaps before coding.
4. Create the appropriate review branch for the current PR scope. Do not bundle all four proposed PRs into one branch.
5. Implement the smallest complete reviewable slice with additive migrations and rollback notes.
6. Add unit, integration, browser, security, and accessibility tests applicable to that slice.
7. Run targeted tests, then the complete repository test suite, type checks, lint, build, secret scan, and dependency audit available in the repository.
8. Do not hide failed tests. Fix failures caused by the change; clearly identify unrelated pre-existing failures.
9. Produce a final report with:
   - current directory
   - repository and branch
   - starting SHA and final SHA
   - commits created
   - every changed file
   - migrations and rollback instructions
   - configuration/secret names added, with values redacted
   - targeted test commands/results
   - full test commands/results and total count
   - security/accessibility checks
   - known limitations or blockers
   - confirmation that Postal source was not modified
   - confirmation that no secrets were printed or committed
   - confirmation that no deployment, restart, credential rotation, production provisioning, or live activation occurred

Stop and report rather than bypassing a security boundary or inventing a missing production secret.
```
