# Campaign scheduling availability

The current runtime has no scheduled-campaign dispatcher. Both
`POST /v1/campaigns/{id}/schedule` and
`POST /v1/campaign-definitions/{id}/schedule` reject valid future requests with
HTTP 409 and `campaign_dispatcher_unavailable`. They require `campaign.manage`
and a tenant-owned campaign. Existing validation errors still apply.

No schedule, idempotent success, audit success, or outbox work is written.
Retrying the same key cannot return an earlier accepted scheduling promise.
Previously persisted schedules remain historical data; operators must review
them before any future dispatcher is activated. This change never sends them.

Scheduling can become available only with a tested dispatcher that provides
leases, idempotent submission, retry limits, coordinated cancellation,
observability, and rollback. A successful API test or preflight does not prove
that campaign delivery exists.

## Validation and rollback

`tests/test_campaign_scheduling_truth.py` exercises both HTTP surfaces, repeat
requests, permission denial, and absence of scheduling or outbox side effects.
The existing mutation and messaging suites cover validation and cancellation.
No database migration or runtime secret change is required. Reverting this
guard would restore a false acceptance response; keep the guard until a
dispatcher is reviewed and certified. Existing delivery activation gates remain
required.
