# Step 3 Email Production Gates

Date: 2026-08-29

Step 3 is implementation-ready but not production-activated.

## Must Pass Before Production Sending

- Linux CI full suite.
- GPG backup/restore certification.
- POSIX DKIM private-key permission certification.
- Migration hash contract repair or approved hash update.
- Authenticated staging canary from Middleware to Klyrow in safe mode.
- SMTP/DNS/domain evidence for SPF, DKIM, DMARC, PTR/rDNS, TLS, and bounce/complaint paths.
- Provider timeout and reconciliation evidence.
- Explicit approval before disabling safe mode or enabling production delivery.

## Prohibited In This Branch

- No production Postal delivery.
- No production DNS activation.
- No live Mautic campaign sending.
- No direct product bypass around Middleware.
