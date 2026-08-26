# Klyrow Differentiated Feature Acceptance Matrix

This matrix is mandatory for the six differentiated feature branches. A feature is not complete merely because its API or UI exists.

## 1. Shared authority matrix

| Domain | Authoritative system | Permitted mirrors/consumers | Forbidden behavior |
|---|---|---|---|
| Human credentials, MFA, verified email, OIDC session | Keycloak | Klyrow stores canonical `(issuer, subject)` and safe profile metadata | Passwords, tokens or billing data in events/Odoo/n8n |
| Tenant, membership, permissions | Klyrow | Odoo may receive customer/team summaries through middleware | Odoo/n8n directly granting Klyrow permissions |
| Consent, preferences, suppressions | Klyrow | Recipient trust UI and safe Odoo support summaries | Provider, n8n or Odoo bypassing send-time enforcement |
| Communication intent and decision | Klyrow | Middleware/Odoo may receive safe audit summaries | Direct send without a valid Klyrow decision |
| Usage, entitlements, wallet reservation | Klyrow | Odoo accounting and owner reporting | Odoo record alone granting entitlement |
| Posted invoices/payments/accounting | Odoo after approved Klyrow request | Klyrow stores immutable mapping and reconciliation status | Direct Klyrow writes to Odoo database |
| Delivery provider state | Postal 3.3.7 or approved adapter | Klyrow normalized lifecycle and mappings | Provider callback changing tenant/consent/billing authority |
| Automation execution | n8n | Klyrow stores request/result/correlation state | n8n direct database access or authoritative business decisions |
| Cross-system delivery | Codestra middleware | Klyrow, n8n, Odoo | Feature modules calling Odoo/n8n directly |
| Reconciliation findings and repair evidence | Klyrow | Odoo work items through middleware | Destructive/financial/identity auto-repair |
| Reseller pricing, margins, wallets | Klyrow | Odoo accounting mirror/settlement | Mutable balance without append-only transaction |

## 2. Common release flags

Every differentiated feature must expose explicit configuration and feature flags. Recommended logical flags include:

```text
KLYROW_DECISION_LEDGER_ENABLED=false
KLYROW_POLICY_ENFORCEMENT_MODE=OBSERVE_ONLY
KLYROW_MESSAGE_PASSPORTS_ENABLED=false
KLYROW_SIMULATION_ENABLED=false
KLYROW_ATTENTION_ENGINE_MODE=OBSERVE_ONLY
KLYROW_RECIPIENT_TRUST_CENTER_ENABLED=false
KLYROW_RECONCILIATION_ENABLED=false
KLYROW_AUTOMATIC_SAFE_REPAIR_ENABLED=false
KLYROW_PROVIDER_MESH_ENABLED=false
KLYROW_PROVIDER_FAILOVER_ENABLED=false
KLYROW_CONFIGURATION_APPLY_ENABLED=false
KLYROW_RESELLER_ENABLED=false
KLYROW_RESELLER_REAL_BILLING_ENABLED=false
KLYROW_WHITE_LABEL_CUSTOM_DOMAINS_ENABLED=false
```

Exact names may follow the repository's configuration conventions, but equivalent safety controls are required.

Defaults in feature branches, tests and ordinary staging must remain non-destructive and non-billing.

## 3. Communication decision ledger acceptance

| Requirement | Evidence required |
|---|---|
| Every release-scoped send path creates an intent | Contract test inventory and coverage report |
| Provider enqueue requires current valid decision | Negative bypass tests for API, SMTP, campaign, journey, AI and admin send |
| Consent/suspension revalidated at enqueue | Race tests showing stale allow is blocked |
| Stable reason codes | Versioned schema and OpenAPI examples |
| Policy versions immutable | PostgreSQL and API mutation tests |
| Approval requires permission and step-up | Browser/API/security tests |
| Quota reservation atomic | Concurrent PostgreSQL integration test |
| Explanation does not leak secrets or unrelated PII | Redaction and cross-tenant tests |
| Message passport verifies and detects tampering | Signature unit/integration tests |
| Middleware/Odoo event is safe and idempotent | Contract tests and sample event fixtures |
| Observe-only migration does not break existing sends | Backward-compatibility staging evidence |
| Enforcement activation has rollback | Runbook and feature-flag rollback proof |

