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
