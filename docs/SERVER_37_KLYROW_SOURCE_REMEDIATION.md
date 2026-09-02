# Server 37 Klyrow source remediation

Date: 2026-09-02
Server: `37.27.128.39`
Repository: `https://github.com/appolon1908-hue/klyrow.com`

## Authority decision

The live gateway `/app/app` tree was hashed file by file and compared with the
reviewed repository. All 25 live Python files exactly match the historical
runtime-authority snapshot at `cab2e2b`, but that snapshot does not pass the
current repository test collection and predates security and delivery-safety
changes on the production remediation branch. It is evidence of the live
state, not a releasable source revision.

This remediation therefore starts from the green full-platform production
branch (`ccf463e`) and incorporates only the required live functionality with
its migrations and tests. It does not overwrite reviewed current code with an
older runtime snapshot.

## File classification

| Live difference | Classification | Remediation |
|---|---|---|
| `webmail.py`, `webmail_models.py` | Legitimate production feature, previously uncommitted | Added to Git with exact recovered content, routes, migrations and tests |
| `platform.py` webmail router | Legitimate production integration | Added to the current composition root only |
| `main.py` webmail status/startup hooks | Legitimate production integration mixed with obsolete drift | Ported only webmail projection hooks; retained current runtime-secret, metric and operation safeguards |
| `agent_mailboxes.py` webmail channel marker | Legitimate scoped production fix | Ported with an explicit browser/channel guard |
| `postal_provisioning.py` live-domain credentials | Legitimate production fix mixed with an obsolete worker | Ported encrypted exact-domain credentials and reconciliation into the current hardened worker |
| `provider.py` webmail inbound capture | Legitimate production integration mixed with security regressions | Ported capture only after current SPF/DKIM/DMARC and spam disposition |
| live direct Postal inbound route | Unexpected security drift | Not ported: it bypassed the current authenticated-results contract |
| `auth_bff.py` | Older unexpected drift | Not ported; current reviewed Keycloak action behavior retained |
| `messaging.py`, `preferences.py`, `service_worker.py`, `smtp_relay.py` | Older source deployment / unexpected drift | Not ported; reviewed current implementations retained |

Generated Python bytecode, caches and runtime configuration are excluded from
source authority and from all images.

## Recovered database authority

The production migration ledger includes
`2026082704_webmail_suite.sql` and
`2026082801_postal_domain_credentials.sql`. Their exact earlier workspace
copies were recovered and committed. The remediation copies have identical
SHA-256 checksums to the recovered files. No credential values are present in
either migration.

## Image authority

Gateway, worker, web, migration and Postal-provisioner images are built only
from the reviewed commit. Their Dockerfiles require a 40-character source SHA,
pin every base image by digest, and set these OCI labels:

- `org.opencontainers.image.source`
- `org.opencontainers.image.revision`
- `org.opencontainers.image.version`

Promotion must use the resulting immutable registry digest. The existing
`webmail-20260828` and `smtp-hotfix-20260826.9` tags are rollback inputs only;
they are not source authority.
