# Codex Feature Task — Simulation and Recipient Attention Engine

## Branch

`feat/klyrow-simulation-attention-engine`

## Planning baseline

`b4a8614c2dd703cf6bc021828ffd4d718002e39d`

This is an implementation scaffold, not completed code.

## Prerequisites

Use the latest reviewed prerequisite baseline containing:

- `feat/klyrow-decision-policy-ledger`
- `feat/klyrow-segmentation`
- `feat/klyrow-journeys-automation`
- `feat/klyrow-experimentation`
- `feat/klyrow-analytics-attribution`
- `feat/klyrow-billing-plans-usage`

Recreate/update this branch from those reviewed prerequisites before editing.

## Mandatory reading

Read the authoritative index, main program, core feature missions, control-plane specification, differentiated program, the **Simulation and Recipient Attention Engine** mission, and the differentiated acceptance matrix completely.

## Objective

Implement a deterministic, no-side-effect digital twin for campaigns, journeys, segments, policies, prices and expected integrations, plus runtime recipient attention-budget arbitration. Extend the existing engines and adapters; do not duplicate them.

## Required delivery

- additive migrations and rollback;
- immutable simulation runs and version snapshots;
- historical and synthetic replay with fixed clock;
- recording adapters that prohibit provider, middleware, n8n, Odoo and billing side effects;
- recipient funnel, policy outcomes, volume, cost, queue, journey, collision and integration-impact results;
- current-versus-proposed comparison;
- attention-policy versions;
- atomic recipient attention claims;
- priority, quiet hours, cooldown, category and frequency rules;
- `SEND_NOW`, `DEFER_UNTIL`, `DROP_SUPERSEDED`, `COMBINE_IN_DIGEST` and `REQUIRE_APPROVAL` outcomes;
- simulation lab and attention-center UI;
- English/Spanish, responsive and WCAG 2.2 AA behavior;
- OpenAPI, events, metrics, alerts and runbooks;
- observe-only runtime mode;
- exact deterministic and zero-side-effect evidence.

## Critical safety invariant

A simulation must never create a real message, provider outbox item, usage charge, middleware event, n8n execution or Odoo record. Runtime attention evaluation must never bypass consent, suppression, billing, sender/domain, risk or production gates.

## Integration boundaries

Use the same segment, journey, policy, content and pricing contracts as runtime through explicit simulation interfaces. Record expected n8n/Odoo events instead of delivering them. Invoke the decision ledger for runtime arbitration.

## Hard restrictions

Do not deploy, merge, restart services, enable runtime enforcement in production, send messages, create real charges, activate n8n/Odoo workflows, modify Postal or access external databases directly.

## Git delivery and report

Push only this branch and open/update one draft PR. Include the full differentiated completion report with exact zero-side-effect assertions, deterministic replay results, concurrency and time-zone tests, browser/accessibility evidence, migrations/rollback, events, metrics and no-production confirmations. Stop afterward.
