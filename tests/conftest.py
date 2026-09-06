from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_klyrow_public_origin(monkeypatch, request) -> None:
    """Prevent one test module's development origin from leaking suite-wide."""

    if request.module.__name__.endswith("test_browser_security_fixes"):
        monkeypatch.setenv(
            "KLYROW_PUBLIC_URL",
            "https://app.klyrow.test",
        )
    else:
        monkeypatch.delenv("KLYROW_PUBLIC_URL", raising=False)


@pytest.fixture(autouse=True)
def isolated_durable_result_keyring(tmp_path, monkeypatch):
    from apps.gateway.app.durable_keys import KEYRING_ENV, new_keyring_document
    path = tmp_path / "durable-result-keyring.json"
    path.write_text(new_keyring_document())
    path.chmod(0o600)
    monkeypatch.setenv(KEYRING_ENV, str(path))
    monkeypatch.setenv("KLYROW_DURABLE_RESULT_LEGACY_READ_ENABLED", "true")
    return path
