# Klyrow Admin, Odoo and n8n Acceptance Matrix

This matrix is mandatory evidence for the relevant feature PRs and final release.

| Capability | Keycloak | Klyrow | Middleware | n8n | Odoo | Required evidence |
|---|---|---|---|---|---|---|
| Email/password signup | Authoritative identity | Local identity/workspace bootstrap | Receives normalized event | Onboarding automation | Company/contact/lead mirror | Browser E2E, duplicate callback, outage test |
| Google signup | Identity broker | Safe identity linking and onboarding | Receives normalized event | Onboarding automation | Company/contact mirror | Google redirect/linking contract tests |
| Email verification | Authoritative flag | Mirrored identity state | Event transport | Follow-up workflow | Contact status mirror | Verification reconciliation test |
| Workspace/membership | Identity claims only where required | Authoritative | Event/command transport | Invitation/follow-up automation | Company/contact/team mirror | Cross-tenant and role tests |
| Postal provisioning | No provider data | Authoritative mapping/state | Event transport | Failure/ready automation | Operational reference/activity | Crash/retry/idempotency tests |
| Plans/subscriptions | No billing payload | Authoritative entitlement | Event/command transport | Sales/renewal automation | Commercial/accounting mirror | Plan/version/entitlement tests |
| Usage | No usage payload | Authoritative append-only ledger | Period-close transport | Threshold automation | Usage statement | Deduplication and reconciliation |
| Invoice | No invoice payload | Invoice request/mirror | Idempotent transport | Collections workflow | Accounting document authority when configured | Invoice idempotency and drift test |
| Payment/credit | No payment payload | Validated mirror/entitlement decision | Signed event/command transport | Collections automation | Accounting record | Replay, out-of-order and authorization tests |
| Support | Authentication only | Customer-visible ticket/reference | Transport | Routing/notification | Helpdesk/task authority when configured | Status reconciliation tests |
| Platform owner | Exact issuer/subject, MFA | `PLATFORM_OWNER` authorization | Privileged command identity | No self-promotion | Back-office access separately controlled | Promotion, step-up and audit tests |
| Production activation | Identity/step-up | Capability and safety gate | Connectivity/preflight | Workflows reviewed and enabled intentionally | Reconciled and healthy | Owner go/no-go and rollback packet |

## Universal assertions

- Keycloak contains no invoices, payment history, message-level usage or payment-card data.
- n8n contains no exported credentials and has no direct database access.
- Odoo synchronization uses middleware APIs, never direct database writes.
- Customer flows do not synchronously depend on n8n or Odoo.
- Klyrow authorization, entitlement, consent, suppression and sending gates cannot be bypassed by an Odoo or n8n action.
- Every event/command is tenant-scoped, authenticated, idempotent, versioned and auditable.
- Platform ownership is bound to exact Keycloak issuer and subject, not an email comparison.
- All privileged actions show reason, actor, timestamp, correlation and result in the audit log.
