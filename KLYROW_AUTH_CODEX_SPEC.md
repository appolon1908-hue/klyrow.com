# Klyrow.com SaaS Authentication and Onboarding

## Codex implementation specification index

This is the authoritative entry point for the Klyrow customer authentication, signup, Google sign-in, logout, first-login workspace onboarding, and Postal 3.3.7 provisioning work.

The specification is divided into five ordered files for reviewability. Codex must read **all five files completely, in order, before modifying code**:

1. [`docs/klyrow-auth/KLYROW_AUTH_CODEX_SPEC_PART_01.md`](docs/klyrow-auth/KLYROW_AUTH_CODEX_SPEC_PART_01.md) — product boundary, architecture, session rules, and complete login/signup/logout UI requirements.
2. [`docs/klyrow-auth/KLYROW_AUTH_CODEX_SPEC_PART_02.md`](docs/klyrow-auth/KLYROW_AUTH_CODEX_SPEC_PART_02.md) — Keycloak client, Google identity provider, Keycloak theme, and BFF/API contract.
3. [`docs/klyrow-auth/KLYROW_AUTH_CODEX_SPEC_PART_03.md`](docs/klyrow-auth/KLYROW_AUTH_CODEX_SPEC_PART_03.md) — application data model and Postal 3.3.7 integration requirements.
4. [`docs/klyrow-auth/KLYROW_AUTH_CODEX_SPEC_PART_04.md`](docs/klyrow-auth/KLYROW_AUTH_CODEX_SPEC_PART_04.md) — security, accessibility, testing, and four-PR implementation split.
5. [`docs/klyrow-auth/KLYROW_AUTH_CODEX_SPEC_PART_05.md`](docs/klyrow-auth/KLYROW_AUTH_CODEX_SPEC_PART_05.md) — configuration names, definition of done, and the complete copy/paste Codex task.

## Non-negotiable baseline

- Canonical issuer: `https://auth.codestra.co/realms/codestra`
- Mail engine: Postal `3.3.7`
- Email/password and Google authentication are handled through Keycloak.
- Use Authorization Code flow with PKCE S256.
- Use `(issuer, subject)` as the canonical identity.
- Do not store OIDC tokens in browser storage.
- Do not implement a Klyrow password database.
- Do not expose Postal or Keycloak secrets to the browser.
- Postal provisioning must be asynchronous, idempotent, tenant-scoped, and outbox-backed.
- Do not modify Postal source or write directly to Postal's database.
- Do not deploy, restart services, rotate credentials, enable production provisioning, or activate live traffic during implementation.

## Instruction to give Codex

```text
Read KLYROW_AUTH_CODEX_SPEC.md and every ordered specification part linked from it completely.

First audit the current repository against the specification and report the gaps.
Then implement only PR 1 on a new branch named:

feat/klyrow-auth-theme-ui

Do not bundle PR 2, PR 3, or PR 4 into the same branch.
Do not deploy, restart Postal or Keycloak, rotate credentials, enable production provisioning, or activate live traffic.
At completion, provide the full evidence report required by Part 05.
```

This documentation branch contains specification files only. It does not implement, merge, deploy, or activate the authentication system.
