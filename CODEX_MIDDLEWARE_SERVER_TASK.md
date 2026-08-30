# Codex Middleware Server Task — Klyrow Mission 01

## Dispatch identity

- Repository: `https://github.com/appolon1908-hue/klyrow.com`
- Execution host: Codestra middleware server
- Expected public IP: `65.109.65.169`
- Expected private IP: `10.40.0.1`
- Branch: `feat/klyrow-auth-theme-ui`
- Required planning ancestor: `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e`
- Working directory: an isolated Codex checkout, preferably `/srv/codex-workspaces/klyrow.com`
- Delivery target: GitHub feature branch and draft pull request only
- Production deployment: prohibited in this task

## Objective

Implement Mission 01 completely: a polished, modern, responsive and accessible Klyrow authentication experience for email/password signup, Google sign-in through Keycloak, verification, password recovery, invitation entry and logged-out confirmation.

This task starts the 25-branch Klyrow implementation program. Work on this branch only. Do not begin Mission 02 or any later mission.

## Mandatory reading order

Read every file completely before editing:

1. `KLYROW_CODEX_EXECUTION_INDEX.md`
2. `KLYROW_AUTH_CODEX_SPEC.md`
3. every authentication specification file linked by `KLYROW_AUTH_CODEX_SPEC.md`
4. `KLYROW_MODERN_SAAS_PROGRAM.md`
5. `docs/implementation/KLYROW_FEATURE_MISSIONS.md`
6. `KLYROW_IDENTITY_AUTOMATION_ODOO_CONTROL_PLANE.md`
7. `docs/implementation/KLYROW_CONTROL_PLANE_BRANCH_MISSIONS.md`
8. `docs/implementation/KLYROW_ADMIN_ODOO_N8N_ACCEPTANCE_MATRIX.md`

The shared security, migration, testing, integration and release contracts in those files are binding.

## Mandatory preflight output

Before changing any file, print and record:

```text
HOSTNAME=
HOST_IPS=
CURRENT_DIRECTORY=
REPOSITORY_REMOTE=
CURRENT_BRANCH=
STARTING_HEAD_SHA=
PLANNING_ANCESTOR_PRESENT=
GIT_STATUS=
CODEX_VERSION=
NODE_VERSION=
PNPM_VERSION=
PYTHON_VERSION=
```

Then verify:

1. This is the Klyrow repository.
2. The active branch is exactly `feat/klyrow-auth-theme-ui`.
3. The branch contains planning ancestor `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e`.
4. The checkout is not the live `/opt/klyrow` production working tree.
5. The working tree is clean before implementation.
6. No production secrets are visible in the repository or shell output.
7. No server, container, Keycloak, Postal, Odoo, n8n or middleware service will be restarted.

Stop and report if any of these checks fail. Do not bypass them with force checkout, reset, secret disclosure or production mutation.

## Existing-code audit

Inspect at minimum:

- `apps/gateway/app/portal.html`
- `apps/gateway/app/portal.js`
- authentication and OIDC routes under `apps/gateway/app`
- existing Keycloak-related configuration and documentation
- frontend package and build configuration, if present
- Docker and reverse-proxy configuration relevant to static assets
- `.github/workflows/ci.yml`
- authentication, browser and accessibility tests

Create an audit table in the completion report with every Mission 01 requirement marked:

- `IMPLEMENTED`
- `PARTIAL`
- `MISSING`
- `UNSAFE`

Preserve working behavior. Replace unsafe browser-token behavior only within this mission's approved scope and without implementing Mission 02's server-side token exchange prematurely.

## Required product experience

Implement a clean Klyrow design system suitable for a modern email SaaS.

### Visual direction

- Professional neutral surfaces with a strong blue/violet Klyrow accent.
- High readability and generous spacing.
- Responsive two-panel desktop authentication shell.
- Single-card mobile and narrow-tablet presentation.
- Consistent buttons, inputs, checkboxes, alerts, links and status messages.
- Important states use text plus iconography, not color alone.
- Reduced-motion support.
- No copied Google, Gmail, Postal or third-party product interface.

### Login page

Include:

- Klyrow logo/wordmark.
- `Welcome back` heading.
- Email field.
- Password field with accessible show/hide control.
- Keep-signed-in option as UI only until Mission 02 defines session policy.
- Forgot-password link.
- Primary `Sign in` action.
- `Continue with Google` action routed through Keycloak identity brokering.
- Link to create an account.
- Loading, disabled, invalid-credentials, rate-limited, account-disabled and service-unavailable states.

### Signup page

Include:

- First name.
- Last name.
- Work email.
- Password.
- Confirm password.
- Password guidance and strength feedback.
- Terms and privacy acknowledgement.
- `Continue with Google` action routed through Keycloak.
- Existing-account link.
- Duplicate-email, weak-password, invalid-email, unavailable-service and submission-loading states.

Keycloak remains authoritative for email/password registration. Do not create a second production password store in Klyrow.

### Additional authentication states

Implement polished responsive pages or states for:

- Verify email.
- Resend verification.
- Verification link expired.
- Verification success.
- Forgot password.
- Password-reset email sent.
- Reset password.
- Reset link expired.
- Reset success.
- Invitation entry and invitation validation.
- Logged-out success.
- Generic authentication service error.
- Account disabled or suspended message.

