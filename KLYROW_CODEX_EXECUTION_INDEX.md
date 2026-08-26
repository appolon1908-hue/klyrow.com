# Klyrow Codex Execution Index

This is the authoritative starting index for implementation.

Codex must read these documents completely before changing application code:

1. `KLYROW_AUTH_CODEX_SPEC.md`
2. every ordered authentication specification linked from that file
3. `KLYROW_MODERN_SAAS_PROGRAM.md`
4. `docs/implementation/KLYROW_FEATURE_MISSIONS.md`
5. `KLYROW_IDENTITY_AUTOMATION_ODOO_CONTROL_PLANE.md`

The identity/automation/Odoo control-plane document is mandatory for every branch. Feature code must publish shared domain events and must not call Odoo or n8n directly.

## Authority boundaries

- Keycloak: authentication, verified identity, MFA and identity-provider linkage.
- Klyrow PostgreSQL: SaaS tenancy, permissions, product state, usage, entitlement and integration state.
- Postal 3.3.7: email delivery engine.
- Codestra middleware: sole cross-system integration boundary.
- n8n: non-authoritative automation.
- Odoo: back-office CRM, customer, accounting, billing, support and operations mirror/management surface.

Billing records must not be stored in Keycloak. Passwords, tokens, secrets and full payment credentials must never be synchronized to Odoo or n8n.

## Required implementation order

### Foundation

1. `feat/klyrow-auth-theme-ui`
2. `feat/klyrow-auth-bff-sessions`
3. `feat/klyrow-tenancy-onboarding`
4. `feat/klyrow-postal-provisioning`

### Core product

5. `feat/klyrow-customer-data-events`
6. `feat/klyrow-consent-preferences`
7. `feat/klyrow-segmentation`
8. `feat/klyrow-content-studio`
9. `feat/klyrow-journeys-automation`
10. `feat/klyrow-experimentation`
11. `feat/klyrow-analytics-attribution`
12. `feat/klyrow-deliverability`

### Platform and commercial

13. `feat/klyrow-developer-platform`
14. `feat/klyrow-integrations`
15. `feat/klyrow-billing-plans-usage`
16. `feat/klyrow-ai-assist`
17. `feat/klyrow-enterprise-admin`
18. `feat/klyrow-stream-separation`

### Control plane and Odoo

19. `feat/klyrow-control-plane-events`
20. `feat/klyrow-odoo-backoffice-sync`

The control-plane branch depends on reviewed identity/tenancy, integration and billing contracts. The Odoo branch depends on reviewed billing, integration, enterprise-admin and control-plane work.

### Operations and release

21. `feat/klyrow-reliability-ha`
22. `feat/klyrow-observability-sre`
23. `feat/klyrow-security-hardening`
24. `feat/klyrow-cross-channel-contract`
25. `release/klyrow-production-readiness`

Before implementing any branch, Codex must update or recreate it from its latest reviewed prerequisites. Existing empty scaffold branches are not proof that implementation exists.

## Platform-owner requirement

The owner account must be configured through verified Keycloak identity values:

```text
KLYROW_PLATFORM_OWNER_ISSUER=https://auth.codestra.co/realms/codestra
KLYROW_PLATFORM_OWNER_SUBJECT=<exact-keycloak-subject>
KLYROW_PLATFORM_OWNER_EMAIL=<verified-owner-mailbox>
```

Never assign platform ownership by email matching alone. Require MFA and step-up authorization for high-risk billing, suspension, role, credential, conflict-resolution and production actions.

## Production restriction

No feature branch may deploy directly to production. Production is allowed only from `release/klyrow-production-readiness` after independent review, staging, migration, backup/restore, security, tenant-isolation, Keycloak, middleware, n8n, Odoo, Postal, billing reconciliation, restricted canary, rollback and explicit owner go/no-go evidence.