## 4. Simulation and attention acceptance

| Requirement | Evidence required |
|---|---|
| Simulation has zero provider side effects | Provider/outbox assertions and isolated test doubles |
| Simulation has zero middleware/n8n/Odoo side effects | Outbox and connector assertions |
| Replay deterministic | Repeated-run equality test with fixed clock and versions |
| Historical and synthetic modes isolated | Data fixture and authorization tests |
| Cost is labeled estimate | UI and API schema checks |
| Journey loops/unreachable nodes reported | Graph-analysis tests |
| Recipient collisions detected | Multi-campaign/journey fixture |
| Attention priority deterministic | Rule matrix tests |
| Quiet hours and time zones correct | DST and boundary tests |
| Concurrent claims duplicate-safe | PostgreSQL locking/idempotency tests |
| Digest does not combine incompatible purposes | Security/transactional/marketing tests |
| Runtime starts in observe-only mode | Configuration and staging evidence |

## 5. Recipient trust center acceptance

| Requirement | Evidence required |
|---|---|
| Token scoped and expiring | Cryptographic/token lifecycle tests |
| Cross-tenant replay rejected | Security test |
| Explanation is safe projection | Redaction fixture covering sensitive attributes |
| Global unsubscribe immediately enforced | End-to-end consent/send-policy test |
| Topic preferences enforced | Send-time policy tests |
| Double opt-in evidence retained | Ledger and browser tests |
| Privacy request durable during Odoo/n8n outage | Outbox/retry test |
| Abuse report can create policy-approved suppression | Integration test |
| Recipient history is privacy-safe | API response contract test |
| English and Spanish complete | Localization coverage test |
| Mobile/keyboard/WCAG 2.2 AA | Browser and accessibility evidence |
| Legal/retention hold blocks unsafe deletion | Workflow test and audit evidence |

## 6. Reconciliation and self-healing acceptance

| Requirement | Evidence required |
|---|---|
| External state read only through approved APIs/connectors | Code search and adapter contract test |
| Finding deduplication stable | Repeated-run test |
| Stale snapshot identified | Time-based test |
| Repair classification enforced | Rule matrix test |
| Financial repair requires approval/step-up | Security and browser test |
| Identity/owner repair never automatic | Negative tests |
| Destructive deletion never automatic | Negative tests |
| Repair preconditions rechecked before execution | Concurrent state-change test |
| Repair idempotent | Repeated command test |
| Partial failure compensates or stops safely | Worker failure test |
| Customer 360 links correlate systems | UI integration test |
| Secrets/PII absent from snapshots/logs | Redaction and secret scan |
| Drift reappearing after repair raises finding | Reconciliation lifecycle test |

## 7. Provider mesh and portability acceptance

| Requirement | Evidence required |
|---|---|
| Postal 3.3.7 remains primary and passes adapter suite | Existing Postal regression plus new contract tests |
| Global Klyrow message ID preserved | Cross-attempt lifecycle test |
| Ambiguous submit never blindly fails over | Timeout-after-submit test |
| Fallback sender/domain verified | Negative routing test |
| Policy/consent/suspension apply across providers | Multi-adapter policy test |
| Provider credentials use secret references | Configuration and secret scan |
| Health routing deterministic/audited | Route-selection tests |
| Export contains no secrets | Package inspection test |
| Package signature verified | Tamper test |
| Validate/plan has no mutations | Database/provider assertions |
| Apply idempotent and rollbackable | Integration test |
| Provider failover remains disabled until canary | Configuration/release evidence |

## 8. Reseller and white-label acceptance

