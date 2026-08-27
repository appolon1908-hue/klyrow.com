# Klyrow Application Stabilization Task

## Branch and safety boundary

Work only on `fix/klyrow-auth-security-stabilization`, stacked on the exact current head of PR #36.

Do not deploy, publish images, mutate a server, change DNS/TLS/Keycloak/Postal, create or rotate credentials, send email, or enable live/external delivery. Preserve these defaults:

```text
KLYROW_SAFE_MODE=true
KLYROW_PRODUCTION_GATE_APPROVED=false
KLYROW_TENANT_POSTAL_PROVISIONING_ENABLED=false
KLYROW_SECURITY_SMTP_ENABLED=false
KLYROW_SECURITY_SMTP_LIVE_ENABLED=false
LIVE_EMAIL_DELIVERY=false
EXTERNAL_EMAIL_DELIVERY=false
PRODUCTION_PROVIDER_ROUTING=false
MARKETING_DELIVERY=false
```

Dedicated SECURITY SMTP implementation remains isolated in its own PRs and is not bundled into this branch.

## Mission 1 — browser-session authority

- Revalidate the local `OidcIdentity`, `User`, tenant membership, and tenant on every authenticated browser request.
- Revoke the opaque browser session immediately when the identity, user, membership, or tenant is disabled.
- Revalidate again before refresh can rotate a session.
- Reflect membership-role changes in existing sessions without relying on expiry.
- Preserve the stable per-session CSRF token and opaque `__Host-klyrow_session` cookie.
- Add regression tests for disabled user, disabled identity, refresh denial, revocation, and role changes.

## Mission 2 — backwards-compatible Postal delivery

- Preserve the released global Postal-credential delivery loop for the standard root Compose deployment.
- Enable tenant-scoped Postal credential delivery only when `KLYROW_TENANT_POSTAL_PROVISIONING_ENABLED=true`.
- The Postal provisioning overlay must set the flag explicitly and retain the provisioning worker, provisioner, and provider-credential key.
- Do not silently inherit the global Postal key once tenant provisioning is explicitly enabled.
- Add tests for the default and explicitly enabled worker selection.

## Mission 3 — runtime domain inventory

Record the operator-confirmed 14-domain sending inventory in a normalized machine-readable manifest. Add a read-only verifier that compares the manifest with `domain_claims` and requires state `SENDING_ENABLED`.

The verifier must:

- use a read-only `SELECT`;
- report missing, wrong-state, and unexpected sending-enabled domains;
- make no DNS, Postal, Keycloak, provider, or database mutation;
- return non-zero on drift.

## Mission 4 — architecture and branch cleanup

- Preserve Klyrow as the email product/control plane.
- Keep Postal and Mautic behind Klyrow.
- Keep Codestra Middleware as the only cross-system write boundary.
- Do not combine unrelated SECURITY SMTP, Odoo, n8n, Kong, Caddy, or deployment activation work.
- Close superseded PRs only after the consolidated implementation is merged.
- Delete no branch until commit ancestry or an archive tag proves its work is preserved.

## Required validation

```text
python scripts/migrate twice against PostgreSQL 17
schema ledger count equals migration-file count
python -m compileall -q apps/gateway
pytest -q tests
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm test:e2e
gitleaks
backend image build
frontend image build
Trivy HIGH/CRITICAL scans
CycloneDX SBOM generation
git diff --check
```

Do not mark the PR ready until exact-head CI is green and every applicable review thread is resolved.
