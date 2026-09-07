# Klyrow issue-to-PR disposition — September 7, 2026

Implementation base: protected main
`6da623eea278ee7ccb9d7c4d2eaa96c5194cf594` (includes merged #97 and #98).
This is a focused source correction, not closure of eight independent release
and feature missions. Follow-up work must preserve this and other merged source.

| Issue | Existing source / this patch | Remaining acceptance |
| --- | --- | --- |
| #82 durable operations | #97 encryption/result/worker fencing and #98 keyring backup/readiness are merged. This patch closes the legacy recovery bypass and enforces explicit command/result service grants. | Full protected release evidence, real keyring rollout/restore/rewrap and legal-hold-aware physical retention remain separate. |
| #85 Middleware email certification | Existing governed contract and encrypted results are preserved; this patch strengthens service and tenant authority. | Real staging mTLS/OAuth bindings, synthetic-recipient lifecycle/timeout/suppression/tenant evidence, rollback and bounded canary certification. Live delivery stays disabled. |
| #31 COD tenant resolver | This patch rejects wrong-tenant/malformed resolver responses; it does not grant any new runtime authority. | Exact runtime service subject/tenant/send-read grants and separately approved bounded sender/recipient test evidence. No email is sent by this PR. |
| #22 platform owner | Existing issuer/subject/MFA guards are retained; no email-to-role shortcut is introduced. | Real verified owner subject/mailbox, enrolled MFA, step-up and recovery rehearsal. No identity is guessed or promoted. |
| #83 browser security | #87's browser-flow, invitation, send-capability and step-up protections are already merged and are not replaced. | Complete final release/browser/staging evidence; this patch does not certify a running browser environment. |
| #84 runtime hardening | #88 PostgreSQL and #91 secret-bootstrap fixes are merged. No stale image/Compose history is replayed. | Mautic dependency/image reconciliation and isolated volume migration/restore remain unfinished. |
| #81 Orbit shell | No unapproved Orbit candidate is installed. | Verify an install-allowed immutable package release with integrity/rollback authority, then implement and test the full shell/route inventory. |
| #21 31-feature program | This patch advances integration correctness and security in the existing implementation. | Remaining feature missions require their own implementation and acceptance; foundational fixes do not finish the whole program. |

All listed issues stay open until their own acceptance evidence exists. Link
this PR as related work, not with automatic-closing keywords. Repository merge
is not authorization to send, deploy, publish images, migrate data or change
production identity. Exact-head CI and independent approval remain required.
