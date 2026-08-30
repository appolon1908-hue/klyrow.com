# K0 Failures

## K0-T2 — D14 mission/source contradiction

The source verification required before K0-T2 found that D14 is absent from the pinned baseline. Full evidence, recovery-rung accounting, options, and the recommendation are recorded in [`docs/BLOCKERS.md`](../../BLOCKERS.md#k0-t2-d14-is-absent-from-the-pinned-baseline).

No production code, dependency, CI, safety-gate, or runtime configuration was changed. The most recent full suite result remains:

```text
177 passed, 9 warnings in 169.35s
```

Resolved by owner direction on 2026-08-30T15:07:20+02:00: accept the pinned-baseline evidence, mark D14 pre-closed, and preserve the existing protections. No corrective code change was required.
