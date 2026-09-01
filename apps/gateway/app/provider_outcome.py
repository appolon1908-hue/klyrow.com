"""Fail-closed handling for ambiguous provider submission outcomes."""

import httpx


INDETERMINATE = "INDETERMINATE"


def provider_outcome_is_ambiguous(exc: Exception) -> bool:
    """Return true when Postal may have accepted a request before failure."""

    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError))


def reconcile_before_retry(
    *,
    state: str,
    provider_message_id: str | None,
    provider_absence_confirmed: bool,
) -> bool:
    """Permit an indeterminate retry only after authoritative absence proof."""

    if state != INDETERMINATE:
        return True
    if provider_message_id:
        return False
    return provider_absence_confirmed is True
