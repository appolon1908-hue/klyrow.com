# Klyrow SMTP Sending-Domain Inventory

## Purpose

This repository records the expected runtime inventory of Klyrow domains that
are verified and sending-enabled. The inventory is operational evidence, not a
bootstrap migration, sender authorization list, or permission to change DNS,
Postal, Keycloak, or live-delivery controls.

The machine-readable evidence is:

```text
evidence/runtime/verified-sending-domains-20260827.json
```

## Expected runtime state

Exactly 14 domains are expected in `domain_claims` with state
`SENDING_ENABLED`:

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

Run from a reviewed Klyrow checkout with a least-privilege read-only database
URL:

```bash
KLYROW_DATABASE_URL='postgresql+psycopg://READ_ONLY_USER@HOST:5432/klyrow' \
  scripts/ops/verify-klyrow-sending-domains
```

The verifier performs one `SELECT` against `domain_claims`. It fails when an
expected domain is missing, has a state other than `SENDING_ENABLED`, or when
another unreviewed domain is sending-enabled.

## Authority and safety

- A verified domain still requires an active sender identity, tenant
  authorization, stream policy, consent/suppression enforcement, quota, and
  every applicable delivery gate.
- Postal and Mautic remain internal engines behind the Klyrow control plane.
- Cross-system events and mutations go through Codestra Middleware.
- Runtime read-back is required. A Git evidence file alone does not prove that
  DNS, DKIM, return path, tracking, sender identities, suppressions, or provider
  state remain healthy.
- `KLYROW_SAFE_MODE`, production approval, canary controls, and external
  delivery gates remain independent and fail-closed.
