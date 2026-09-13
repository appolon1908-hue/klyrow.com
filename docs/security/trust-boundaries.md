# Trust boundaries

| Caller | Destination | Authority | Required verification |
| --- | --- | --- | --- |
| Customer | Caddy → Kong → `/v1/` | Valid Keycloak identity or tenant-bound product API key | Signature, issuer/audience, membership, scope, limits; reconstruct tenant headers |
| Browser | Same-origin BFF | HttpOnly OIDC session and CSRF token | Cookie origin, per-flow state, PKCE, MFA and session deadlines |
| SMTP client | Klyrow submission | TLS and one-time-issued hashed SMTP credential | Tenant, sender/domain, quota and suppression checks before durable acceptance |
| Postal | Klyrow callback | Provider signature and bound delivery identity | Signature, timestamp, deduplication and tenant attribution |
| Klyrow | Middleware receiver | Existing signed event contract and restricted mTLS edge | Source, timestamp, replay/body binding; migration to service JWT/mTLS is coordinated |
| Middleware | Odoo external API | Dedicated restricted bot credential | Allowed models/methods, idempotent writes, audit and retry |
| Alertmanager | Middleware alert receiver | Restricted service identity | Firing/resolved identity, classification and `odoo_sync` routing |
| Collectors | Prometheus/Loki/Tempo | Private scoped telemetry credentials | Ingestion authorization and bounded, redacted labels |
| Grafana | Observability queries | Keycloak viewer and datasource reader | No ingestion/admin/business writer credentials |
| Superset | Analytics views | `superset_reader` | SELECT only, no writer or SQL Lab authority for ordinary viewers |

## Sole Odoo writer

Only code deployed as Middleware may load an Odoo write credential. The included
Middleware adapter under `integrations/codestra-middleware/` is a source overlay,
not part of the gateway image. A directory name by itself is not an authorization
boundary: image contents, service mounts, service identity, OpenBao ACL and
network/firewall policy must agree.

Gateway runtime must never import the Middleware Odoo writer or mount its
credential. Odoo references in tenant metadata and durable integration commands
are allowed; direct RPC clients, SQL clients and credentials are not. The M00
source scan identifies only the inbound-mail writer described in current-state.
There is no deployment evidence here proving Klyrow → Odoo network denial.

## Sensitive data

See `secret-references.json` for names/locations, never values. Secret scanning
must cover Git-tracked content; do not print `.env` or mounted secret files.
Customer API keys and SMTP credentials remain non-retrievable hashes. Webhook
signing requires recoverable protected signing material and independent rotation;
a hash cannot be used as its replacement.

KPI synchronization must use an explicit field allowlist and aggregates. Do not
forward raw message bodies, reset links, API/SMTP passwords, private keys or raw
telemetry to Odoo. The historical inbound helpdesk/accounting mail integration
is a separate, explicit content-bearing workflow; do not reuse it for KPI sync.

## Gaps that require tests, not assumptions

The application tenant-filter tests do not establish PostgreSQL RLS. Static
configuration tests do not establish deployed firewall or OpenBao enforcement.
The source includes public health/metadata and signed callback routes by design;
an anonymous route is not automatically an unprotected admin endpoint. Exact
platform-owner OIDC/MFA checks and tenant authorization must be tested through
the composed app. New `/internal/v1/` paths must be classified INTERNAL both in
OpenAPI and at the edge.
