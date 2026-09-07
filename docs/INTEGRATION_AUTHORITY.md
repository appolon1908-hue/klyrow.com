# Integration authority and recovery boundaries

Related issues: #82, #31, #85; program tracker #21.

## Tenant resolver response contract

A successful resolver response must be an object with boolean `authorized: true`,
the exact requested `permission`, and nonblank string `identity_id` and
`tenant_id` fields. When a tenant header selected a tenant, the returned tenant
must match it exactly. A different tenant or a denied grant returns 403
`not_found` before the tenant database lookup; malformed authority returns 503
`authorization_unavailable`. The existing header-conflict, suspended-tenant,
transport-failure, audience and credential checks are preserved.

These checks do not repair a missing runtime service registration. An operator
must still register and verify the real COD service subject, tenant and exact
send/read grants through the approved resolver authority. No wildcard or
platform-admin grant is needed for email send/status.

## Commands and integration results

`/v1/commands` requires `klyrow.middleware.command.write`.
`/v1/integrations/results` requires `klyrow.integration.result.write`.
Both require authenticated `service: true`, a registered identity type of
`SERVICE` or `SERVICE_ACCOUNT`, and the exact explicit permission. A subject
named `middleware-service`, a human administrator role, a wildcard, or a
send-only grant cannot substitute for these requirements. Invalid permission
collections fail closed instead of causing a server error. Space-delimited
scope strings and sequences of strings retain exact-token semantics.

Resolver identity type remains resolver-authoritative. The direct signed OIDC
path derives service type from the enabled registered identity, not a token's
self-declared identity type; signature, issuer, audience and active tenant
membership checks still run. The existing configured Middleware key is still
validated in constant time and now creates an explicitly typed service context
with the two capabilities it previously accessed through a subject-name shortcut.
This does not generate, rotate, publish or provision any credential. Production
continues to require its approved authentication transport and runtime policy.

## Recovery of ambiguous Mautic work

Both `/v1/operations/{id}/reconcile` and the older
`/v1/admin/operations/integrations/{id}/recover` call one recovery guard while
holding the outbox row lock used by worker completion. Mautic dead letters and
operations with a same-tenant, same-outbox `MAUTIC_LATE` observation return 409
`operation_requires_provider_readback` without changing state, committing a
recovery audit, or writing a new idempotency response. This keeps the older
operator API from bypassing the canonical reconciliation policy.

Unambiguous Mautic retries and existing N8N/Odoo recovery remain supported.
Observations belonging to another tenant or operation cannot block a legitimate
retry. This guard is not a provider cancellation protocol, and it cannot undo
an external effect already in flight. Provider readback and independently
approved reconciliation remain necessary for ambiguous work.

## Evidence and rollout

`test_integration_authority.py` exercises resolver response binding, typed
service permissions, malformed grants, authenticated legacy-key compatibility,
and actual signed OIDC tokens with registered service/human identities.
`test_durable_operation_results.py` exercises both recovery surfaces, state and
idempotency preservation, foreign-tenant isolation, and competing PostgreSQL
transactions. PostgreSQL tests run in the existing required contract CI phase.

Before this patch, the new baseline regression selection had 42 failures and
17 passes on protected source `6da623eea278ee7ccb9d7c4d2eaa96c5194cf594`.
The corrected broader local selection passed 154 tests with three
PostgreSQL-only skips. The local environment has older FastAPI and cannot
collect the full platform suite; pinned hosted CI, independent final-head
review, image/security gates and release validation remain required. Local
success is not production certification.

No deployment, live email, provider activation, Keycloak mutation, tenant
registry write, database migration, volume change or key rotation is performed
by this source change. No delivery flag or branch protection is weakened.
