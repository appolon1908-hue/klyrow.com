"""Versioned, context-authenticated control replays and integration results.

Legacy JSON remains read-only compatible during an explicit rollout; every new
control replay/result is encrypted with a dedicated file-backed keyring.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException

from .durable_keys import KeyringError, load_keyring

FORMAT = "klyrow-durable-result.v1"
MAX_RESULT_BYTES = 65536
MAX_ENVELOPE_BYTES = 131072
MAX_DOCUMENT_BYTES = MAX_RESULT_BYTES + 1024
_SENSITIVE = ("password", "secret", "token", "authorization", "cookie", "credential", "privatekey",
              "apikey", "accesskey", "signature", "session", "reseturl", "verificationurl")
_CONTENT = {"body", "raw", "mime", "html", "htmlbody", "textbody", "headers", "url", "uri",
            "email", "recipient", "recipients", "phone", "cardnumber", "cvv"}


def _unavailable() -> HTTPException:
    return HTTPException(503, "durable_result_unavailable")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_result_field")
        result[key] = value
    return result


def _loads(raw):
    return json.loads(raw, object_pairs_hook=_unique_object)


def canonical(value: dict[str, Any], *, limit: int = MAX_RESULT_BYTES) -> bytes:
    if not isinstance(value, dict):
        raise ValueError("result_must_be_object")
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(raw) > limit:
        raise ValueError("result_too_large")
    return raw


def redact_result(value: dict[str, Any]) -> dict[str, Any]:
    canonical(value)
    def visit(item, depth=0):
        if depth > 12:
            raise ValueError("result_too_deep")
        if isinstance(item, dict):
            output = {}
            for name, child in item.items():
                normalized = re.sub(r"[^a-z0-9]", "", name.lower())
                output[name] = "[REDACTED]" if any(word in normalized for word in (*_CONTENT, *_SENSITIVE)) else visit(child, depth + 1)
            return output
        if isinstance(item, list):
            if len(item) > 1000:
                raise ValueError("result_list_too_large")
            return [visit(child, depth + 1) for child in item]
        return item
    return visit(value)


def _binding(kind: str, *parts: str) -> list[str]:
    if any(not isinstance(part, str) or not part for part in parts):
        raise _unavailable()
    return [kind, *parts]


def seal(value: dict[str, Any], binding: list[str]) -> str:
    try:
        keys = load_keyring()
        kid = keys.active_key_id
        nonce = secrets.token_bytes(12)
        aad = json.dumps([FORMAT, kid, *binding], separators=(",", ":")).encode()
        cipher = AESGCM(keys.keys[kid]).encrypt(nonce, canonical(value, limit=MAX_DOCUMENT_BYTES), aad)
        return json.dumps({"format": FORMAT, "kid": kid,
                           "nonce": base64.urlsafe_b64encode(nonce).decode(),
                           "ciphertext": base64.urlsafe_b64encode(cipher).decode()}, separators=(",", ":"), sort_keys=True)
    except (KeyringError, ValueError, TypeError, OverflowError, RecursionError):
        raise _unavailable() from None


def unseal(raw: str, binding: list[str]) -> dict[str, Any]:
    try:
        if not isinstance(raw, str) or len(raw.encode()) > MAX_ENVELOPE_BYTES:
            raise ValueError
        value = _loads(raw)
        if not isinstance(value, dict):
            raise ValueError
        if "format" not in value:
            if os.getenv("KLYROW_DURABLE_RESULT_LEGACY_READ_ENABLED", "true").lower() != "true":
                raise ValueError
            canonical(value)
            return value
        if value.get("format") != FORMAT or set(value) != {"format", "kid", "nonce", "ciphertext"}:
            raise ValueError
        keys = load_keyring()
        kid = value["kid"]
        nonce = base64.b64decode(value["nonce"], altchars=b"-_", validate=True)
        ciphertext = base64.b64decode(value["ciphertext"], altchars=b"-_", validate=True)
        if len(nonce) != 12:
            raise ValueError
        aad = json.dumps([FORMAT, kid, *binding], separators=(",", ":")).encode()
        result = _loads(AESGCM(keys.keys[kid]).decrypt(nonce, ciphertext, aad))
        canonical(result, limit=MAX_DOCUMENT_BYTES)
        return result
    except (KeyringError, KeyError, ValueError, TypeError, InvalidTag, UnicodeError, RecursionError):
        raise _unavailable() from None


def seal_control_response(value, *, tenant_id, storage_key, request_hash, resource_id):
    return seal(value, _binding("control-replay", tenant_id, storage_key, request_hash, resource_id))


def read_control_response(row):
    return unseal(row.response_json, _binding("control-replay", row.tenant_id, row.key, row.request_hash, row.resource_id))


def seal_integration_result(value, *, tenant_id, outbox_id, source, result_key):
    digest = hashlib.sha256(canonical(value)).hexdigest()
    document = {"schema_version": 1, "request_hash": digest, "result": redact_result(value)}
    return seal(document, _binding("integration-result", tenant_id, outbox_id, source, result_key))


def integration_document(row):
    value = unseal(row.payload_json, _binding("integration-result", row.tenant_id, row.outbox_id, row.source, row.result_key))
    envelope = _loads(row.payload_json)
    if envelope.get("format") == FORMAT:
        if set(value) != {"schema_version", "request_hash", "result"} or type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise _unavailable()
        if not isinstance(value["request_hash"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["request_hash"]):
            raise _unavailable()
        return redact_result(value["result"]), value["request_hash"]
    return redact_result(value), hashlib.sha256(canonical(value)).hexdigest()


def result_matches(row, value):
    return secrets.compare_digest(integration_document(row)[1], hashlib.sha256(canonical(value)).hexdigest())


def result_readback(row, *, current: datetime | None = None):
    """Do not silently present absent, malformed, or expired results as success."""
    metadata = {"schema_version": 1, "availability": "UNAVAILABLE", "expires_at": None}
    if row is None:
        return {}, metadata
    try:
        retention = int(os.getenv("KLYROW_RESULT_RETENTION_SECONDS", "2592000"))
        if not 3600 <= retention <= 7776000:
            raise ValueError
        created = row.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        expires = created + timedelta(seconds=retention)
        metadata["expires_at"] = expires.isoformat()
        if expires <= (current or datetime.now(timezone.utc)):
            metadata["availability"] = "EXPIRED"
            return {}, metadata
        payload, _ = integration_document(row)
        metadata["availability"] = "AVAILABLE"
        return payload, metadata
    except (HTTPException, ValueError, TypeError, AttributeError, OverflowError, RecursionError):
        metadata["availability"] = "INVALID"
        return {}, metadata


def rewrap_integration_result(row):
    """Preserve the original semantic digest, including fields removed by redaction."""
    payload, digest = integration_document(row)
    return seal({"schema_version": 1, "request_hash": digest, "result": payload},
                _binding("integration-result", row.tenant_id, row.outbox_id, row.source, row.result_key))
