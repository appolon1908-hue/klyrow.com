# Klyrow issue reconciliation — September 9, 2026

Source baseline: protected main `367f707` (includes merged #102 and #104).
PR #103 remains the customer-event ingestion slice of #21. Its review repairs
cover old-writer migration compatibility, concurrent key collisions, canonical
header support and complete timestamp-aware request binding. It also consumes
#104's Postal image correction from main.

## Observed runtime evidence

Read-only container and loopback HTTP inspection found a connected Klyrow host.
The gateway and web image revision is
`da9d85891a4e313748e309aed86662d6c03d26bb`, not the current source baseline.
`/healthz` reports `ok`; `/readyz` reports `ready` and `safe_mode: false`.
Mautic reports the older 7.1.3 image, revision
`42628161ffcc5720a46179a54e0992b25804a79a`.

The inspected gateway environment has `KLYROW_SAFE_MODE=false`,
`LIVE_EMAIL_DELIVERY=true`, `EXTERNAL_EMAIL_DELIVERY=true` and
`PRODUCTION_PROVIDER_ROUTING=true`. The platform-owner issuer, subject and email
variables and `KLYROW_DURABLE_RESULT_KEYRING_FILE` are unset. These are environment
observations, not proof that all alternative configuration sources are absent.
No values of credentials, message contents or personal identity were read.
No runtime configuration, identity, database or delivery setting was changed.

The earlier zero-connected-host and disabled-delivery assumptions must not be
used as current runtime evidence. A source merge alone does not update this
running revision or certify its behavior.

## Issue disposition

| Issue | Remaining work |
| --- | --- |
| #21 | #103 advances customer events; the broader 31-mission feature program remains incomplete. |
| #22 | Verify canonical owner identity, immutable Keycloak subject, MFA, step-up and recovery. The running gateway lacks the inspected owner environment bindings. |
| #31 | Read back the exact COD subject/tenant/narrow resolver grants and complete the bounded sender/recipient acceptance with approved runtime authority. No email was sent in this audit. |
| #81 | SDK main `a194b5154a5b313c8fc4b9150abd17a4cc6612ae` still exposes an Orbit manifest with `status: superseded-source-candidate` and `installAllowed: false`; no GitHub release was returned. Immutable package authority remains a prerequisite to full-shell adoption. |
| #82 | Source keyring/retention/operation repairs are merged. Real rollout, keyring backup/restore/rewrap, retention/hold and recovery certification remain. |
| #83 | Source browser repairs are merged; running Keycloak/browser and protected release evidence remain. |
| #84 | #102's Mautic 7.2 candidate is merged; runtime remains 7.1.3. Installed-version/plugin upgrade rehearsal, actual backup/restore, measured RTO/RPO and approved cutover/rollback remain. |
| #85 | Exact staging mTLS/OAuth bindings, lifecycle/idempotency/timeout/suppression/tenant evidence, backup/rollback and bounded canary certification remain. Live runtime settings must be reconciled with the release plan. |

None of the eight issues meets all of its closure criteria from this source
repair and read-only inventory. Main requires current-head frontend, test,
secrets and image checks, resolved review threads, one approval, and approval
from someone other than the last pusher. Stale approvals are dismissed on push.
