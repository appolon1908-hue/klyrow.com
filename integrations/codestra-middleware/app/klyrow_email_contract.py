"""Response binding shared by the two Klyrow command adapters."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def document_digest(document: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def matches(request: Any, document: dict[str, Any], value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("message_id"), str)
        and bool(value["message_id"])
        and value.get("command_id") == request.command_id
        and value.get("tenant_id") == request.tenant_id
        and value.get("correlation_id") == request.correlation_id
        and value.get("request_hash") == document_digest(document)
        and isinstance(value.get("sender"), str)
        and value["sender"].lower() == document["sender"].lower()
        and value.get("recipients") == [address.lower() for address in document["recipients"]]
    )


ACCEPTED_STATUSES = frozenset({"accepted", "queued", "sending", "processing", "submitted", "sent", "delivered"})
