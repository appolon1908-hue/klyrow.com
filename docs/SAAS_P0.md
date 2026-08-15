# SaaS P0 capabilities

Klyrow owns tenant-scoped profiles with email, phone, CRM/external/customer identifiers and custom attributes. Upsert resolves matching identifiers and merges duplicates. Typed behavioral events form each profile timeline. Dynamic segments support nested `all`, `any`, and `not` rules, attributes, event counts/windows, comparisons, preview size and samples. Suppressed addresses are excluded.

Journey graphs validate typed nodes and edges for triggers, segment/event entry, waits, email, conditional/percentage/A-B splits, goals, profile updates, webhooks/middleware, segment changes, unsubscribe/suppression and exit. Drafts can publish, pause, resume and roll back. Runs record per-profile history; goal events complete matching runs.

Consent records capture topic, status, source, version, timestamp and proof. Preference changes are audited and revocation suppresses the address. Marketing sends require a profile, latest granted consent and enabled topic preference. Transactional mail has a separate stream and usage entry but never bypasses global suppressions or domain/tenant controls.

The portal exposes onboarding, profiles/consent, segmentation, journeys, analytics, deliverability, developer and MFA panels. Analytics use real internal messages/events. Deliverability queries live MX/SPF/DKIM/DMARC/PTR and persists snapshots/alerts; TLS stays false until trusted certificate verification.

TOTP MFA, hashed recovery codes and revocable sessions harden access. Responses carry request IDs and latency metrics. OpenAPI is `/v1/developer/openapi.json`. Personalization escapes values and rejects active HTML. The hard gate forces safe mode unless both `KLYROW_SAFE_MODE=false` and `KLYROW_PRODUCTION_GATE_APPROVED=true` are intentionally configured after all external checks.
