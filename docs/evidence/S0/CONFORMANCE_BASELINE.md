# S0 Source-Discovered Conformance Baseline

- Measured: 2026-08-30T15:32:38+02:00
- Implementation commit: `0cd48c6247ac360d94931666caa7934979c4cd9b`
- Manifest: `codestra/integration/klyrow-smtp.integration.v1.json`
- Source scope: every Python file under `apps/gateway/app/`

## C1 — Published events

Finite event values discovered at `emit_middleware` call sites:

```text
klyrow.email.bounced
klyrow.email.clicked
klyrow.email.deferred
klyrow.email.delivered
klyrow.email.held
klyrow.email.opened
klyrow.email.queued
klyrow.email.unknown
klyrow.usage.recorded
```

Declared but not present in the finite discovered set:

```text
klyrow.email.complained
klyrow.email.inbound_received
klyrow.email.sent
klyrow.email.unsubscribed
```

Finite discovered values absent from the manifest:

```text
klyrow.email.held
klyrow.email.unknown
klyrow.usage.recorded
```

The source also contains three open-ended emitters:

```text
apps/gateway/app/main.py:461
apps/gateway/app/main.py:751
apps/gateway/app/provider.py:660
```

The strict C1 xfail rejects both an unequal finite set and any open-ended emitter. This baseline is broader than a hand-maintained expected list because it reflects the K0 trunk candidate after its 65 additional commits.

## C2 — Commands

Source discovery found neither `POST /v1/commands` nor `GET /v1/operations/{command_id}` and found no registered handler for any of the five declared commands.

## C3 — Message statuses

Declared but not found as core `Message.status` values:

```text
bounced
cancelled
complained
deferred
indeterminate
provider_accepted
submitted
suppressed
```

Core `Message.status` values absent from the manifest:

```text
accepted_test
complaint
hard_bounce
quarantined
rejected
sent
soft_bounce
```

The status path at `apps/gateway/app/main.py:368` also has an open-ended fallback. The strict C3 xfail requires a closed and exactly equal status model.

## C4 — Middleware headers

Headers discovered inside `emit_middleware`:

```text
Authorization
Content-Type
X-Klyrow-Event-Id
X-Klyrow-Signature
X-Klyrow-Timestamp
X-Source-System
```

Required but missing:

```text
Idempotency-Key
X-Correlation-ID
X-Tenant-ID
```

## C5 — Prometheus labels

All 12 Prometheus collectors were discovered from constructor calls. No collector uses a forbidden label, so the forbidden-label conformance check passes. All 12 collectors are missing one or more required platform labels, recorded as the strict C5 xfail for S4.

