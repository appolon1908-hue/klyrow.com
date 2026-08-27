# Klyrow SMTP Sending-Domain Inventory

## Purpose

This repository records the expected runtime inventory of Klyrow domains that are both verified and sending-enabled. The inventory is an operational contract, not a bootstrap migration and not permission to change DNS, Postal, Keycloak, or live-delivery controls.

The machine-readable source is:

```text
config/runtime/klyrow-sending-domains.json
```

## Expected runtime state

Exactly 14 domains are expected in `domain_claims` with state `SENDING_ENABLED`:

1. `beyvra.com`
2. `breero.com`
3. `breero.shop`
4. `codestra.agency`
5. `codestra.cloud`
6. `codestra.co`
7. `codestra.digital`
8. `codestra.media`
9. `klyrow.com`
10. `kyqra.com`
11. `moneybee.loan`
12. `moneybeeloan.com`
13. `nativoenglish.com`
14. `telnexa.co`

## Read-only verification

Run from a reviewed Klyrow checkout with a read-only database URL:

```bash
KLYROW_DATABASE_URL='postgresql+psycopg://READ_ONLY_USER@HOST:5432/klyrow' \
  scripts/ops/verify-klyrow-sending-domains
```

The verifier performs one `SELECT` against `domain_claims`. It fails when an expected domain is missing, has a state other than `SENDING_ENABLED`, or when another unreviewed domain is sending-enabled.

## Authority and safety

- Klyrow owns domain onboarding, sender authorization, Postal/Mautic integration, suppression, consent, usage, and delivery lifecycle.
- Postal and Mautic remain internal provider engines.
- Cross-system events and mutations go through the Codestra Middleware boundary; this inventory does not authorize direct Odoo or n8n writes.
- Runtime read-back is required. A Git manifest alone is not evidence that DNS, DKIM, return path, tracking, sender identities, suppression policy, or provider state are healthy.
- `KLYROW_SAFE_MODE`, production approval, canary, and external-delivery gates remain independent and fail-closed.
