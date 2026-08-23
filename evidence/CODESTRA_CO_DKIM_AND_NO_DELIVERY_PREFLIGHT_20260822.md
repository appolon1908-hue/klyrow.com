# codestra.co DKIM and no-delivery preflight certification

Date: 2026-08-22

## DNS reconciliation

- GoDaddy authenticated control: available on Server A.
- Approved allowlist domain: `codestra.co`.
- Matching GoDaddy record: present, TXT `postal-H8XQUC._domainkey`, TTL 3600.
- The record value exactly matches the approved 243-byte Postal public-key value.
- Both authoritative nameservers publish the same value.
- Public recursive DNS publishes the same value.
- Before/after diff: empty; no DNS mutation was necessary.
- Postal reports `spf_status=OK`, `dkim_status=OK`, `mx_status=OK`, and `return_path_status=OK` for `codestra.co`.

## Server A machine identity reconciliation

- Client: `cod-web-out-email-production`.
- Issuer: `https://auth.codestra.co/realms/codestra`.
- Keycloak service account: enabled.
- Root-owned credential source: `/etc/codestra/secrets/cod-web-out-email/klyrow-oidc-client-secret`, mode 0600.
- The secret matched Keycloak, but its file contained a trailing newline. Normalizing the existing credential from 87 bytes to its canonical 86-byte value fixed form-encoded client authentication. No credential was rotated.
- Fresh client-credentials token: HTTP 200.
- Audiences: `codestra-api`, `codestra-kong-certification`.
- Scopes include `klyrow.read`, `klyrow.send`, `email.send`, `email.status`, and `campaign.cod-web-out`.
- Server-owned tenant claim: `COD`.

## Authenticated no-delivery preflight

Path: Server A mTLS client -> Klyrow private interface -> canonical OIDC verification -> Server A tenant resolver -> sender policy.

- mTLS: PASS.
- Fresh token authentication: PASS.
- Authoritative tenant resolution: PASS; Klyrow resolved the service identity to its internal tenant UUID.
- Authorized sender `sales@codestra.co`: PASS.
- Sandbox-only recipient `capture@klyrow-sink.test`: PASS.
- Response: HTTP 200, `allowed=true`, `dry_run=true`, `postal_submitted=false`.
- Provider message count before/after: 1 / 1.
- Provider message delta: 0.
- Forged sender `forged@moneybeeloan.com`: HTTP 403 `sender_address_not_allowed`.
- Forged-sender provider message delta: 0.

## Safety

- Email submitted: 0.
- Email delivered: 0.
- DNS mutations: 0.
- Live delivery remains disabled.
- SMS/Jasmin/SMPP/Telnexa billing were not modified.

## Result

`CODESTRA_CO_DKIM=PASS`

`SERVER_A_KLYROW_NO_DELIVERY_PREFLIGHT=PASS`

`SENDER_RESTRICTION=PASS`

`FINAL_STATUS=SERVER_A_KLYROW_EMAIL_SERVICE_IDENTITY_CERTIFIED`
