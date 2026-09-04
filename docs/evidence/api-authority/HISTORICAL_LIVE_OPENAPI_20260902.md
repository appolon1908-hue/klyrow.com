# Historical live Klyrow OpenAPI authority — 2026-09-02

## Evidence identity

This record preserves the non-executable evidence from the historical live-gateway snapshot without adding a second importable application tree.

- Observed runtime source snapshot: `ca2254e5f3beeadd0122578ee96d7a59751cda60`
- Historical evidence PR head: `26faa33f922af0210c5efa9ac9f3164b3b3ec0af`
- Historical exact-head Actions run: `33588339797` — PASS
- Observed runtime: `klyrow-gateway-1`
- Files compared with the observed container: 25
- OpenAPI-documented HTTP operations: 258
- Sorted documented `METHOD PATH` SHA-256: `7d005a48538f0fcc15370a395cb0f33f1928b368dc07d631f0384b58a241b2e6`

The original evidence stated that all 25 captured files matched the observed container byte-for-byte before the snapshot was committed. The historical branch and commit remain available in Git history for forensic comparison.

The fingerprint above covers the operations emitted by the historical OpenAPI document only. The observed application also exposed routes omitted from that schema, including its runtime discovery endpoint and at least one hidden compatibility endpoint (`POST /v1/email/send`, registered with `include_in_schema=False`). The historical evidence did not inventory the complete `APIRoute` table, so it does **not** establish an authoritative total runtime-operation count and must not be used to prove hidden-route compatibility.

## Authority boundary

The canonical application remains `apps.gateway.app.platform:app`, sourced from `apps/gateway`. Current operation-level audience, authentication, CSRF, webhook-signature, and idempotency authority must be changed only through the canonical source and its focused remediation PRs.

The historical snapshot classified documented routes as `PUBLIC`, `BROWSER_BFF`, `INTERNAL`, `ADMIN`, `WEBHOOK`, `TRACKING`, or `LEGACY`. Those values are historical observations. They do not prove the enforced dependency of every route, they do not cover hidden routes, and they are not permission to restore the old snapshot over protected source.

## Non-duplication rule

The prior branch carried an importable `runtime_authority/` copy of the gateway. That duplicate tree is deliberately excluded from this reconciled evidence record because it could be imported, tested, packaged, or certified instead of the canonical application.

No executable source, workflow, image, Compose file, migration, or runtime dependency is preserved here. Reproduction must compare the historical Git commit or archived artifact directly; it must not create another application package inside the repository.

## Change control

Any current operation added, removed, renamed, reclassified, or assigned a different authentication model requires review against the current canonical route table and OpenAPI authority. Candidate validation must inventory the deployable `apps.gateway.app.platform:app`, including hidden `APIRoute` entries, and derive authentication metadata from the dependencies actually enforced by that application. A historical fingerprint mismatch is evidence of evolution and must not be “fixed” by restoring stale runtime code.

## Safety

This document authorizes no deployment, image publication, route activation, provider mutation, database change, email delivery, or production traffic change.
