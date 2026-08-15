# Deliverability and acceptable use

Only opt-in and transactional mail is permitted. A sender must own a verified domain. Klyrow checks tenant quotas, per-minute limits, suspension state, sender domain, suppressions and unsubscribes before Postal submission. Hard bounces, complaints and unsubscribes must immediately enter the tenant suppression list. Operators should suspend a tenant on abnormal complaint or bounce spikes and investigate before re-enabling it.

Launch requires aligned SPF, Postal-generated DKIM, DMARC, forward-confirmed PTR, `mail.klyrow.com` HELO, valid SMTP TLS, functioning bounce MX, complaint handling, one-click unsubscribe for marketing messages, and monitored queues. Warm sending gradually; do not evade provider controls or send unsolicited bulk mail.

The exact live selector, return-path, verification token, and provider actions are in [MAIL_DNS.md](MAIL_DNS.md). Keep DMARC at monitoring mode until controlled-message headers consistently show aligned SPF and DKIM, then progress to quarantine and reject. No reporting address is published until an owned mailbox is approved.

Safe mode, verified sender domains, consent/preferences, per-tenant daily quota, suppression checks, idempotency keys, tenant suspension, and authenticated SMTP provide the current abuse controls. A bounce, complaint, or unsubscribe webhook creates a suppression. The in-process request rate limiter is single-instance only; replace it with shared state before horizontal scaling. Never clear safe mode or permit unrestricted campaigns based on DNS configuration alone.
