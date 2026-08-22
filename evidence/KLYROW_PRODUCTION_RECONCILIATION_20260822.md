# Klyrow production reconciliation

Date: 2026-08-22

## Current runtime

- `api.klyrow.com` resolves to `37.27.128.39`; `/healthz` and `/readyz` return HTTP 200.
- Canonical Keycloak discovery at `auth.codestra.co` returns HTTP 200.
- `mail.klyrow.com` resolves to `37.27.128.39`.
- `37.27.128.39` PTR is `mail.klyrow.com`; forward-confirmed reverse DNS passes.
- Private SMTP submission from Server A negotiates TLS 1.3 with a publicly trusted certificate for `mail.klyrow.com`; certificate verification returns 0.
- Gateway and SMTP relay use immutable image `codestra/klyrow-gateway:bc603189d7fe-exact` and are healthy.
- Postal web, worker, and SMTP containers are healthy.
- Active provider queue rows: 0.
- Active provider usage-event rows: 0.
- Active provider delivery-event rows: 0.
- Live delivery remains gated and no customer email was sent.

## Shared-host regression

- Telnexa billing API remains on `telnexa/billing:sha-4dbd67190ccc0fb2be52ec700882178e29c6ff27` and is healthy.
- Telnexa billing worker remains on the same image.
- Jasmin remains on `telnexa/jasmin-hardened:sha-4b4e5c73463d` and is healthy.
- Telnexa RabbitMQ remains on `telnexa/rabbitmq-hardened:sha-4b4e5c73463d` and is healthy.
- SMS/Jasmin/SMPP/Telnexa billing configuration was not changed.

## Remaining external production gates

1. `klyrow.co` has no public A/AAAA record. The required customer application URL is unavailable. This domain is not in the previously authorized 14-domain GoDaddy allowlist, so no DNS mutation was attempted.
2. Public TCP/587 to `mail.klyrow.com` is not reachable. Private Server A submission is healthy, but standard Internet mail-client access is not yet exposed/certified.
3. Protected PR #11 still requires an independent review. Production must not be replaced with the unreviewed branch revision.
4. Live external transactional/campaign/inbound E2E remains gated. The no-delivery identity preflight and internal-sink tests pass, but they do not prove Internet acceptance.

## Truthful status

- `KEYCLOAK_HEALTH=PASS`
- `KLYROW_HEALTH=PASS`
- `POSTAL_HEALTH=PASS`
- `QUEUE_HEALTH=PASS`
- `PTR_FC_RDNS=PASS`
- `PRIVATE_SMTP_TLS=PASS`
- `PUBLIC_SMTP_SUBMISSION=BLOCKED_NOT_EXPOSED`
- `CUSTOMER_PORTAL_DNS=BLOCKED_MISSING_KLYROW_CO_DNS`
- `TELNEXA_SMS_UNCHANGED=PASS`
- `TELNEXA_BILLING_UNCHANGED=PASS`
- `CUSTOMER_EMAILS_SENT=0`
- `FINAL_STATUS=PRODUCTION_SAFE_MODE_HEALTHY_EXTERNAL_GATES_REMAIN`
