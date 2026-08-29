# Klyrow Codex Execution Index

This is the authoritative starting index and branch order for implementation.

Codex must read these documents completely before changing application code:

1. `KLYROW_AUTH_CODEX_SPEC.md`
2. every ordered authentication specification linked from that file
3. `KLYROW_MODERN_SAAS_PROGRAM.md`
4. `docs/implementation/KLYROW_FEATURE_MISSIONS.md`
5. `KLYROW_IDENTITY_AUTOMATION_ODOO_CONTROL_PLANE.md`
6. `docs/implementation/KLYROW_CONTROL_PLANE_BRANCH_MISSIONS.md`
7. `docs/implementation/KLYROW_ADMIN_ODOO_N8N_ACCEPTANCE_MATRIX.md`
8. `KLYROW_DIFFERENTIATED_FEATURES_PROGRAM.md`
9. `docs/implementation/KLYROW_DIFFERENTIATED_FEATURE_MISSIONS.md`
10. `docs/implementation/KLYROW_DIFFERENTIATED_ACCEPTANCE_MATRIX.md`

The identity/automation/Odoo control-plane documents are mandatory for every branch. Feature code must publish shared domain events and must not call Odoo or n8n directly.

Branch names and the ordered catalog below are authoritative. Numeric labels inside earlier mission documents are document identifiers only when they differ from this unified execution order.

## Authority boundaries

- **Keycloak:** authentication, verified identity, MFA and identity-provider linkage.
- **Klyrow PostgreSQL:** SaaS tenancy, permissions, product state, profiles/events, consent, usage, entitlement, communication decisions, attention, simulation, provider routing intent, reseller commercial rules, reconciliation and integration state.
- **Postal 3.3.7:** primary email-delivery engine.
- **Codestra middleware:** sole cross-system integration boundary.
- **n8n:** non-authoritative automation.
- **Odoo:** back-office CRM, customer, accounting, billing, support and operations mirror/management surface.

Billing records must not be stored in Keycloak. Passwords, tokens, secrets, private keys and full payment credentials must never be synchronized to Odoo or n8n.

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

### Differentiated communications operating system

21. `feat/klyrow-decision-policy-ledger`
22. `feat/klyrow-simulation-attention-engine`
23. `feat/klyrow-recipient-trust-center`
24. `feat/klyrow-reconciliation-self-healing`
25. `feat/klyrow-provider-mesh-portability`
26. `feat/klyrow-reseller-white-label`

Required dependencies:

- decision/policy ledger: auth sessions, tenancy, consent/preferences, billing, stream separation and control-plane events;
- simulation/attention: decision ledger, segmentation, journeys, experimentation, analytics and billing;
- recipient trust: consent/preferences, decision ledger, content/message lifecycle and control-plane events;
- reconciliation: Postal provisioning, integrations, billing, enterprise admin, control-plane events and Odoo synchronization;
- provider mesh: Postal provisioning, deliverability, developer platform, stream separation, decision ledger and control-plane events;
- reseller/white label: billing, enterprise admin, Odoo synchronization, provider mesh and decision ledger.

### Operations and release

27. `feat/klyrow-reliability-ha`
28. `feat/klyrow-observability-sre`
29. `feat/klyrow-security-hardening`
30. `feat/klyrow-cross-channel-contract`
31. `release/klyrow-production-readiness`

Before implementing any branch, Codex must update or recreate it from its latest reviewed prerequisites. Existing scaffold branches are not proof that implementation exists.

## Differentiated product invariant

Once enabled for a send path, every outbound communication must follow:

```text
intent
  -> tenant/permission resolution
  -> consent/suppression/stream policy
  -> entitlement/quota/billing reservation
  -> attention arbitration
  -> risk and sender/domain checks
  -> immutable decision
  -> provider outbox
  -> provider reconciliation
  -> signed message passport
  -> middleware/n8n/Odoo evidence
  -> end-to-end explanation timeline
```

No API, SMTP credential, campaign, journey, AI action, n8n workflow or administrator may bypass the authoritative Klyrow decision lifecycle.

## Platform-owner requirement

The owner account must be configured through verified Keycloak identity values:

```text
KLYROW_PLATFORM_OWNER_ISSUER=https://auth.codestra.co/realms/codestra
KLYROW_PLATFORM_OWNER_SUBJECT=<exact-keycloak-subject>
KLYROW_PLATFORM_OWNER_EMAIL=<verified-owner-mailbox>
```

Never assign platform ownership by email matching alone. Require MFA and step-up authorization for high-risk billing, wallet, margin, suspension, role, credential, provider-route, repair, conflict-resolution and production actions.

## One-branch execution rule

For each branch Codex must:

1. print host, repository, branch, starting SHA and status;
2. inventory existing behavior;
3. mark requirements `IMPLEMENTED`, `PARTIAL`, `MISSING` or `UNSAFE`;
4. update/recreate from reviewed prerequisites;
5. implement only that branch mission;
6. include additive migration and rollback;
7. include tests, OpenAPI, domain events, metrics, alerts and runbooks;
8. push only the branch;
9. open/update one independently reviewable PR;
10. post exact evidence;
11. stop without beginning the next branch.

## Production restriction

No feature branch may deploy directly to production. Production is allowed only from `release/klyrow-production-readiness` after independent review, staging, migrations, backup/restore, security, tenant/reseller isolation, Keycloak, middleware, n8n, Odoo, Postal/provider, decision-enforcement, billing/wallet reconciliation, restricted canary, rollback and explicit owner go/no-go evidence.

The existence of a branch, a green CI result or a Codex completion report is not production authorization.