| Requirement | Evidence required |
|---|---|
| Platform, reseller and customer isolation | Full permission matrix and IDOR tests |
| Reseller cannot become platform owner | Identity/role negative tests |
| Tenant transfer effective-dated and reconciled | Workflow and concurrency tests |
| Price-book versions immutable | API/database tests |
| Wallet append-only and concurrent-safe | Ledger/locking tests |
| Credit/adjustment step-up and dual control | Security/workflow tests |
| Margin reproducible from price versions | Calculation and reconciliation fixtures |
| Odoo records created only through middleware | Contract/code-search evidence |
| Test mode creates no real invoice/payment | Odoo adapter assertions |
| White-label assets isolated | Cross-reseller browser/security test |
| Custom domain requires DNS/TLS validation | Activation negative/positive tests |
| Recipient trust identifies actual sender | End-to-end branded message/trust test |
| Wholesale pricing not leaked to customer | API/UI authorization tests |
| Reseller suspension behavior documented/tested | Entitlement and critical-message policy tests |

## 9. Cross-system event acceptance

Every event added by these branches must include:

- event ID;
- schema name/version;
- tenant/platform scope;
- actor/service identity;
- correlation and causation IDs;
- occurred and recorded timestamps;
- idempotency key or stable aggregate/version;
- purpose and data classification;
- minimal payload;
- no secret values;
- documented producer and consumer;
- retry and replay behavior;
- contract fixture.

Consumer rules:

- middleware validates service identity and schema;
- n8n acknowledges execution but is not authoritative;
- Odoo mapping uses stable external IDs;
- Klyrow result inbox validates signature, tenant, event, ordering and replay;
- duplicate events are safe;
- out-of-order financial or entitlement results do not corrupt state.

## 10. Owner admin acceptance

The platform-owner interface must add clean sections for:

```text
Decision Explorer
Policy Center
Approval Inbox
Message Passports
Simulation Lab
Attention Conflicts
Recipient Trust and Privacy
System Integrity
Repair Plans
Provider Mesh
Configuration Portability
Resellers
Wallets and Margin
Odoo Reconciliation
n8n Automation Evidence
```

Acceptance requires:

- global search by tenant, customer, user identity, domain, message, decision, passport, provider attempt, invoice, Odoo ID, n8n execution and event ID;
- permission and step-up controls;
- no secrets exposed;
- explicit stale/partial-data indicators;
- safe deep links;
- English and Spanish strings;
- responsive desktop/tablet layouts;
- keyboard and accessibility evidence.

## 11. Staging certification

Before any differentiated feature is considered release-scoped, staging must show:

1. migrations applied and rollback decision points documented;
2. existing Klyrow API/SMTP/campaign behavior remains compatible;
3. Keycloak login/signup unaffected;
4. Postal delivery path still works through safe test/canary controls;
5. middleware event delivery and replay protection pass;
6. n8n/Odoo outage does not block normal requests;
7. tenant and reseller isolation pass;
8. no real billing or provider failover occurred;
9. metrics and alerts load;
10. backup/restore includes the new tables and signing metadata;
11. feature flags can disable the new behavior without data loss;
12. exact artifact and SHA recorded.

## 12. Production hard gate

Production activation remains restricted to `release/klyrow-production-readiness`.

The final release packet must explicitly include go/no-go rows for:

- decision enforcement versus observe-only;
- message-passport signing keys;
- simulation resource limits;
- attention policy defaults;
- recipient trust domains and TLS;
- privacy/abuse Odoo workflows;
- reconciliation adapter credentials;
- automatic safe-repair classes;
- provider routing/failover;
- configuration apply permission;
- reseller real billing;
- white-label custom domains;
- rollback and stop criteria.

Missing external credentials, DNS/TLS readiness, Odoo/n8n workflow approval, provider validation, signing keys, independent review or owner authorization remain blockers. Codex must not fabricate or bypass them.
