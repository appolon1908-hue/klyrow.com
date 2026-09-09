# Klyrow issue-to-PR disposition — September 7, 2026

Implementation base: protected main
`b7874a4863ff8df8d90da23e820db40e3bb6bcea` (includes merged #97–#101).
This is a focused source correction, not closure of eight independent release
and feature missions. Follow-up work must preserve this and other merged source.

| Issue | Existing source / this patch | Remaining acceptance |
| --- | --- | --- |
| #82 durable operations | #97 encryption/result/worker fencing, #98 keyring backup/readiness, #99 tenant/recovery authority and #101 hold-aware result-payload retention are merged. | Full protected release evidence and real keyring rollout/restore/rewrap/retention-policy certification remain separate. |
| #85 Middleware email certification | #89's governed contract and #97–#99's encrypted results, tenant/service grants and recovery are merged. | Real staging mTLS/OAuth bindings, synthetic-recipient lifecycle/timeout/suppression/tenant evidence, rollback and bounded canary certification. Live delivery stays disabled. |
| #31 COD tenant resolver | #99 rejects wrong-tenant/malformed resolver responses. The upstream production-platform source correction is already recorded in the issue. | Exact runtime service subject/tenant/send-read grants and separately approved bounded sender/recipient test evidence. No email is sent by this PR. |
| #22 platform owner | Existing issuer/subject/MFA guards are retained; no email-to-role shortcut is introduced. | Real verified owner subject/mailbox, enrolled MFA, step-up and recovery rehearsal. No identity is guessed or promoted. |
| #83 browser security | #87's browser-flow, invitation, send-capability and step-up protections are already merged and are not replaced. | Complete final release/browser/staging evidence; this patch does not certify a running browser environment. |
| #84 runtime hardening | #88 PostgreSQL and #100 offline Mautic data migration/restore are merged. This patch adds a separate 7.2.0 image/runtime candidate using the upstream patched dependency constraints. | Exact candidate image CI/security/reproducibility, installed 7.1.3-to-7.2.0/plugin rehearsal, protected image publication, real data/database cutover, backup/restore and measured RTO/RPO. Production Compose is unchanged. |
| #81 Orbit shell | The SDK main manifest still reports `superseded-source-candidate` and `installAllowed: false` at this audit. No unapproved package is installed. | An install-allowed immutable package release with integrity/rollback authority, then full shell implementation and route/browser/accessibility acceptance. |
| #21 31-feature program | Source now includes #97–#101's operation/runtime foundations. This patch advances the remaining Mautic runtime candidate. | Remaining feature missions require their own implementation and acceptance; foundational fixes do not finish the whole program. |

All listed issues stay open until their own acceptance evidence exists. Link
this PR as related work, not with automatic-closing keywords. Repository merge
is not authorization to send, deploy, publish images, migrate data or change
production identity. Exact-head CI and independent approval remain required.
