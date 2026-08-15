# Deliverability and acceptable use

Only opt-in and transactional mail is permitted. A sender must own a verified domain. Klyrow checks tenant quotas, per-minute limits, suspension state, sender domain, suppressions and unsubscribes before Postal submission. Hard bounces, complaints and unsubscribes must immediately enter the tenant suppression list. Operators should suspend a tenant on abnormal complaint or bounce spikes and investigate before re-enabling it.

Launch requires aligned SPF, Postal-generated DKIM, DMARC, forward-confirmed PTR, `mail.klyrow.com` HELO, valid SMTP TLS, functioning bounce MX, complaint handling, one-click unsubscribe for marketing messages, and monitored queues. Warm sending gradually; do not evade provider controls or send unsolicited bulk mail.
