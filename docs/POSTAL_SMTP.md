# Postal SMTP production runbook

Postal `3.3.7` runs as separate web, worker, and SMTP containers. The web UI is proxied at `https://app.klyrow.com`; the SMTP/HELO hostname is `mail.klyrow.com`. MariaDB and RabbitMQ are on the internal `klyrow_backend` network. SMTP is intentionally published only as `127.0.0.1:2525 → postal-smtp:25`; management, databases, queues, and Docker remain private.

The server remains in Postal Development mode with a 10,000-message server
limit, while Klyrow has `safe_mode=true` and `production_gate_approved=false`.
Port 25 is now available for MX traffic and authenticated STARTTLS submission;
these application gates still prevent unrestricted production delivery.

Mautic `7.1.3` uses authenticated SMTP at `postal-smtp:25` over the private Compose network. A login-only probe passed; no DATA command or external delivery was performed. Plain SMTP is acceptable only on this isolated internal network. Public submission must require STARTTLS before authentication.

Public forward DNS, PTR, identity-matched FCrDNS, and Postal's DNS validation now
pass. Forced-IPv4 outbound TCP/25 passes to Google and Microsoft MX hosts.

The dedicated `mail.klyrow.com` Let's Encrypt certificate is deployed by
`/usr/local/sbin/deploy-klyrow-postal-tls`. Certbot calls the certificate-specific
hook `/etc/letsencrypt/renewal-hooks/deploy/klyrow-postal-tls`; it copies only the
full chain and private key into Postal's root-controlled secret directory and
restarts only `postal-smtp`. The private-key copy is mode `0600`. A Certbot ACME
staging dry run and the actual deploy hook both pass.

Live EHLO advertises STARTTLS. Verification with SNI and hostname checking
returns a trusted Let's Encrypt chain, SAN `mail.klyrow.com`, TLS 1.3, and verify
code 0. Public port 25 and loopback diagnostic port 2525 map only to Postal SMTP;
465 and 587 remain closed.

The unauthenticated relay probe reached `RCPT TO` without DATA and was rejected
with `530 Authentication required` on the public listener. Invalid authentication
was rejected with 535. Mautic authenticated over STARTTLS and issued only NOOP.

## Controlled canary result

The single held Odoo canary was released from the same stored Postal message;
no second submission was made. Gmail returned permanent SMTP error 550-5.7.26
because SPF and DKIM did not pass, so Postal recorded HardFail. Do not resend
until the envelope-domain SPF and DKIM failure are diagnosed and a new canary is
explicitly authorized. Postal is Live, but every existing credential is set to
hold, Klyrow safe mode remains enabled, and its production gate remains false.

`postal-worker` requires both `backend` and `frontend` networks: backend for
Postal databases/queues and frontend for recipient MX DNS and TCP/25 egress.
This attachment is persisted in Compose and exposes no worker port.

The first message contained a DKIM header, but Postal generated its fallback
signature: `d=bounce.klyrow.com; s=postal`. Postal does that when the sending
domain's cached DKIM status is not `OK`; no corresponding fallback selector was
published. The cached state was refreshed without rotating the valid key. A
local non-delivering proof now cryptographically verifies `d=klyrow.com;
s=postal-QQaKrT`. The live public key and DNS key have the same SHA-256 digest.

One dedicated Postal webhook now targets
`http://gateway:8000/v1/webhooks/postal-native`. Postal's SSRF allowlist permits
that service name. Events include sent, delivery failed, bounce, delayed, held,
loaded, and link clicked. Postal signs the exact body with RSA-SHA256; Klyrow
verifies it, persists event ID/correlation/delivery state, normalizes the event,
and emits the existing bearer-authenticated HMAC middleware contract. Failures
return 503 for Postal's bounded five-attempt schedule; Klyrow marks the fifth
failure as DLQ. Completed event IDs are idempotently acknowledged.

The recorded message-1 HardFail was replayed as metadata only and accepted as
`email.bounced`, preserving correlation ID
`klyrow-odoo-canary-ad53bfce26504919907e4fe14eef10c4`. It created no email.
Middleware accepted it; downstream n8n/Odoo completion is not yet proven.

The dedicated deployment identity was restored. Connection-only tests from `37.27.128.39` received `220` banners from Gmail and Outlook MX hosts, so outbound TCP/25 is PASS. No `EHLO`, envelope command, or message data was sent to either host. `scripts/mail-readiness` now repeats these bounded connection/banner checks.

The deployment identity remains intentionally least-privilege. Preserve provider and firewall controls; do not broaden access merely to bypass the PTR gate.
