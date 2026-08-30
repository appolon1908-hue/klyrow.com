PHASE: M0 Invariant suite
COMMIT: a355199ba396f5072c1bee0f4afde1ff3b963b72
TESTS_BEFORE: 133   TESTS_AFTER: 284
SUITE_GREEN_CLEAN_CHECKOUT: YES
INVARIANTS_ADDED / VERIFIED: P1-P20 (P1-P11 and P13 registered as strict xfail; P12 and P14-P20 verified)
PIPELINES_REMAINING: 3
SAFE_MODE: true
PRODUCTION_GATE_APPROVED: false
DEFECTS_CLOSED: none
FAILURES_ENCOUNTERED: reserved-domain parity fixture (R1/R3); four Windows-only baseline limitations (R1/R5); workflow-dispatch historical gitleaks findings outside the M0 diff (R1); Docker registry authentication failure with host-Python fallback (R1/R5)
BLOCKERS: none
PRODUCTION_FILES_CHANGED: 0
PARITY_BASELINE: 22 passed, 14 strict xfailed across 36 API/SMTP/provider cells
LINUX_CI: test job passed with 164 passed and 25 xfailed
LINUX_CI_RUN: https://github.com/appolon1908-hue/klyrow.com/actions/runs/33319056951
CURRENT_MAIN_MERGE_SUITE: 253 passed, 31 strict xfailed in 454.73s
