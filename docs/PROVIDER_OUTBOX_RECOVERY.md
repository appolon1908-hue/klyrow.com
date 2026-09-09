# Provider outbox and alert recovery

The September 9 runtime review found 82 provider dead letters and one usage
dead letter on 37.27.128.39. These are integration records, not a count of
undelivered external emails. No queued or retrying rows remained. The worker
image was `da9d85891a4e313748e309aed86662d6c03d26bb` and did not contain the
reconciliation API already implemented on main. No production rows were changed.

## Recovery order

1. Release the reviewed source through `scripts/verify-release-authority` and
   the protected image/configuration workflow. Preserve backup, prior digest,
   migration evidence, and the email activation controls from PR #106. Drain
   the old worker before switching: the new usage dispatcher claims records
   as PROCESSING using `available_at` as a five-minute lease. No schema change
   is required. For rollback, stop the new worker and reconcile any PROCESSING
   usage rows before running an older worker, which cannot recover that state.
2. Authenticate as the approved tenant-scoped platform-admin service. Read
   `GET /v1/internal/email/operations/health`; `outbox.version` must be 1.
   The new status counts contain no message contents or recipient identities.
3. For each affected tenant, call
   `POST /v1/internal/email/operations/outbox/reconcile` with `apply:false`,
   a meaningful `reason`, and `limit:50` or smaller. Review the returned
   requeue/skip/block counts. Existing logic validates tenant ownership and
   attachment completeness; never reconstruct missing attachment bytes.
4. Inspect the accepted accounting event and confirm destination readiness.
   The other inbound records comprised 78 quarantined messages and two
   accepted local-inbox messages. Preserve their retained content and
   classification; do not forward them as accounting/support mail.
5. Review the sandbox lifecycle and usage records separately. Their history
   is not proof of external delivery or billable production usage. The mirrored
   Server A lifecycle schema accepts `provider=postal`; never relabel a
   sandbox event as Postal to force acceptance. Obtain the correct receiver
   disposition before any apply page containing these records.
6. Apply only a reviewed bounded reconciliation page through the same API with
   `apply:true` and `confirmation:"RECONCILE_PROVIDER_OUTBOX"`. The existing API
   records an audit event. Re-read status, the receiver inbox, and billing
   deduplication records before the next page. Keep blocked records visible.
   Do not directly update database states or replay SMTP messages.

The dispatcher now isolates malformed payloads and transport exceptions per
record, uses stable IDs for legacy events, fences acknowledgements to the
current claim, and recovers expired usage claims. HTTP response codes are
logged without response bodies or credentials. A successful callback response
only confirms transport acceptance; final downstream processing needs read-back.

## Alert route

Klyrow Prometheus had zero Alertmanager targets. The central instance at
65.109.65.169 had a separate receiver-file permission failure; fix that through
the `Codestra-Alertmanager` recovery runbook first. Its inventoried HTTP Docker
bridge listener is not a cross-host endpoint and must not be exposed publicly.

The reviewed native Alertmanager contract uses mTLS and the canonical TLS name
`aler.codestra.media`. Provision its private listener and Klyrow monitoring
client identity through the monitoring/ingress authority. Then render the
full Klyrow configuration with `scripts/render-alert-routing.py --target`
set to that reviewed private IPv4:port and `--environment production`. The
script preserves existing scrapes, requires certificate verification, and
prints configuration only. It never sends an alert or creates a listener.

Validate the result with the deployed version of `promtool check config`.
Include `compose.alert-routing.yaml`, its four required file references, and
the rendered configuration in the protected release checksum. Verify the
mounted client key is readable by Prometheus's existing non-root identity.
The optional overlay is not automatically included in standard launchers.

After deployment, `/api/v1/alertmanagers` must report the expected active target.
Read back the two actual Klyrow alert fingerprints in Alertmanager and their
Middleware notification receipts. Observe a fresh notification-success delta
with no corresponding failure delta. Do not treat cumulative counters or
`/-/ready` as delivery proof. The self-scrape and new routing alert expose a
missing route locally, but cannot deliver their own notification while the
route is broken. No notification probe was sent during this review.

Evidence: `docs/evidence/provider-recovery-20260909.json`.
