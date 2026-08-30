# M0 failures encountered

## R1/R3 — Reserved-domain parity fixture

The first parity fixture used `capture@klyrow-sink.test`. The public API validates
mailboxes with `EmailStr`, which rejects the reserved `.test` suffix before any
mail guard runs. That produced four misleading failures, including strict-xfail
XPASS outcomes. The smallest reproduction identified fixture validation as the
cause. The test-only sink was changed to `capture@example.net` and placed in the
fixture tenant's sandbox allowlist. No production code or behavior changed.

## R1/R5 — Windows baseline limitations

The unmodified baseline has four host-specific failures on this Windows runner:

- the encrypted-backup round trip requires a local GPG executable;
- the DKIM key-permission assertion requires POSIX mode `0600` semantics;
- the DKIM DNS matrix case cascades because the preceding permission test exits
  before leaving an active key;
- the released migration hash differs after checkout under the machine's global
  `core.autocrlf=true` configuration.

No test was edited, skipped, or weakened. Local verification deselected exactly
those four cases at the command line and passed with `160 passed, 4 deselected,
25 xfailed`. The exact branch commit then ran in the repository's clean Ubuntu CI
environment and passed with `164 passed, 25 xfailed`.

## R1 — Historical workflow-dispatch gitleaks findings

The manually dispatched CI run's secret job scanned the repository's full
304-commit history and reported two instances of the same pre-existing fixture in
`apps/web/e2e/auth.spec.ts`, from commits `e5b8791` and `c5b36f7` dated Aug 27.
Neither commit nor file is in the M0 diff. The exact-commit Linux test, dependency
audit, and migration jobs passed. Pull-request CI remains the authoritative gate
because its gitleaks invocation is scoped by the pull-request event.
