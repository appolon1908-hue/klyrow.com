# Klyrow SECURITY SMTP runtime activation

This runbook activates only the dedicated Keycloak password-recovery stream.
It does not enable general transactional, marketing, campaign, or bulk delivery.

## Immutable source

Deploy from a protected merged `main` SHA. Render the runtime with both Compose
files so the SMTP relay receives the same fail-closed gates as the mail worker:

```bash
docker compose \
  -f docker-compose.yml \
  -f compose.security-smtp.yaml \
  --env-file /approved/path/klyrow.env \
  config --quiet
```

Do not use the feature branch or an unreviewed local checkout.

## Required runtime records

Before setting either live gate, establish one dedicated Klyrow tenant and verify:

```text
SMTP_CREDENTIAL=ACTIVE
SMTP_CREDENTIAL_STREAMS=["SECURITY"]
SMTP_CREDENTIAL_ALLOWED_SENDERS=[<exact reviewed sender>]
SMTP_CREDENTIAL_EXPIRY=FUTURE
SENDER_IDENTITY=ACTIVE
SENDER_IDENTITY_STREAM=SECURITY
PROVIDER_DOMAIN=SENDING_ENABLED
PROVIDER_DOMAIN_SENDING_ENABLED=true
TENANT=ENABLED
TENANT_MAIL_POLICY_REPUTATION!=SUSPENDED
```

The SMTP password is stored outside Git and is never accepted by the preflight
command. Rotate the previously exposed Postal DKIM keys before activation.

## Disabled deployment

First deploy the merged application and migrations with:

```text
KLYROW_SECURITY_SMTP_ENABLED=false
KLYROW_SECURITY_SMTP_LIVE_ENABLED=false
KLYROW_SECURITY_SMTP_PRODUCTION_APPROVED=false
KLYROW_SECURITY_SMTP_EXPECTED_MODE=disabled
```

Then run:

```bash
docker compose \
  -f docker-compose.yml \
  -f compose.security-smtp.yaml \
  --env-file /approved/path/klyrow.env \
  exec -T worker python -m app.security_smtp_preflight
```

The command is read-only and prints no credential secret.

## One-recipient canary

For the genuine Keycloak reset test, authorize only a controlled mailbox:

```text
KLYROW_SECURITY_SMTP_ENABLED=true
KLYROW_SECURITY_SMTP_LIVE_ENABLED=true
KLYROW_SECURITY_SMTP_PRODUCTION_APPROVED=false
KLYROW_SECURITY_SMTP_CANARY_RECIPIENTS=reset-canary@example.com
KLYROW_SECURITY_SMTP_CANARY_MAX_DELIVERIES=1
KLYROW_SECURITY_SMTP_EXPECTED_MODE=canary
```

The relay rejects every other external recipient, a second recipient in the
same message, and any delivery beyond the reviewed canary allowance.

Restart only the `smtp-relay` and `worker` services after reviewing the rendered
environment:

```bash
docker compose \
  -f docker-compose.yml \
  -f compose.security-smtp.yaml \
  --env-file /approved/path/klyrow.env \
  up -d --no-deps smtp-relay worker
```

Rerun `app.security_smtp_preflight`, verify private STARTTLS on
`10.40.0.4:587`, and then execute one real Keycloak forgot-password transaction.

## Production promotion

Production approval is a separate change. Clear the temporary canary list and
set:

```text
KLYROW_SECURITY_SMTP_PRODUCTION_APPROVED=true
KLYROW_SECURITY_SMTP_EXPECTED_MODE=production
```

Keep these unrelated capabilities disabled:

```text
LIVE_EMAIL_DELIVERY=false
EXTERNAL_EMAIL_DELIVERY=false
MARKETING_DELIVERY=false
KLYROW_BULK_DELIVERY_ENABLED=false
KLYROW_CAMPAIGN_DELIVERY_ENABLED=false
```

## Evidence required

Record only privacy-safe evidence:

```text
merged source SHA
rendered Compose SHA-256
runtime image digest
SMTP TLS peer certificate fingerprint
credential ID and expiry (never the password)
sender and domain status
Keycloak correlation ID
Klyrow message ID
Postal provider message ID
delivery outcome and timestamps
reset-link one-time-use result
reset-link expiration result
forced reauthentication result
```

Never record the reset token, complete reset URL, password, SMTP password, raw
MIME body, or Keycloak session token in workflow summaries, middleware events,
Odoo, n8n, analytics, or logs.
