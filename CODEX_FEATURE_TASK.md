# Codex Feature Task — Reseller and White-Label Platform

## Branch

`feat/klyrow-reseller-white-label`

## Planning baseline

`b4a8614c2dd703cf6bc021828ffd4d718002e39d`

This is an implementation scaffold, not completed code.

## Prerequisites

Use the latest reviewed baseline containing:

- `feat/klyrow-billing-plans-usage`
- `feat/klyrow-enterprise-admin`
- `feat/klyrow-odoo-backoffice-sync`
- `feat/klyrow-provider-mesh-portability`
- `feat/klyrow-decision-policy-ledger`

## Mandatory reading

Read all files required by the authoritative execution index and the complete **Reseller and White-Label Platform** mission and acceptance matrix.

## Objective

Implement a secure platform-owner → reseller → customer hierarchy, delegated administration, immutable price books, wallet and margin ledgers, reseller/customer commercial views, truthful white-label branding and approved Odoo accounting synchronization through middleware.

## Required delivery

- additive migrations and rollback;
- reseller accounts and effective-dated child-tenant relationships;
- no arbitrary unlimited nesting;
- immutable wholesale/retail price-book versions;
- contracts, credit terms and settlement metadata;
- append-only wallets, reservations, releases, credits, refunds and adjustments;
- dual control and step-up for material adjustments;
- reproducible provider/platform/wholesale/retail margin ledger;
- delegated admin grants with explicit permission and expiry;
- reseller/customer/owner dashboards and Customer 360;
- isolated versioned brand profiles;
- verified custom-domain and TLS activation with safe fallback;
- truthful sender/legal/recipient-trust identity;
- Odoo partner, customer, price-list, subscription, usage, invoice, payment, credit, settlement and support mappings through middleware;
- test mode with zero real charges or posted invoices;
- OpenAPI, events, metrics, alerts and runbooks;
- full platform/reseller/customer permission, wallet concurrency, pricing, margin, transfer, Odoo replay, brand isolation, custom-domain, browser, accessibility, security and secret-scan tests.

## Authority boundaries

Klyrow remains authoritative for usage, entitlements, wallet reservations, pricing versions, margins and communication permission. Odoo is accounting/back-office through middleware. A reseller is never platform owner and cannot view platform secrets or another reseller's customers.

## Hard restrictions

Do not deploy, merge, activate real reseller billing, post real Odoo invoices, enable unverified custom domains, restart services, change DNS/TLS, access Odoo/Postal/Keycloak databases directly, expose wholesale pricing to customers without permission, hide required sender/legal identity or print/commit secrets.

## Git delivery and report

Push only this branch and open/update one draft PR. Include exact permission-matrix, IDOR, price-version, wallet locking, dual-control, margin, currency, transfer, Odoo replay, test-mode, brand isolation, domain verification, accessibility, migration, rollback and no-production evidence. Stop afterward.
