"""Private test-only authority for the separately collected adapter suite."""

import pytest


@pytest.fixture(autouse=True)
def isolated_durable_result_keyring(tmp_path, monkeypatch):
    # This suite is collected outside tests/, so that conftest is not inherited.
    from apps.gateway.app.durable_keys import KEYRING_ENV, new_keyring_document
    path = tmp_path / "adapter-durable-result-keyring.json"
    path.write_text(new_keyring_document())
    path.chmod(0o600)
    monkeypatch.setenv(KEYRING_ENV, str(path))
    monkeypatch.setenv("KLYROW_DURABLE_RESULT_LEGACY_READ_ENABLED", "true")
    return path
