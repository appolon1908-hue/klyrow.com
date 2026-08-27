# Browser edge and authentication contract

`app.klyrow.com` is the only public browser and OIDC BFF origin. The production
callback is exactly `https://app.klyrow.com/auth/callback`; it is never derived
from a browser-controlled origin or forwarded hostname.

The public hosts have separate responsibilities:

- `app.klyrow.com` routes to the frontend on loopback port `18004`. The
  frontend proxies `/auth`, `/app/api`, and `/v1` to the matching gateway.
- `api.klyrow.com` routes to the gateway but rejects browser/BFF and SPA paths.
- `track.klyrow.com` exposes only `/t/*` tracking-token requests and returns 404
  for application pages.
- `bounce.klyrow.com` is a transport identity and does not serve a web app.
- Unknown and sender-domain tracking hosts such as `track.codestra.co` must be
  rejected by the TLS default vhost and by the frontend container host guard.

## Atomic activation gate

Do not point the provider edge at the frontend until the matching gateway and
web images are running together. Before `nginx -t` and a graceful reload, run:

```bash
KLYROW_EDGE_BASE_URL=http://127.0.0.1:18004 scripts/verify-browser-edge
```

The probe requires the SPA, BFF session endpoint, exact Keycloak redirect URI,
and wrong-host rejection to pass together. A frontend-only deployment is not a
valid release because it would render the UI while `/auth/*` and `/app/api/*`
remain unavailable.

The edge/authentication release does not authorize mail delivery. Keep
`KLYROW_SAFE_MODE=true`, `LIVE_EMAIL_DELIVERY=false`,
`EXTERNAL_EMAIL_DELIVERY=false`, and `PRODUCTION_PROVIDER_ROUTING=false` until
the independent mail-production gate is approved.
