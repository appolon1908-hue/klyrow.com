"""Ephemeral encrypted storage for SECURITY-stream MIME payloads.

Identity-security mail can contain password-reset links or one-time verification
codes.  Klyrow therefore never stores SECURITY raw MIME as plaintext/base64.
The relay encrypts the MIME body with a dedicated Fernet key and the security
worker scrubs ciphertext immediately after successful provider submission (or
when a message is terminally dead-lettered/expired).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


PAYLOAD_VERSION = "fernet-v1"
DEFAULT_MAX_AGE_SECONDS = 3600


class SecurityPayloadError(ValueError):
    """Raised when a SECURITY payload cannot be safely encrypted/decrypted."""


def _key_path() -> Path:
    raw = os.getenv("KLYROW_SECURITY_PAYLOAD_KEY_FILE", "").strip()
    if not raw:
        raise SecurityPayloadError("KLYROW_SECURITY_PAYLOAD_KEY_FILE is required")
    return Path(raw)


def _fernet() -> Fernet:
    try:
        key = _key_path().read_bytes().strip()
    except OSError as exc:
        raise SecurityPayloadError("SECURITY payload encryption key is unavailable") from exc
    try:
        return Fernet(key)
    except (TypeError, ValueError) as exc:
        raise SecurityPayloadError("SECURITY payload encryption key is invalid") from exc


def max_payload_age_seconds() -> int:
    raw = os.getenv(
        "KLYROW_SECURITY_PAYLOAD_MAX_AGE_SECONDS",
        str(DEFAULT_MAX_AGE_SECONDS),
    ).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise SecurityPayloadError(
            "KLYROW_SECURITY_PAYLOAD_MAX_AGE_SECONDS must be an integer"
        ) from exc
    if value < 300 or value > 86400:
        raise SecurityPayloadError(
            "KLYROW_SECURITY_PAYLOAD_MAX_AGE_SECONDS must be between 300 and 86400"
        )
    return value


def encrypted_security_payload(
    raw: bytes,
    *,
    raw_sha256: str,
    message_id: str,
    stream: str,
) -> dict[str, Any]:
    if stream.upper() != "SECURITY":
        raise SecurityPayloadError("encrypted SECURITY payload requires SECURITY stream")
    token = _fernet().encrypt(raw).decode("ascii")
    return {
        "raw_sha256": raw_sha256,
        "encrypted_raw": token,
        "encryption": PAYLOAD_VERSION,
        "message_id": message_id,
        "size": len(raw),
        "stream": "SECURITY",
    }


def decrypt_security_payload(payload: dict[str, Any]) -> bytes:
    if payload.get("stream") != "SECURITY":
        raise SecurityPayloadError("unexpected security payload stream")
    if payload.get("encryption") != PAYLOAD_VERSION:
        raise SecurityPayloadError("unsupported SECURITY payload encryption version")
    encoded = payload.get("encrypted_raw")
    if not isinstance(encoded, str) or not encoded:
        raise SecurityPayloadError("SECURITY payload ciphertext is missing")
    try:
        return _fernet().decrypt(encoded.encode("ascii"))
    except (InvalidToken, UnicodeEncodeError) as exc:
        raise SecurityPayloadError("SECURITY payload ciphertext is invalid") from exc


def scrubbed_security_payload(payload: dict[str, Any], *, reason: str) -> str:
    """Return privacy-safe JSON after the sensitive body has left its retry window."""

    safe = {
        "raw_sha256": str(payload.get("raw_sha256") or ""),
        "message_id": str(payload.get("message_id") or ""),
        "size": int(payload.get("size") or 0),
        "stream": "SECURITY",
        "body_state": "PURGED",
        "purge_reason": reason[:64],
    }
    return json.dumps(safe, separators=(",", ":"), sort_keys=True)
