# Klyrow production go-live audit

Date: 2026-08-30  
Audited repository head: `57678867166043c2351d56f58ad47785e9456c18`  
Audited host: `37.27.128.39` / private `10.40.0.4`

## Verdict

`NO_GO_FOR_UNRESTRICTED_PRODUCTION`

The host is already configured for live email delivery, but the running
software and the committed integration contract do not satisfy the required
production gates. No additional delivery gate was opened during this audit.

## Directly verified passes

- `api.klyrow.com/healthz` and `/readyz`: HTTP 200.
- `app.klyrow.com`: HTTP 200.
- Keycloak discovery for the Codestra realm: HTTP 200.
- `mail.klyrow.com` A: `37.27.128.39`.
- PTR: `37.27.128.39 -> mail.klyrow.com`.
- FCrDNS: `mail.klyrow.com -> 37.27.128.39`.
- Public SMTP STARTTLS: trusted certificate for `mail.klyrow.com`, TLS 1.3,
  certificate verification successful.
- Postal reports all 14 approved domains verified with SPF, DKIM, MX, and
  return-path status `OK`; `booked4seasons.com` is absent.
- The owner-authorized paced sender verification is bounded to three approved
  recipients and one sender every 30 minutes. At audit time 54 of 118 senders
  had been accepted (162 recipient deliveries); Postal recorded all 162 as
  `Sent`, with no queue-pressure pause or recorded campaign error.
- Exact `main` test suite: 253 passed, 31 strict expected failures.
- Main CI is green at the audited repository head.
- Nightly Klyrow backup and Certbot timers are active.

## DNS change applied

Thirteen domains lacked SPF at their `bounce.<domain>` return-path hostname.
The additive record below was applied through the GoDaddy API without changing
any existing record:

```text
bounce.<domain> TXT "v=spf1 include:spf.klyrow.com -all" TTL 600
```

Affected domains:

- `beyvra.com`
- `breero.com`
- `breero.shop`
- `codestra.agency`
- `codestra.cloud`
- `codestra.co`
- `codestra.digital`
- `codestra.media`
- `kyqra.com`
- `moneybee.loan`
- `moneybeeloan.com`
- `nativoenglish.com`
- `telnexa.co`

Final verification: 52/52 answers passed across both authoritative GoDaddy
nameservers for every domain, Cloudflare `1.1.1.1`, and Google `8.8.8.8`.
`bounce.klyrow.com` already had the required record and was not changed.

Operational backups:

- `/root/klyrow-backups/godaddy-bounce-spf-prechange-20260830T192224Z`
- `/root/klyrow-backups/godaddy-bounce-spf-finalcheck-20260830T192224Z`

## Production blockers

1. The running gateway and SMTP-relay images still contain
   `SIMULATED_PUBLIC_KEY` in the tenant DKIM rotation endpoint. The production
   database audit found zero issued simulated keys and zero affected domains,
   so this is not presently a tenant incident; it remains a release blocker.
2. The running SMTP relay queries `Suppression` directly and rejects every
   suppression at RCPT. It does not use the stream-aware canonical suppression
   function, so transactional SMTP behavior diverges from the API path.
3. The running SMTP relay inserts `ProviderMessage` and `ProviderAudit` but no
   canonical billing `UsageEvent`; SMTP submissions remain unmetered.
4. The repository's executable mail register still has 31 strict expected
   failures. Confirmed production-relevant gaps include inbound authentication,
   ambiguous-provider reconciliation, one-click unsubscribe injection, enhanced
   bounce classification, stream priority, and canonical metering.
5. Runtime activation drift exists. The gateway and worker currently have
   `KLYROW_SAFE_MODE=false`, `KLYROW_PRODUCTION_GATE_APPROVED=true`,
   `LIVE_EMAIL_DELIVERY=true`, `EXTERNAL_EMAIL_DELIVERY=true`, and
   `PRODUCTION_PROVIDER_ROUTING=true`, while the committed integration manifests
   still state `PREPARED_NOT_DEPLOYED` and keep production gates false.
6. Receiver-side SPF/DKIM/DMARC evidence for the paced messages has not been
   captured. Postal `Sent` is provider acceptance evidence, not inbox/authentication
   evidence.

## Required next change

Do not broaden recipients, enable bulk/campaign sending, or advertise unrestricted
production until the live runtime is replaced by an immutable reviewed release
that closes the blockers above, the contract matches the runtime, rollback is
rehearsed, and a bounded receiver-side canary confirms SPF, DKIM, and DMARC.

Telephony production dialing and the private observability services were not
activated or modified by this audit.
