# Mission Blockers

## [K0-T2] D14 is absent from the pinned baseline

- Status: RESOLVED by owner direction on 2026-08-30T15:07:20+02:00
- Date: 2026-08-30T15:05:36+02:00  · Class: design / mission-source contradiction
- Doing: Confirm D14 against the mission's pinned `main@6ff3d51` baseline before changing dependencies or CI.
- Happened: The exact baseline Git object already pins both dependencies, contains `tests/test_provider.py`, and runs the whole test directory in CI:

  ```text
  $ git show 6ff3d5176dadf336d5b357723363bd1c171a0450:apps/gateway/requirements.txt
  ...
  dnspython==2.7.0
  cryptography==50.0.0
  aiosmtpd==1.4.6

  $ git ls-tree -r --name-only 6ff3d5176dadf336d5b357723363bd1c171a0450 -- tests/test_provider.py
  tests/test_provider.py

  $ git show 6ff3d5176dadf336d5b357723363bd1c171a0450:.github/workflows/ci.yml
  ...
  - name: Install gateway and test dependencies
    run: pip install -r apps/gateway/requirements.txt pytest pip-audit
  ...
  - name: Compile and test
    env:
      PYTHONPATH: .
    run: |
      python -m compileall -q apps/gateway
      pytest -q tests
  ```

  A fresh environment installed only the checked-in requirements plus CI test tooling, and the candidate completed `177 passed, 9 warnings in 171.05s`; there was no collection failure.
- Rungs: R1 inspected the exact baseline blobs and reproduced clean collection / R2 not applicable because the kickoff requires immediate R6 for a defect mismatch / R3 not attempted because there is no defect to fix / R4 not applicable / R5 not permitted because silently redefining D14 would change the approved mission / R6 reached as required
- Why stopped: The mission says a defect that is not as described is an immediate R6. Owner direction is required on whether D14 should be recorded as already closed before this mission or whether a different baseline/ref was intended.
- Options: 1. Accept the pinned baseline evidence, mark D14 pre-closed, preserve the existing requirement and CI coverage, and resume at K0-T3.  2. Provide the intended baseline/ref where D14 reproduces, then restart K0-T2 against that source; this may invalidate the verified K0-T1 candidate relationship.
- Recommendation: Option 1. The dependency and full-suite CI protections are already present in both the pinned baseline and the candidate, and the clean 177-test run proves collection works.
- Blocked downstream: K0-T3 through K0-T7 and phases K1-K9
- Resolution: The owner selected Option 1. D14 is recorded as pre-closed at the pinned baseline; the existing dependency pins and full-suite CI coverage are preserved without a redundant code change. SMTP S0 now runs before K0-T3 as directed by `SMTP_INTEGRATION_MISSION.md`.

## [P00-GATE] PR #50 requires a fresh external approval

- Status: OPEN
- Doing: Squash-merge the fully tested K0 trunk after adding the master mission's required explanation of the seven modified existing tests.
- Happened: All three PR workflows passed at `5f92e7ce98c90f2584c6e14a7d37871565600f28`, including backend, frontend, secret, image, and both integration-contract checks. GitHub nevertheless reports `mergeable_state: blocked` because `main` requires one approving review, dismisses stale reviews after a push, and enforces the rule for administrators. The authenticated repository owner cannot approve their own pull request.
- Rungs: R1 inspected PR reviews, check runs, and `main` protection / R2-R5 cannot supply an independent review / R6 reached because merging now would require bypassing protected-branch policy.
- Why stopped: The master mission authorizes a normal squash merge, not bypassing or weakening branch protection.
- Resolution required: An eligible reviewer other than the pull-request author must approve the latest head of [PR #50](https://github.com/appolon1908-hue/klyrow.com/pull/50). Resume only after GitHub reports the PR clean and mergeable.
- Blocked downstream: K0 squash merge, legacy-ref deletion, `k0-complete` tag, S0/M0 retirement, and phases 01-16.
- Safe state: No branch was deleted, no tag was created, `main` was not changed, and Phase 01 was not started.
- Latest verification: The unauthenticated PR view briefly reported `mergeable_state: clean` after CI, but the authenticated owner view immediately before both merge attempts reported `mergeable_state: blocked`. The authenticated repository-protection result is authoritative. No merge endpoint was called after a blocked precondition, and no protection rule was bypassed or weakened.
