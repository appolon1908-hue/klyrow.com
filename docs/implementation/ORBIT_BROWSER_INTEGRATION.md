# Orbit and browser integration — issues #81 and #83

Audit date: 2026-09-10. Starting Klyrow main: `40866af8db9567a1f89ae44f1ce22ead9d52dbe7`.
Workspace: isolated source checkout on middleware, not a running application change.

## Requirement inventory before editing

| Requirement | State at audit | Implementation owner / next action |
| --- | --- | --- |
| Browser-bound PKCE/state/nonce and concurrent flow cookies | IMPLEMENTED | Existing browser security and per-flow cookie modules; retain and run regression suite |
| Invitation membership, rollback and exact identity authority | IMPLEMENTED | Existing invitation and step-up guards; retain |
| Canonical backend `mail.send`, CSRF and delivery gates | IMPLEMENTED | `browser_security_fixes.browser_send`; retain |
| Browser send permission presentation | MISSING | Expose canonical permission projection and consume it in dashboard |
| Orbit-compatible safe session projection | MISSING | Adapt existing BFF summary; do not return OIDC credentials |
| Expiry and return-to browser integration | PARTIAL | Handle anonymous/401 consistently and preserve protected deep links through sign-in |
| Multi-tab UI invalidation | MISSING | Same-origin notification rechecks backend authority; no session data in channel |
| Route inventory / new page gate | MISSING | Make current component routing consume the inventory and verify it in CI |
| Immutable Orbit install authority | UNSAFE to consume | SDK main `a194b5154a5b313c8fc4b9150abd17a4cc6612ae`: release `orbit/release/orbit-v2.0.0.json` is `superseded-source-candidate`, `installAllowed: false`; no releases published |
| Shared Orbit header/footer/tokens and full-shell certification | MISSING / blocked | Await protected immutable installable packages; do not copy superseded tarballs |
| Running Keycloak staging and promotion evidence | MISSING | Separate authorized staging/release process; source tests cannot certify runtime |

## Integration contract

The Vue app continues to use Klyrow's same-origin BFF and host-only session
cookie. The Orbit view is a projection of that summary, not a second login
system. Klyrow's central role catalog supplies capabilities; the API rechecks
current membership and all existing send controls on every mutation. UI
capabilities are presentation hints, never authorization.

The consumer contract is pinned for review to SDK
`a194b5154a5b313c8fc4b9150abd17a4cc6612ae/orbit/contracts/auth-session.openapi.yaml`.
Klyrow retains its existing response fields and cookie name. The frontend
adapter maps identity, tenant, role, expiry and capabilities into the Orbit
shape and excludes the CSRF credential and session identifier. No SDK auth stub
is used. The adapter must be revalidated against the eventual accepted release.

Session notifications contain only an invalidation marker. Receiving tabs
reload their current route and obtain authority from the BFF. Protected
deep links retain path, query and fragment; authentication action URLs and
external destinations are not return targets. API requests remain same-origin,
no-store, and never automatically retry a mutation.

## Route scope and missing surfaces

`apps/web/src/routeManifest.ts` is the executable inventory of the current six
root views and all existing authentication states. Product prefixes retain
their existing component fallback; they do not establish that a dedicated
campaign, billing or account page exists. The route gate checks every root
Vue view and every declared route.

Public marketing belongs to `klyrow-Website-`. Dedicated account, billing,
campaign, audience, template, delivery, legal and unknown-route pages are not
implemented by this change. The current auth UI links to local terms/privacy
paths, whose content still needs an approved legal/public-site integration.
Loading and error states exist in product views; empty states are partial.
Shared degraded/forbidden/expired presentation, responsive full-shell
screenshots and Orbit visual baselines remain acceptance work for #81.

## Release and rollback

No schema migration, provider contract, domain event, Odoo/n8n integration or
runtime configuration changes are needed. Rollback is a source revert and the
normal atomic gateway/web release procedure. Existing clients ignore the
additive `capabilities` response field; absent capabilities disable send in the
new UI until gateway/web versions match.

Do not close #81 or #83 based on this source slice. The immutable package
release, independent review and actual staging evidence remain separate gates.
No production credentials, identity records, provider resources, mail sends,
DNS, services or production flags are changed by this work.

## Source validation

Execution: isolated `/root/klyrow-issues81-83-20260910/klyrow.com` checkout on
middleware (`65.109.65.169`), branch `fix/orbit-browser-integration-20260910`.
The PR records final commit and GitHub workflow evidence. No source merge or
runtime deployment is performed as part of this branch report.

Commands run from `apps/web`:

- `pnpm install --frozen-lockfile`: pass.
- `pnpm typecheck`: pass.
- `pnpm test`: 22 passed, including route and adapter tests.
- `pnpm lint`: no errors; 36 existing Vue spacing warnings.
- `pnpm build`: pass.
- `pnpm exec playwright install chromium`: pass.
- `pnpm test:e2e`: 13 passed; mobile/tablet/desktop auth accessibility,
  keyboard focus, auth action failure handling, deep links, expiry, capability
  presentation, send retry identity and multi-tab logout. API responses are
  controlled browser fixtures, not a running Keycloak or provider assertion.

Backend: isolated Python 3.12 environment with exact gateway requirements;
`PYTHONPATH` points to this checkout. Focused command from the repository root:

```sh
python -m pytest -q tests/test_browser_session_authority.py tests/test_browser_security_fixes.py tests/test_browser_flow_cookie_authority.py tests/test_browser_frontend_api_contract.py tests/test_browser_session_lifecycle.py tests/test_browser_step_up_identity.py tests/test_browser_step_up_deadline.py
```

Result: 64 passed. Includes unchanged invitation/tenant, browser flow,
CSRF/send, session revocation and step-up regression coverage. The new summary
checks cover current role changes, unknown roles, UTC expiry and no OIDC tokens.
The adoption manifest validates against the exact pinned SDK JSON schema.
`git diff --check` passes. Full backend, dependency audits, migration-twice,
image/SBOM/scans/reproducibility and readiness results are recorded on the PR
when the corresponding jobs complete; they are not implied by focused tests.

Changed behavior is additive session metadata and browser integration only.
No data model, OpenAPI path/security, domain event, Middleware/Odoo/n8n contract,
Postal source, identity database or production policy changes. Existing metrics,
alerts and runtime rollback procedures remain applicable. No secrets were
printed or committed, and no external send or live activation was performed.
