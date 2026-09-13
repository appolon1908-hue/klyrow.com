# Klyrow production readiness

Decision: **FAIL — not authorized for production release.**

This file distinguishes local source checks from deployment acceptance. `FAIL`
includes gates without fresh runtime evidence; it does not assert that the
deployed service was tested and found broken. Scope: Klyrow repository changes,
not installation or activation of other Codestra repositories.

## Source checks

| Check | Status | Evidence / remaining work |
| --- | --- | --- |
| Repository/API/secret-reference inventory | PASS | `docs/architecture/current-state.md`, generated `docs/api/` and `docs/security/secret-references.json` |
| Middleware-only Odoo writer ADR | PASS | `docs/adr/ADR-001-middleware-only-odoo-writer.md` |
| OpenAPI validation and audience separation | PASS | `python scripts/validate-api-contracts.py`; 351 operations across four exports |
| Template-version history API | PASS | Cursor pagination, immutable content, authentication, cross-tenant and wrong-parent tests |
| Database outage readiness | PASS | `/health/ready` reports redacted 503; liveness is independent |
| Source/packaging Odoo-writer guardrails | PASS | `tests/test_odoo_writer_architecture.py`; not a live network/ACL test |
| Generated TypeScript API types/client compilation | PASS | Pinned openapi-typescript generation and TypeScript compiler in contract CI |
| Contract drift/compatibility checks | PASS | Generated-file comparison and conservative operation/schema/security diff; initial exports have no predecessor at baseline |
| Python regression checks | PASS | Python 3.12 full run: 1,237 passed, 19 skipped, one exact-fingerprint policy expectation failed; that expectation was updated to the reviewed exclusions and `pytest -q tests --lf --lfnf=none` passed the remaining test. All 1,238 executed cases now pass; skipped runtime/PostgreSQL gates are not certified |
| Full-history and staged-change secret scan | PASS | Five reviewed historical findings were TestClient `Idempotency-Key` values, not credentials; exact commit/file/line exclusions in `.gitleaksignore`, no broad file/rule suppression |
| All M06 target operations and typed response schemas | FAIL | Existing API remains broader/different than the target; template history added, remaining contract gaps inventoried |
| AsyncAPI and normalized M07 summary production | FAIL | Existing signed event protocol differs from the new envelope; coordinated producer/consumer migration remains |
| Full Odoo KPI writer/reconciler | FAIL | Included worker handles inbound mail, not the complete daily KPI loop; existing Odoo model mappings unavailable in this repo |
| OTLP instrumentation and end-to-end traces | FAIL | SDK/exporter configuration and runtime trace proof remain |
| PostgreSQL RLS | FAIL | Runtime role is restricted, but table policies are not implemented in checked-in migrations |

## Required production gates

| Gate | Status | Evidence needed |
| --- | --- | --- |
| Keycloak login, issued claims and session enforcement | FAIL | Approved deployment token/login tests |
| OpenBao workload authentication and Odoo credential ACL | FAIL | Middleware read succeeds; Klyrow/telemetry reads denied |
| Caddy → Kong edge authentication, TLS and tenant-header reconstruction | FAIL | Live valid/invalid JWT/API-key and wrong-tenant tests |
| Klyrow API/SMTP send and provider event | FAIL | Approved real-domain submission and callback evidence |
| Customer webhook signing, delivery, rotation and replay | FAIL | Independent dispatcher and receiver evidence |
| Middleware → existing Odoo KPI models | FAIL | Idempotent upsert, replay, metrics and reconciliation |
| Alertmanager → Middleware → Odoo firing/resolved incident | FAIL | Same incident identity and no duplicate mutation |
| Klyrow → Odoo blocked | FAIL | Deployed firewall/NetworkPolicy and credential denial |
| Grafana/Prometheus/Alertmanager/Superset → Odoo write blocked | FAIL | Deployed service identities and denial tests |
| Superset SQL writes blocked | FAIL | SELECT-only grants tested against the analytics store |
| Prometheus/Alertmanager/Loki/Tempo ready; Alloy forwarding | FAIL | Fresh private telemetry and authenticated scrape/query evidence |
| Odoo outage does not block mail; backlog drains after recovery | FAIL | Controlled outage/recovery test with zero accepted-event loss |
| Observability outage does not block mail | FAIL | Controlled telemetry outage test |
| Backup restore and rollback | FAIL | Fresh recovery drill using the approved immutable release |
| Exact-commit CI, image scans/SBOM/signing and release promotion | FAIL | Remote CI and approved deployment evidence for the final commit |
| Telnexa API/SMPP/DLR and duplicate-billing tests | NOT APPLICABLE | Owned by Telnexa; still required for a platform-wide release |
| VICIdial calling integration | NOT APPLICABLE | Owned by the calling platform; not certified by Klyrow tests |

## Changes and rollback

New APIs:

- `GET /v1/templates/{template_id}/versions?limit=&cursor=`
- `GET /v1/templates/{template_id}/versions/{version_id}`

Database migrations: none. Existing immutable `template_versions` rows are read
without changing historical content. Runtime changes also add private-namespace
OpenAPI classification and a redacted 503 readiness response.

Deployment changes: none executed. CI adds a required `contracts` prerequisite
before building release candidates. No email activation flag, production secret,
provider configuration, DNS record or external service was changed.

Rollback by reverting this source change and regenerating schema/type snapshots;
redeploy the previous approved immutable image through the normal promotion
process if needed. There is no data rollback and no accepted-message deletion.
