# Codestra observability and Odoo integration

This contract adds the production-facing observability boundary for Klyrow. It
keeps the existing outbox, authentication, audit, and safe-mode authorities in
place; it does not add a second event writer or a direct Odoo client.

## Runtime ownership

| Component | Runtime responsibility | May write Odoo? |
| --- | --- | --- |
| Codestra-Prometheus | Scrape Klyrow metrics, evaluate recording rules and technical alerts | No |
| Codestra-Alertmanager | Deduplicate and route firing/resolved alerts | No |
| Codestra-Grafana | Read-only operational dashboards | No |
| Codestra-Telemetry / Codestra-Alloy | Collect and forward metrics, logs and traces | No |
| Codestra-Loki / Codestra-Tempo | Store and query logs/traces | No |
| Codestra-* exporters | Expose host, container, Redis, Postgres and probe metrics | No |
| Superset | Read-only business analytics | No |
| Codestra-OpenBao | Secret and credential reference authority | No |
| Middleware | Normalize, deduplicate, enrich and deliver approved summaries | Yes; sole writer |
| Odoo | Kyyow Superadmin control center and system of record for summaries | Receives through Middleware |

The authoritative machine-readable boundary is
[`monitoring/codestra-observability-boundary.v1.json`](../monitoring/codestra-observability-boundary.v1.json).

## Klyrow API surface

These routes are internal `/v1` routes. The edge must keep them private; the
gateway requires a service identity with the exact observability scope shown.
All Odoo-bound work is written to the existing `IntegrationOutbox` with target
`ODOO`. A Middleware worker owns the private mTLS hop and the Odoo JSON-2
adapter.

| Method | Path | Scope | Purpose |
| --- | --- | --- | --- |
| POST | `/v1/internal/integrations/alertmanager/events` | `klyrow.observability.write` | Accept firing/resolved Alertmanager events, validate bounded labels, and enqueue an idempotent Odoo alert summary |
| POST | `/v1/internal/integrations/kpis/snapshots` | `klyrow.observability.write` | Accept only approved Prometheus recording-rule references and enqueue KPI snapshots |
| GET | `/v1/internal/integrations/odoo/health` | `klyrow.observability.read` | Report private transport configuration, outbox backlog and dead letters |
| GET | `/v1/internal/integrations/odoo/checkpoints` | `klyrow.observability.read` | Report event-type/state checkpoints without exposing payloads |
| POST | `/v1/internal/integrations/odoo/reconcile` | `klyrow.observability.write` | Request an idempotent Middleware reconciliation run |
| GET | `/v1/internal/integrations/observability/contract` | `klyrow.observability.read` | Return the runtime ownership and forbidden-writer contract |

Alert identity is fingerprint + state + normalized start time. KPI identity is
the supplied snapshot ID. Replays return the existing operation, while a
different payload under the same identity returns a conflict. The handler
never accepts tenant, customer, recipient, trace, request, raw URL or secret
labels, and request metrics use bounded route templates instead of raw paths.

## Readiness and activation

Source and contract checks are production-ready when they pass, but that is not
the same as certifying a live deployment. Before activation, operators must
record all gates below in the release evidence:

- immutable release/image digest and rollback target;
- private Prometheus scrape credential and Alertmanager mTLS route;
- Middleware service identity, tenant binding and exact scopes;
- Middleware-to-Odoo JSON-2 adapter credentials and private network path;
- firing/resolved deduplication evidence for the same alert;
- KPI snapshot read-back evidence and reconciliation evidence;
- backup/restore and rollback rehearsal;
- independent safe email-delivery approval. This integration does not enable
  live mail delivery.

Validate the static boundary with:

```bash
python scripts/validate-codestra-integration.py
python -m pytest -q tests/test_observability_integration.py tests/test_contract_conformance.py
```
