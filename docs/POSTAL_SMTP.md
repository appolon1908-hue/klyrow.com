# Postal SMTP production runbook

Postal `3.3.7` runs as separate web, worker, and SMTP containers. The web UI is proxied at `https://app.klyrow.com`; the SMTP/HELO hostname is `mail.klyrow.com`. MariaDB and RabbitMQ are on the internal `klyrow_backend` network. SMTP is intentionally published only as `127.0.0.1:2525 → postal-smtp:25`; management, databases, queues, and Docker remain private.

The server is in Postal Development mode with a 10,000-message server limit, while Klyrow has `safe_mode=true` and `production_gate_approved=false`. Do not change these gates or expose public submission until [MAIL_DNS.md](MAIL_DNS.md) passes.

Mautic `7.1.3` uses authenticated SMTP at `postal-smtp:25` over the private Compose network. A login-only probe passed; no DATA command or external delivery was performed. Plain SMTP is acceptable only on this isolated internal network. Public submission must require STARTTLS before authentication.

After DNS/PTR pass:

1. Issue the `mail.klyrow.com` certificate with the existing Certbot nginx/webroot lifecycle.
2. Run `scripts/install-postal-tls`; it validates the certificate name, copies only the required certificate/key with restricted permissions, enables Postal TLS, and restarts only `postal-smtp`.
3. Install the same command as a Certbot deploy hook and test renewal with `certbot renew --dry-run`.
4. Verify `EHLO` advertises STARTTLS and `openssl s_client -starttls smtp -connect mail.klyrow.com:25 -servername mail.klyrow.com -verify_hostname mail.klyrow.com -verify_return_error` succeeds with a modern protocol and full chain.
5. Expose only port 25 for server-to-server SMTP. Add 587 only if authenticated public submission is explicitly required. Do not open 465 or 2525 by default.

The unauthenticated relay probe reached `RCPT TO` without DATA and was rejected with `530 Authentication required`. Repeat externally after port 25 is deliberately opened.

The latest verification run could not repeat server-local TCP/25 or SMTP checks because `37.27.128.39` rejected every available SSH identity. Treat the earlier connection timeout as superseded only after a new connection-level test from that exact server succeeds; the provider's policy notification alone is not PASS evidence.
