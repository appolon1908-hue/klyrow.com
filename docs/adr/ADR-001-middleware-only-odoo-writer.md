# ADR-001: Middleware is the only external Odoo writer

Status: accepted for implementation. Date: 2026-09-13.

## Context

Klyrow already uses FastAPI/Vue/PostgreSQL/Postal/Mautic and ships a separately
owned Middleware source overlay. Usage and delivery events are durably received,
but the included Odoo worker handles inbound mail only. A target blueprint must
not be mistaken for evidence that daily KPI synchronization or production ACLs
already work.

## Decision

Keep the current stack. Preserve existing public response shapes, authentication
and durable acceptance. Generate an inspectable API baseline from the canonical
composition root and validate it in CI before adding new contracts.

Only Middleware may load Odoo writer credentials or call Odoo mutation methods.
Klyrow produces durable normalized events and business summaries. Odoo outages
must not affect mail acceptance or delivery. Telemetry services never hold this
credential. Enforce the rule independently through credential grants, service
identity, Odoo authorization, network policy/firewall and architecture tests.

Use supported Odoo JSON-2 for the new KPI adapter, with configured mappings to
existing KPI models. Do not change the existing inbound-mail JSON-RPC transport
without verifying its Odoo deployment and method compatibility. Each logical
upsert needs server-side transactional idempotency; a separate search then
create across API calls is insufficient.

New internal endpoints use `/internal/v1/`. Keep existing private endpoints
authenticated and explicitly documented during migration. Caddy/Kong is the
target public edge; do not deploy a replacement based on source tests alone.

## Consequences

The owned integration overlay can be edited/tested here, but its deployment and
Odoo model mappings require verification in their owning systems. Generated
contracts expose remaining typed-response and pagination gaps rather than
inventing implementation. Source and runtime acceptance remain separate gates.

Rollback source changes through a revert and regenerate the contract artifacts.
Never revert durable event records or remove accepted work to roll back a worker.
Keep production delivery gates disabled until all required runtime tests pass.
