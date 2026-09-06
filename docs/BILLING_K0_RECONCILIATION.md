# Billing route and backlog preservation

This selectively restores two behaviors identified by issue #49 from historical
tip `ad432f9bf598a629be2ca23c3663f7feb4064c81` onto current main.

The literal subscription `change` and `cancel` routes now register before the
generic `{status}` route. Clients reach plan-change and cancel-at-period-end
handlers instead of trying to transition to invalid states named CHANGE or
CANCEL. Existing tenant, transition, and pricing rules remain in the handlers.

Billing event discovery excludes events already represented in the durable
work ledger before applying the 200-event limit. Previously every tick scanned
the same oldest 200 events, preventing later events from entering the ledger.
The existing lease/retry processing remains intact, and the batch remains
bounded. No provider submission or external billing call is introduced.

`tests/test_billing_route_backlog.py` exercises both literal HTTP operations and
205 events with the first 200 already completed. It verifies later events are
processed exactly once. Existing service-boundary tests cover lease recovery.
No schema or live migration is required. Keep the corrected selection on
rollback to avoid starving existing backlog. This closes only the billing
subpart of the historical audit, not all of #49.
