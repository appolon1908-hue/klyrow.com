# Historical live Klyrow OpenAPI authority — 2026-09-02

## Evidence identity

This record preserves the non-executable evidence from the historical live-gateway snapshot without adding a second importable application tree.

- Observed runtime source snapshot: `ca2254e5f3beeadd0122578ee96d7a59751cda60`
- Historical evidence PR head: `26faa33f922af0210c5efa9ac9f3164b3b3ec0af`
- Historical exact-head Actions run: `33588339797` — PASS
- Observed runtime: `klyrow-gateway-1`
- Files compared with the observed container: 25
- Documented OpenAPI HTTP operations: 258
- Runtime discovery route: 1 additional operation, for 259 runtime operations total
- Sorted `METHOD PATH` authority SHA-256: `7d005a48538f0fcc15370a395cb0f33f1928b368dc07d631f0384b58a241b2e6`

The original evidence stated that all 25 captured files matched the observed container byte-for-byte before the snapshot was committed. The historical branch and commit remain available in Git history for forensic comparison.

## Authority boundary

The canonical application remains `apps.gateway.app.platform:app`, sourced from `apps/gateway`. Current operation-level audience, authentication, CSRF, webhook-signature, and idempotency authority must be changed only through the canonical source and its focused remediation PRs.

The historical snapshot classified routes as `PUBLIC`, `BROWSER_BFF`, `INTERNAL`, `ADMIN`, `WEBHOOK`, `TRACKING`, or `LEGACY`. Those values are historical observations, not permission to restore the old snapshot over protected source.

## Non-duplication rule

The prior branch carried an importable `runtime_authority/` copy of the gateway. That duplicate tree is deliberately excluded from this reconciled evidence record because it could be imported, tested, packaged, or certified instead of the canonical application.

No executable source, workflow, image, Compose file, migration, or runtime dependency is preserved here. Reproduction must compare the historical Git commit or archived artifact directly; it must not create another application package inside the repository.

## Change control

Any current operation added, removed, renamed, reclassified, or assigned a different authentication model requires review against the current canonical OpenAPI authority. A historical fingerprint mismatch is evidence of evolution and must not be “fixed” by restoring stale runtime code.

## Safety

This document authorizes no deployment, image publication, route activation, provider mutation, database change, email delivery, or production traffic change.
