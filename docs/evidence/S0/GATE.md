# Gate S0 — Contract Conformance

PHASE: S0 Land branch + conformance test  
COMMIT: `0cd48c6247ac360d94931666caa7934979c4cd9b`  
TESTS_BEFORE: 177  
TESTS_AFTER: 186 passed, 5 strict xfailed  
SUITE_GREEN_CLEAN_CHECKOUT: YES  
INVARIANTS_ADDED: C1, C2, C3, C4, C5  
INVARIANTS_VERIFIED: C5 forbidden-label enforcement passes; C1-C4 and C5 required-label gaps are strict xfails  
EXISTING_TESTS_MODIFIED: 0  
SAFE_MODE: true  
PRODUCTION_GATE_APPROVED: false  
DEFECTS_CLOSED: none; S0 makes C1-C5 source-visible and self-reporting  
FAILURES_ENCOUNTERED: wrong isolated-worktree staging corrected before commit; concurrent remote push reconciled without force; local Node absent and verified by GitHub Node 22 workflow  
BLOCKERS: none

## Gate checklist

- [x] `codex/klyrow-smtp-integration-files@f2044cf` folded by merge and recorded as entry 68 in the K0 reconciliation manifest.
- [x] `tests/test_contract_conformance.py` discovers events, registered commands/routes, core message statuses, Middleware headers, and Prometheus collector labels from application source.
- [x] C1, C2, C3, and C4 are `xfail(strict=True)` with their C-codes.
- [x] C5 forbidden labels pass against all discovered collectors; missing required platform labels are a separate strict C5 xfail for S4.
- [x] Both integration workflows execute the source-backed conformance file.
- [x] Python integration validator passed locally.
- [x] Full suite passed after gate evidence was added: `186 passed, 5 xfailed, 9 warnings in 171.82s`.
- [x] Test count exceeds the S0 minimum of 134 and does not decrease from the 177-test K0 candidate.

## Fail-closed flags

```text
KLYROW_SAFE_MODE=true
KLYROW_PRODUCTION_GATE_APPROVED=false
publicSubmissionEnabledByDefault=false
liveDeliveryEnabledByDefault=false
metricsEnabledByDefault=false
```

No file under `apps/` and no existing runtime safety configuration changed in S0.

## Workflow evidence

- Validate Codestra integration files: run `33314274201` — success — https://github.com/appolon1908-hue/klyrow.com/actions/runs/33314274201
- Validate Codestra SMTP integration files: run `33314274184` — success — https://github.com/appolon1908-hue/klyrow.com/actions/runs/33314274184

## Source-discovered mismatch evidence

See `docs/evidence/S0/CONFORMANCE_BASELINE.md` for the exact finite sets, dynamic call sites, missing routes, status differences, missing headers, and collector-label results.