### Language support

Provide complete English and Spanish interface strings. Do not leave mixed-language fallback text in a single screen.

## Keycloak theme

Create or extend a Klyrow Keycloak login theme and email theme without modifying Keycloak source.

Required theme surfaces include:

- Login.
- Registration.
- Identity-provider selection or Google continuation.
- Verify email.
- Forgot password.
- Reset password.
- Required actions.
- Error and expired-action states.
- English and Spanish messages.
- Branded verification and password-reset emails.

Preserve the canonical issuer:

```text
https://auth.codestra.co/realms/codestra
```

Google OAuth must be brokered by Keycloak. Never place a Google client secret in browser code or the repository.

## Frontend implementation rules

- Prefer Vue 3 + TypeScript under the program's `apps/web` target when the repository audit confirms the progressive migration path.
- Keep the current portal available until replacement routes pass acceptance tests.
- Use reusable components rather than duplicating markup across states.
- Use semantic HTML.
- Every form control requires an associated label.
- Validation must be connected with `aria-describedby` and announced appropriately.
- Focus must move predictably after navigation and validation failure.
- All actions must work by keyboard.
- Use visible focus indicators.
- Meet WCAG 2.2 AA contrast and interaction requirements.
- Do not use `localStorage` or `sessionStorage` for access tokens, refresh tokens, identity secrets or passwords.
- Do not expose Postal, Keycloak, Odoo, n8n or middleware credentials.
- Do not make browser calls directly to Postal, Odoo or n8n.

## Cross-system boundaries for this mission

This branch implements presentation and theme behavior only.

- Keycloak is authoritative for authentication and verified identity.
- Klyrow remains authoritative for tenancy and product state.
- Codestra middleware is the only future cross-system integration boundary.
- n8n is non-authoritative automation.
- Odoo is the future back-office CRM, accounting, billing and support surface.
- Do not implement Odoo or n8n synchronization in Mission 01.
- Do not publish real signup or billing events until the control-plane branches implement the shared event/outbox contract.
- Do not put billing records into Keycloak.

## Required tests

Add and run applicable tests for:

1. Every authentication page/state.
2. Client-side validation.
3. Password show/hide behavior.
4. Loading and disabled controls.
5. Server-error mapping.
6. English and Spanish rendering.
7. Mobile, tablet and desktop layout behavior.
8. Keyboard-only operation.
9. Focus order and focus restoration.
10. Accessible names, descriptions and live-region errors.
11. Automated accessibility scanning.
12. Google redirect initiation through the Klyrow/Keycloak route.
13. No Google secret in the frontend bundle.
14. No OIDC token, password or secret written to browser storage.
15. Existing gateway and authentication regression tests.
16. Production build.
17. Type checking and linting.
18. Secret scan and dependency/security scan.

Do not claim a test passed unless the exact command was run and its exact result was captured.

## Required CI changes

Update CI only as needed to run the new frontend, theme, browser and accessibility checks. Preserve existing gateway, PostgreSQL migration, gitleaks, container scan and SBOM jobs.

Do not add a production deployment job.

## Git and PR requirements

- Work only on `feat/klyrow-auth-theme-ui`.
- Do not rewrite unrelated history.
- Do not force-push.
- Create logical commits.
- Push this feature branch only.
- Update the existing draft PR for this branch if present; otherwise open one against `planning/klyrow-modern-saas-program`.
- Keep the PR draft until targeted and complete checks pass.
- Do not merge.
- Do not retarget to `main` until prerequisite documentation PRs are reviewed and merged.

## Hard prohibitions

Do not:

- deploy to staging or production;
- modify the live `/opt/klyrow` checkout;
- restart or reconfigure Caddy, Docker, Keycloak, Postal, Odoo, n8n, RabbitMQ, PostgreSQL, Mautic or middleware services;
- modify Postal source code;
- write directly to Postal, Keycloak or Odoo databases;
- rotate credentials;
- change DNS, PTR/rDNS or TLS certificates;
- enable live email, SMS or PSTN delivery;
- enable unrestricted Postal provisioning;
- enable real billing or payment collection;
- use OAuth password grant or Keycloak Direct Access Grants;
- store bearer or refresh tokens in browser storage;
- print or commit secrets;
- bypass a failing security, tenant-isolation or production-safety check.

## Completion report

At completion, post a report to the feature PR containing:

1. Hostname and host IPs.
2. Isolated working directory.
3. Repository remote.
4. Branch.
5. Starting SHA.
6. Final SHA.
7. Every commit created.
8. Every changed file.
9. Requirement audit: implemented, partial, missing and unsafe.
10. Implemented UI and theme behavior.
11. Retained and migrated behavior.
12. Exact targeted test commands and results.
13. Exact complete test-suite commands and results.
14. Lint, type-check and production-build results.
15. Browser and accessibility results.
16. Security, dependency and secret-scan results.
17. CI changes and status.
18. Known limitations and blockers.
19. Confirmation that Postal source was not modified.
20. Confirmation that no Keycloak, Odoo, n8n or Postal database was accessed directly.
21. Confirmation that no secrets were printed or committed.
22. Confirmation that no deployment, merge, service restart, DNS/TLS change, credential rotation, production provisioning, real billing or live activation occurred.

After posting the report, stop. Do not automatically start Mission 02.