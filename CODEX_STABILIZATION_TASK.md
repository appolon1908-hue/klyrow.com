# Klyrow Authentication and SECURITY-Mail Stabilization Task

## Branch and safety boundary

Work only on `fix/klyrow-auth-security-stabilization`.

Do not deploy, publish images, mutate a server, change DNS/TLS/Keycloak/Postal, create or rotate credentials, send email, or enable live/external delivery. Preserve these defaults:

```text
KLYROW_SAFE_MODE=true
KLYROW_PRODUCTION_GATE_APPROVED=false
KLYROW_SECURITY_SMTP_ENABLED=false
KLYROW_SECURITY_SMTP_LIVE_ENABLED=false
KLYROW_SECURITY_SMTP_PRODUCTION_APPROVED=false
LIVE_EMAIL_DELIVERY=false
EXTERNAL_EMAIL_DELIVERY=false
PRODUCTION_PROVIDER_ROUTING=false
MARKETING_DELIVERY=false
```

## Mission 1 — SECURITY SMTP runtime

Integrate the reviewed behavior from `fix/security-smtp-runtime-wiring` without losing the current authentication/BFF, onboarding, dashboard, Postal-provisioning, or worker code.

Required behavior:

- worker and SMTP relay receive identical SECURITY activation policy;
- explicit production-approval gate;
- exact lower-case canary recipient allowlist before production approval;
- bounded canary maximum from 1 through 10;
- reject a second recipient in a canary SMTP transaction;
- reject external recipients outside the exact canary allowlist;
- read-only preflight verifies tenant, credential, expiry, SECURITY-only stream, exact sender, verified/enabled domain, and tenant policy without reading or printing the SMTP password;
- non-SECURITY streams remain sandbox-only.

## Mission 2 — encrypted SECURITY payload retention

Integrate the encryption design from `feat/keycloak-security-mail-hardening` and resolve every review finding.

Required behavior:

- queued SECURITY MIME is encrypted at rest;
- decryption occurs only in the dedicated SECURITY delivery worker;
- plaintext/base64 MIME and reset codes never appear in database JSON, logs, audit details, or API responses;
- successful provider submission purges ciphertext;
- the standard root `docker-compose.yml` wires the encryption-key file into both `worker` and `smtp-relay`, and defines the root Compose secret;
- sandbox-delivered SECURITY messages and `sandbox_captures` are scrubbed no later than the bounded retention deadline;
- terminal/dead-letter SECURITY records are scrubbed, including lease-expiry paths;
- cleanup is idempotent and preserves delivery/dead-letter status and non-sensitive metadata;
- add regression tests for Compose wiring, sandbox capture cleanup, delivered cleanup, terminal/dead-letter cleanup, missing key, invalid key, and bounded maximum age.

## Mission 3 — resolver availability semantics

Apply the small resolver correction from PR #30 to the current `apps/gateway/app/main.py` without copying its mixed historical branch.

Required behavior:

- `httpx.RequestError` while contacting the authoritative resolver returns HTTP 503 with `authorization_unavailable`;
- resolver HTTP 5xx returns the same 503;
- malformed/non-JSON resolver responses return the same 503;
- a nominally successful response missing `identity_id` or `tenant_id` returns the same 503;
- preserve 401 for invalid credentials, 404 for deliberately hidden resources, and 403 for authorization denial;
- add focused regression tests.

## Required validation

Run and report:

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

Do not mark the PR ready until exact-head CI is green and every review thread is resolved.
