# Odoo acknowledgment reliability follow-up

Related: #85 and PR #89. This extends, rather than replaces, the governed
integration at `082946414e8bfcc0874ff51459cf3290f92961a6`.

## Contract

Both Odoo authentication and inbound-ingestion replies must be JSON-RPC 2.0
objects echoing the exact request ID, with exactly one of `result` or `error`.
An unrelated, conflicting or malformed 2xx acknowledgment cannot mark an event
delivered. Positive integer IDs are required; booleans are not IDs.

HTTPX request failures, including protocol and content-decoding failures, enter
the existing bounded retry/dead-letter path. This preserves the idempotency key
for Odoo reconciliation and never performs an immediate resubmission. Remote
response bodies are not stored in the safe error field. Lease-token predicates,
retry limits and lease release remain unchanged.

## Reproduction

Run from the repository root:

```sh
python -m pytest -q tests/test_klyrow_odoo_transport.py
```

The 33 tests use the real transport/worker, HTTPX MockTransport and a recording
mock database session. Only deployment settings are substituted. On the exact
source above: 15 failed, 18 passed. With this patch: 33 passed. Coverage includes
both RPC phases, wrong/missing IDs, wrong protocol version, conflicting response
members, boolean IDs, valid acknowledgments, sanitized access rejection and
three-attempt dead-letter/lease-release behavior. Existing imported regression
fixtures now use valid correlated RPC envelopes so ingestion-negative tests do
not fail prematurely during authentication.

These are isolated regression results, not PostgreSQL, staging, full-suite,
image-scan or production certification. Required exact-head CI and independent
review must pass before merge. Production TLS, OIDC/resolver grants and approved
canary evidence remain open under #85.

## Rollback and boundaries

No schema, dependency, secret, deployment or delivery flag changes are required.
Rollback through a reviewed source revert and the established immutable-image
release process; do not edit a running container. Neither this patch nor a merge
authorizes provider activation, Odoo writes, email delivery or production changes.
