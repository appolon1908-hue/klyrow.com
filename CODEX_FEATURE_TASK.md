# Codex Feature Task — Recipient Trust Center

## Branch

`feat/klyrow-recipient-trust-center`

## Planning baseline

`b4a8614c2dd703cf6bc021828ffd4d718002e39d`

This is an implementation scaffold, not completed code.

## Prerequisites

Use the latest reviewed baseline containing:

- `feat/klyrow-consent-preferences`
- `feat/klyrow-decision-policy-ledger`
- `feat/klyrow-content-studio`
- message lifecycle/provider event support
- `feat/klyrow-control-plane-events`

## Mandatory reading

Read all files required by `KLYROW_CODEX_EXECUTION_INDEX.md`, especially the **Recipient Trust Center** mission and differentiated acceptance matrix.

## Objective

Implement a privacy-safe public recipient experience for `Why am I receiving this?`, consent/preferences, frequency reduction, unsubscribe, communication-history summary, privacy requests, abuse reporting and support. Use existing Klyrow consent, decision, content, middleware and Odoo contracts rather than duplicating authority.

## Required delivery

- additive migrations and rollback;
- scoped, expiring, replay-resistant token/session design;
- safe explanation projection from the decision ledger;
- global/topic/frequency/language/quiet-hour preferences;
- unsubscribe, resubscribe and double opt-in evidence;
- privacy export/correction/deletion workflows with retention/legal-hold controls;
- abuse and support reporting;
- durable middleware events for approved n8n/Odoo workflows;
- immediate authoritative consent/suppression enforcement in Klyrow;
- public and administrative APIs;
- tenant configuration and owner SLA/abuse/privacy views;
- mobile-first English/Spanish WCAG 2.2 AA interface;
- rate limiting, anti-enumeration and safe error behavior;
- OpenAPI, events, metrics, alerts, runbooks and exact tests.

## Privacy rules

Never expose sensitive segment criteria, medical/financial/risk attributes, internal fraud classifications, employee notes, unrelated recipients, raw decision facts, credentials or provider internals. Public history is a safe summary, not a full profile dump.

## Integration boundaries

Klyrow remains consent/privacy authority. Odoo is a support/work-management surface through middleware. n8n may notify or route work but cannot change consent or complete deletion by direct mutation. Postal links point to Klyrow trust endpoints only.

## Hard restrictions

Do not deploy, merge, activate a public production domain, restart services, access Odoo/Postal/Keycloak databases, print tokens/secrets, automatically delete legally retained data or bypass suppression/consent rules.

## Git delivery and report

Push only this branch and open/update one draft PR. Include exact token security, redaction, cross-tenant, consent enforcement, Odoo/n8n outage durability, localization, mobile, keyboard, accessibility, migration, rollback and no-production evidence. Stop afterward.
