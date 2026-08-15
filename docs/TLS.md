# TLS lifecycle

Certbot manages the current trusted `klyrow.com` certificate (apex, `www`, `app`, `api`, `track`, and `bounce`) and the active `certbot.timer`; nginx reload is installed as a deploy hook. The certificate expires 2026-11-13. Its private key is root-only (`0600`) beneath a root-only Let's Encrypt directory.

`mail.klyrow.com` is intentionally not on that certificate because public DNS is missing. Do not request it until its A record resolves to `37.27.128.39`. Do not replace or disturb the existing web certificate. Once issued, use `scripts/install-postal-tls` and a narrow Certbot deploy hook to refresh only Postal's certificate copy and SMTP service.

STARTTLS is currently disabled and therefore FAIL/BLOCKED-EXTERNAL, not provisionally passed. Renewal is operational for web TLS; Postal auto-reload becomes testable only after the mail certificate exists.

The latest authoritative recheck still found no `mail.klyrow.com` A record. ACME issuance and Postal restart remain prohibited until that prerequisite is live.
