# Mission Blockers

## [K0-T2] D14 is absent from the pinned baseline

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
