# TLS lifecycle

Certbot manages the current trusted `klyrow.com` certificate (apex, `www`, `app`, `api`, `track`, and `bounce`) and the active `certbot.timer`; nginx reload is installed as a deploy hook. The certificate expires 2026-11-13. Its private key is root-only (`0600`) beneath a root-only Let's Encrypt directory.

`mail.klyrow.com` now publicly resolves to `37.27.128.39`, but its required PTR still returns `static.39.128.27.37.clients.your-server.de.`. The continuation gate requires DNS and PTR to pass before certificate issuance, so no mail certificate has been requested or installed. Do not replace or disturb the existing web certificate. Once PTR is corrected, use `scripts/install-postal-tls` and a narrow Certbot deploy hook to refresh only Postal's certificate copy and SMTP service.

STARTTLS is currently disabled and therefore FAIL/BLOCKED-EXTERNAL, not provisionally passed. Renewal is operational for web TLS; Postal auto-reload becomes testable only after the mail certificate exists.

The latest authoritative recheck confirms the mail A record is live. ACME issuance and Postal restart remain gated only by the required PTR correction.
