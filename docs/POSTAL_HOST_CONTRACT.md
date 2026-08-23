# Postal API host contract

- Canonical/public web host: `app.klyrow.com`
- Internal Docker service host: `postal-web`
- API base URL: `http://postal-web:5000`
- HTTP Host header: `app.klyrow.com`
- TLS SNI: not applicable to the private plaintext Docker hop

The private hop is confined to the Klyrow backend network. Postal enforces its
canonical web host, so workers must set `KLYROW_POSTAL_API_HOST_HEADER` rather
than relying on DNS or proxy side effects. Production defaults to
`app.klyrow.com`; an empty value is permitted only for test fixtures whose
Postal endpoint does not enforce a canonical Host.

Campaign execution defaults to `CAMPAIGN_EXECUTION_DISABLED`. The distinct
`CAMPAIGN_CANARY_ONLY` mode requires production, an explicit enable flag, one
authorized tenant and campaign, exactly one server-configured allowlisted
recipient, and the existing sender, domain, consent, suppression, quota, rate,
reputation, and abuse checks. It does not enable bulk or unrestricted campaign
production.
