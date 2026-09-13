# ADR-002: Export current contracts and expose immutable template history

Status: accepted. Date: 2026-09-13.

## Context

The existing composed application has more than 300 documented operations and
several compatibility/browser surfaces. Replacing its contract wholesale with
the mission's target endpoint list would advertise unimplemented behavior and
break callers. Template versions already exist as immutable rows, but their
listing and individual retrieval endpoints were missing.

## Decision

Export the canonical composed OpenAPI into separate public, private, browser and
callback contracts. Retain existing schemas and response shapes. Treat future
target-only endpoints as gaps until implemented. JSON serialization in `.yaml`
files is intentional: JSON is valid YAML 1.2 and produces deterministic output.

CI rejects stale generated contracts, validates OpenAPI and operation IDs,
checks existing operations and reachable schemas for changes, regenerates
TypeScript API types and compiles the client. The compatibility checker is
conservative: existing schema changes require a versioned migration even when a
reviewer believes them additive. Adding operations/optional parameters is
allowed. It does not certify the unfinished AsyncAPI migration.

Read existing template-version rows through two authenticated, tenant-scoped
endpoints. Return typed content and UTC timestamps. Order history by decreasing
immutable version number, fetch `limit + 1` rows, and return an opaque cursor
only when another page exists. Enforce the parent template and tenant on every
request, including lookup by version ID. A cursor is a position, never an
authorization credential. Do not rename existing template identifiers or add a
schema migration for a read-only capability.

Readiness returns 503 on SQLAlchemy dependency failure and never includes the
database exception body. Liveness remains independent of the database and
external business/observability systems.

## Consequences and rollback

Generated artifacts are large because they describe existing operations; review
handler changes together with generated differences. The new public endpoints
increase documented operations from 349 to 351. No message admission, delivery,
Odoo transport, tenant identity or activation gate changes are introduced.

Rollback is a source revert and regeneration of the schemas/types. Historical
templates and accepted-message records require no data rollback.
