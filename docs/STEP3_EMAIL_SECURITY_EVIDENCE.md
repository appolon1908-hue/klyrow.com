# Step 3 Email Security Evidence

Date: 2026-08-29

## Implemented Controls

- Canonical provider endpoints require `ctx["service"]`.
- Product/browser callers cannot access the canonical provider shim directly.
- Existing Klyrow sender, domain, suppression, policy, and sandbox checks still run.
- Canonical sends force `sandbox=True`.
- Postal credentials and DKIM private keys are not returned by canonical read endpoints.
- Tenant-scoped database lookups are used for messages, events, domains, reputation, and health.

## Production Security Gates Still Required

- Live Middleware service token validation through Kong.
- External secret-store verification for provider credentials and DKIM private keys.
- Linux CI backup and permission certification.
- Live negative auth tests for non-service callers and wrong tenant/caller.
