# Communications API v1 — Step 3 Klyrow Email Provider

## Authority

This branch implements the Klyrow/provider side of the frozen Communications API v1 contract from:

`appolon1908-hue/SDK-repository:feat/communications-api-v1-contracts@63c793e88cca5daecfb5c8a688b8674ab288c522`

Klyrow remains the principal email runtime around Postal/Mautic. Middleware remains the only cross-system write authority.

## Required provider mapping

1. Accept only the reviewed Middleware service identity and tenant context.
2. Preserve provider-local idempotency and reject conflicting key reuse.
3. Map canonical sender/domain/template/content fields into the Klyrow API without exposing raw Postal admin APIs.
4. Return durable Klyrow message/provider references suitable for Middleware read-back.
5. Preserve safe mode and production gate behavior.
6. Surface sender/domain verification evidence needed by the canonical read model: SPF, DKIM selector/state, DMARC, TLS/send-path and PTR/rDNS evidence where available.
7. Surface deliverability/reputation snapshots through governed read endpoints.
8. Keep bounces, complaints, delivery events and suppressions durable and tenant-scoped.
9. Sign outbound delivery events and persist event IDs for replay protection.
10. Provide authoritative message read-back sufficient to resolve uncertain submission outcomes.
11. Do not accept direct product/SDK bypasses around Middleware for privileged unified-communications writes.

## Required tests

- valid Middleware service identity accepted
- invalid audience/scope/service identity rejected
- tenant mismatch rejected
- same idempotency key/same payload returns same logical result
- same key/different payload conflicts
- safe mode never invokes Postal
- verified sender/domain policy
- suppression and consent behavior
- provider timeout before acceptance
- provider timeout after possible acceptance with read-back resolution
- delivered/bounced/complained event signing and replay rejection
- domain/DKIM/deliverability read model validation
- no secret/provider credential leakage in responses/logs

## Production boundary

Do not change `KLYROW_SAFE_MODE` or `KLYROW_PRODUCTION_GATE_APPROVED` as part of this branch. Production sending remains separately gated.