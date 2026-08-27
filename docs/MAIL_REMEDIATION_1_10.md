# Production mail remediation 1–10

This release turns the ten audited gaps into explicit API checks and fail-closed activation controls. `GET /v1/admin/mail/readiness` is the canonical operator view; the same checks appear on the `/admin` page, while a tenant-scoped view appears under **Mail readiness** on `/`.

| # | Gap | Repository remediation | Remaining launch authority |
|---:|---|---|---|
| 1 | Inbound/shared inbox routes inactive | Canonical 16-address manifest, idempotent provisioning, attested route activation, provider inbox list/detail | Destination owners must attest Odoo/helpdesk/security references |
| 2 | Postal events retrying through HTTP 503 | Signed events are persisted and acknowledged 202; middleware delivery retries from the durable local queue | Drain existing DLQ after deploying and validating middleware mTLS |
| 3 | Machine credential 403 and direct-Postal bypass | Scoped API keys and service-account secrets now authenticate on product routes with server-derived scopes | Rotate callers from direct Postal keys to Klyrow credentials |
| 4 | Structured payload versus `raw_b64` mismatch | Live worker accepts governed SMTP MIME and structured API payloads and submits the matching Postal fields | Enable the provider live gate after canary evidence |
| 5 | PTR mismatch | Runtime PTR comparison and provider-domain activation block sending on mismatch | Change reverse DNS at the infrastructure provider; the repository cannot mutate it |
| 6 | Campaign gates disabled | Provider and campaign domains have separate, audited, phrase-attested activation endpoints | Admin must satisfy DNS, PTR, transport, inbound, and campaign attestations |
| 7 | Tracking and placement incomplete | Postal open/click flags are emitted, analytics aggregate lifecycle events, and Gmail seed OAuth placement checks are available | Install tenant-approved Gmail OAuth secrets and validate tracking DNS |
| 8 | Corporate roles only staged | Versioned manifest, provisioning API/tool, destination verification, and tenant status matrix | Team destinations must be staffed before activation |
| 9 | Agent mailboxes inactive | Readiness verifies mailbox, inbound route, and outbound authorization as one unit; campaign/domain gates precede validation | Identity, Odoo/VICIdial, and provider-route adapters must attest each mailbox |
| 10 | Source/deployment drift | Clean-tree deployment, commit-tagged images, release SHA in health/readiness, schema gate, and image rollback | Deploy this committed release instead of copying hotfix files into the live checkout |

## Safe rollout order

1. Merge and deploy the committed release with all live-delivery gates false.
2. Apply `2026082701_mail_operations_remediation.sql` and confirm the required schema version.
3. Install the Postal transport registry and each server-specific root-owned credential.
4. Correct PTR and run `scripts/mail-readiness` plus `GET /v1/admin/mail/readiness`.
5. Provision role addresses without `activate`, verify every destination, then activate routes.
6. Create scoped Klyrow machine credentials and remove direct Postal credentials from callers.
7. Drain/replay event DLQ through Klyrow after middleware mTLS passes.
8. Activate one provider domain, one controlled tenant policy, and one canary only.
9. Validate delivery, reply ingestion, open/click lifecycle, and Gmail folder placement.
10. Activate campaign domains and human mailboxes only after their independent checks pass.

No endpoint in this release silently opens production sending. External infrastructure and human-destination prerequisites remain visible as `BLOCKED` instead of being inferred or bypassed.
