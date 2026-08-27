import json

from cryptography.fernet import Fernet
import pytest

from app.security_payload import (
    SecurityPayloadError,
    decrypt_security_payload,
    encrypted_security_payload,
    max_payload_age_seconds,
    scrubbed_security_payload,
)


def configure_key(tmp_path, monkeypatch):
    key_file = tmp_path / "security-payload-key"
    key_file.write_bytes(Fernet.generate_key() + b"\n")
    monkeypatch.setenv("KLYROW_SECURITY_PAYLOAD_KEY_FILE", str(key_file))
    return key_file


def test_security_payload_is_encrypted_and_scrubbed(tmp_path, monkeypatch):
    configure_key(tmp_path, monkeypatch)
    raw = b"Subject: Verify\r\n\r\nYour code is 482731"
    payload = encrypted_security_payload(
        raw,
        raw_sha256="abc123",
        message_id="<message@example.test>",
        stream="SECURITY",
    )

    serialized = json.dumps(payload)
    assert "482731" not in serialized
    assert "raw_b64" not in payload
    assert payload["encryption"] == "fernet-v1"
    assert decrypt_security_payload(payload) == raw

    scrubbed = json.loads(scrubbed_security_payload(payload, reason="provider_submitted"))
    assert scrubbed["body_state"] == "PURGED"
    assert scrubbed["purge_reason"] == "provider_submitted"
    assert "encrypted_raw" not in scrubbed
    assert "482731" not in json.dumps(scrubbed)


def test_security_payload_key_is_required(monkeypatch):
    monkeypatch.delenv("KLYROW_SECURITY_PAYLOAD_KEY_FILE", raising=False)
    with pytest.raises(SecurityPayloadError):
        encrypted_security_payload(
            b"secret",
            raw_sha256="digest",
            message_id="message",
            stream="SECURITY",
        )


def test_payload_retention_is_bounded(monkeypatch):
    monkeypatch.setenv("KLYROW_SECURITY_PAYLOAD_MAX_AGE_SECONDS", "3600")
    assert max_payload_age_seconds() == 3600
    monkeypatch.setenv("KLYROW_SECURITY_PAYLOAD_MAX_AGE_SECONDS", "86401")
    with pytest.raises(SecurityPayloadError):
        max_payload_age_seconds()
