# K0-T1 Candidate Verification

- Verified: 2026-08-30T15:01:17+02:00
- Candidate: `origin/feat/klyrow-postal-provisioning`
- Candidate commit: `e5b8791d0d9c652b084943c5b5fb765b2b32e811`
- Baseline `origin/main`: `6ff3d5176dadf336d5b357723363bd1c171a0450`
- Divergence from baseline: 65 commits ahead, 0 commits behind
- Worktree state before verification: clean

## Dependency verification

A fresh Python virtual environment was created outside the repository and populated with:

```text
pip install -r apps/gateway/requirements.txt pytest pip-audit
```

The checked-in requirements already pin both dependencies named in D14:

```text
dnspython==2.7.0
aiosmtpd==1.4.6
```

The checked-in CI installs the complete requirements file and runs `pytest -q tests`, so `tests/test_provider.py` cannot be silently omitted because `aiosmtpd` is absent.

## Test evidence

Command:

```text
PYTHONPATH=. python -m pytest tests/ -q
```

Result:

```text
177 passed, 9 warnings in 171.05s
```

The warnings are existing FastAPI and Starlette deprecation warnings. There were no collection errors, failures, skips, or xfails. The candidate exceeds the mission baseline of 133 tests by 44 tests.

## Decision

K0-T1 passes. The candidate is the specified 65-ahead/0-behind trunk candidate and its test count is not below 133. D14 is already closed in this candidate and will be preserved through reconciliation.
