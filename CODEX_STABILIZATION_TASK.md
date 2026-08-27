# Klyrow Application Stabilization Task

## Branch and safety boundary

Work only on `fix/klyrow-auth-security-stabilization`, stacked on the exact
current head of PR #36.

Do not deploy, publish images, mutate a server, change DNS/TLS/Keycloak/Postal,
create or rotate credentials, send email, or enable live/external delivery.
Preserve these defaults:

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

Dedicated SECURITY SMTP implementation remains isolated in its own PRs.

## Mission 1 — browser-session authority

- Revalidate `OidcIdentity`, `User`, membership, and tenant on every
  authenticated browser request.
- Revoke the opaque session immediately when an authority record is disabled.
- Enforce a bounded browser idle timeout before touching `last_seen_at`.
- Preserve the original absolute session deadline across refresh rotation.
- Revoke all sessions for the local user across all linked OIDC identities when
  `/auth/logout-all` is used.
- Reflect membership-role changes immediately.
- Preserve stable per-session CSRF and the opaque `__Host-klyrow_session`
  cookie.

## Mission 2 — invitations

- Keep the supported Keycloak OIDC `/forgot-credentials` flow with PKCE, state,
  nonce, and safe return URLs.
- Bind an explicitly validated invitation to its one-time OIDC transaction.
- Fail closed when the selected invitation no longer matches the verified
  identity email or tenant.
- Return the invitation capability once to the authorized OWNER/ADMIN creator
  with `Cache-Control: no-store`; persist only its hash.
- Do not silently create a new owner workspace when a selected invitation
  fails.

## Mission 3 — Postal runtime compatibility and callback tenancy

- Preserve the released global Postal-credential delivery loop for the root
  Compose deployment.
- Enable tenant-scoped Postal credentials only when
  `KLYROW_TENANT_POSTAL_PROVISIONING_ENABLED=true`.
- In tenant mode, resolve every signed Postal lifecycle callback from durable
  local send/provider mappings and a READY tenant mapping.
- Never use `KLYROW_POSTAL_TENANT_ID` as a fallback in tenant mode.
- Reject ambiguous or unresolved tenant attribution without writing event,
  audit, message, or suppression state.

## Mission 4 — runtime domain evidence

Maintain the operator-confirmed 14-domain evidence and the read-only verifier.
The verifier must report missing, wrong-state, and unexpected sending-enabled
domains, make no mutation, and return non-zero on drift.

## Mission 5 — architecture and branch cleanup

- Klyrow remains the email product/control plane.
- Postal and Mautic remain internal engines.
- Codestra Middleware remains the only cross-system write boundary.
- Keep SECURITY SMTP, Odoo, n8n, Kong, Caddy, DNS/TLS, and deployment
  activation isolated.
- Close superseded PRs only after the consolidated implementation is merged.
- Delete no branch until ancestry or an archive tag proves its work is
  preserved.

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
backend and frontend image builds
Trivy HIGH/CRITICAL scans
CycloneDX SBOM generation
git diff --check
```

Do not mark the PR ready until exact-head CI is green and every applicable
review thread is resolved.
