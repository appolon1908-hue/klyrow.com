# Open issue reconciliation — September 6, 2026

Reviewed against protected main
`d205073596a76e41d656d97c3622a7081e032324`. This is a source audit, not runtime
certification. Recheck current heads, CI attempts, and independent approvals
before merging any follow-up. No issue is closed merely because a related PR
merged.

## Current implementation and remaining work

| Issue | Verified source progress | Remaining acceptance |
| --- | --- | --- |
| [#85](https://github.com/appolon1908-hue/klyrow.com/issues/85) Middleware email | [#89](https://github.com/appolon1908-hue/klyrow.com/pull/89) merged as `d205073596a76e41d656d97c3622a7081e032324`: governed email commands, callback/event reliability, tenant/caller replay binding, adapter contracts, and strict Odoo acknowledgement validation. | Approved staging mTLS/OAuth identity and recipient fixtures; callback, suppression, timeout, backup/restore, rollback and bounded canary evidence at the accepted artifact. Unsupported batch/template/scheduled commands remain rejected. |
| [#84](https://github.com/appolon1908-hue/klyrow.com/issues/84) runtime images | [#88](https://github.com/appolon1908-hue/klyrow.com/pull/88) merged as `befe3e2a4be365a54ddac63d0787d04fbf0634d6`; PostgreSQL runtime and security validation are present. | Mautic image dependency remediation and safe migration away from the whole application volume. Historical Composer aliases/manual lock edits cannot be assumed compatible or secure. Real isolated-volume backup/restore and migration-twice evidence remains required. |
| [#83](https://github.com/appolon1908-hue/klyrow.com/issues/83) browser security | [#87](https://github.com/appolon1908-hue/klyrow.com/pull/87) merged as `b19159db729e4b622f5a6de9418bf112e2a528f0`: per-transaction browser cookies, invitation role preservation, send permission, step-up identity and absolute deadline guards. | Complete release evidence, including repaired deploy-readiness. The host-prefixed cookie correctly uses `Path=/`; the historical issue's `/auth` path is incompatible with the `__Host-` prefix. No production owner identity or MFA evidence is inferred from source tests. |
| [#82](https://github.com/appolon1908-hue/klyrow.com/issues/82) durable operations | [#90](https://github.com/appolon1908-hue/klyrow.com/pull/90) rejects unexecutable schedules; [#91](https://github.com/appolon1908-hue/klyrow.com/pull/91) bootstraps OAuth files atomically; [#92](https://github.com/appolon1908-hue/klyrow.com/pull/92) applies mutation capabilities and matching resolver requests. All are reviewable follow-ups, not protected source yet. | Dedicated versioned replay-result encryption and rotation; full operation race acceptance; persisted-result schema/redaction/size/unavailability/retention contract; final integration and release evidence. Current plaintext `Idempotency.response_json` is not a dedicated encrypted result store. |
| [#81](https://github.com/appolon1908-hue/klyrow.com/issues/81) Orbit adoption | Located shared packages on SDK protected source `1c776b55857072f43f62281a1877c87c0dfeada8`. | The [release manifest](https://github.com/appolon1908-hue/SDK-repository/blob/1c776b55857072f43f62281a1877c87c0dfeada8/orbit/release/orbit-v2.0.0.json) says `superseded-source-candidate` and `installAllowed: false`. No published GitHub release was available during this audit. Full-shell adoption requires protected, immutable package artifacts, integrity and rollback authority first. |
| [#49](https://github.com/appolon1908-hue/klyrow.com/issues/49) K0 preservation | The selective audit below identifies current recovery and inbound replacements. [#93](https://github.com/appolon1908-hue/klyrow.com/pull/93) restores literal subscription actions and prevents billing event starvation after the first 200 events. | Complete behavior-by-behavior disposition of the large historical production-remediation aggregate; missing historical files are not proof that their behavior was superseded. |
| [#31](https://github.com/appolon1908-hue/klyrow.com/issues/31) COD resolver | The existing issue records the source registry correction in production-platform PR #254, merge `86cbca784e5785833c0d72e282da0abd9443c8ac`. | Apply/reconcile the approved registry in the actual environment and verify the immutable client subject, narrow tenant grants, sender, and bounded delivery evidence. No runtime success is claimed. |
| [#22](https://github.com/appolon1908-hue/klyrow.com/issues/22) platform owner | Owner guards and browser step-up corrections are merged. | Approved immutable Keycloak subject and verified mailbox, enrolled MFA/fresh authentication, recovery rehearsal, privileged-operation inventory, and runtime evidence. Email text alone cannot establish owner authority. |
| [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) 31-branch program | Auth/tenancy/browser foundations are merged; the repository contains broader API foundations. | Remaining feature missions must follow the execution index and independent review gates. Existing profile/event/segment/journey CRUD does not satisfy all mission acceptance criteria. This tracker is not complete. |

## Shared readiness defect

Current-main [run 34050892586](https://github.com/appolon1908-hue/klyrow.com/actions/runs/34050892586/job/101534218305)
attempted to upload `evidence/runtime` as a GitHub release file and failed
because it is a directory. The authoritative fix is
[Infustruction-repo #102](https://github.com/appolon1908-hue/Infustruction-repo/pull/102).
It uploads regular top-level files and retains runtime evidence for artifact
collection. Both create and upload regression paths pass. Klyrow must update
its shared workflow pin only after the fix reaches protected upstream source.

## K0 preservation evidence

| Historical tip | Current disposition and evidence |
| --- | --- |
| `d5777a8afaa6954d35462e08d4d4153f0164b308` | Current `main.py` retains first-attempt-only canary claims and retry recovery. `test_postal_outage_retries_without_loss_or_second_canary_claim` exercises outage, recovery, and one reservation. The broader branch's certification-ledger/policy inventory still needs reconciliation. |
| `198ab2957a061c3c745d775e0010bd429295adfd` | Historical native inbound MIME is superseded by the current Postal Hash contract: signature, timestamp, exact route, tenant, attachment hash/size, and duplicate checks in `provider.postal_inbound`. `test_postal_hash_inbound_requires_signature_timestamp_exact_route_and_replay_dedupe` covers the current path. |
| `c0035709dc6ca1efb3c7cc29c76894c604890318` | Current inbound checks tenant enablement and both exact route registries. Sender-controlled MIME spam headers are not trusted scanner authority; the native Hash path quarantines mail without authenticated SPF/DKIM/DMARC results. Fixture spam-policy tests remain separate from live scanner evidence. |
| `ad432f9bf598a629be2ca23c3663f7feb4064c81` | Current Hash ingress enforces the smaller tenant/route size limit and quarantine policy. Two billing gaps were reproduced: shadowed literal subscription actions and event starvation after 200 represented events. [#93](https://github.com/appolon1908-hue/klyrow.com/pull/93) selectively fixes both, with real HTTP and 205-event regressions. Existing tenant reads, idempotence and lease recovery tests pass. |
| `59e58d39f0a67c39219c76579d94e6e00766e736` | The historical ten-gap document was read. Current source has related delivery, callback, mailbox, credential and readiness modules, but the old `mail_operations.py`, `mail_roles.py`, `postal_transport.py`, `gmail_seed.py`, role-address provisioning script and aggregate regression module are absent. Each associated behavior still needs a selective disposition before #49 can close. |

## Validation and next integration gate

The scheduling follow-up has 9 focused tests and 582 local suite passes. The
capability follow-up has 114 focused tests and 687 local suite passes. The
credential follow-up has 15 focused migration/transport tests and 582 local
suite passes. The billing follow-up has 4 focused tests and 575 local suite
passes. Each full local run also has one PostgreSQL-only skip and the
same two environment failures: unavailable GPG agent and external webhook DNS.
These limitations are not silently excluded from the result. Exact-head CI
performs the required hosted checks.

Review follow-ups cover resolver grant selection and atomic credential
publication, including disk failure, concurrent installation and old empty
file recovery. Fresh independent approval after each final push remains a
merge requirement. PRs #90 and #92 both touch scheduling/authentication and
must retain both changes during integration. Delivery, provider, identity,
volume, and deployment activation remain governed by their separate gates.
