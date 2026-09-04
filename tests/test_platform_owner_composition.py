from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from apps.gateway.app import platform_owner
from apps.gateway.app.auth_bff import SESSION_COOKIE
from apps.gateway.app.platform_owner_policy import PlatformOwnerError


class _FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def scalar(self, _statement):
        return SimpleNamespace(revoked_at=None)


def _runtime_app(monkeypatch, validator):
    monkeypatch.setattr(platform_owner, "DB", lambda: _FakeSession())
    monkeypatch.setattr(platform_owner, "_validate_session", validator)

    app = FastAPI()
    app.state.instrumented_responses = []

    @app.middleware("http")
    async def instrumentation(request, call_next):
        response = await call_next(request)
        app.state.instrumented_responses.append(
            (request.url.path, response.status_code)
        )
        response.headers.update(
            {
                "X-Test-Instrumented": "true",
                "X-Request-Id": "test-request-id",
                "X-Content-Type-Options": "nosniff",
            }
        )
        return response

    platform_owner.install_platform_owner_guard(app)

    @app.post("/app/api/credits")
    def protected_operation():
        return {"handler": "ran"}

    @app.get("/health/live")
    def public_health():
        return {"status": "ok"}

    return app


def test_production_composition_installs_exact_owner_guard() -> None:
    source = Path("apps/gateway/app/platform.py").read_text(encoding="utf-8")
    assert "install_platform_owner_guard(app)" in source
    assert "platform_owner_router" in source


def test_guard_covers_every_browser_api_for_platform_admin_sessions() -> None:
    source = Path("apps/gateway/app/platform_owner.py").read_text(
        encoding="utf-8"
    )
    assert 'PLATFORM_OWNER_PATH_PREFIXES = ("/app/api/",)' in source
    assert "PlatformOwnerConfig.from_env" in source
    assert "validate_platform_owner_claims" in source


def test_unbound_step_up_redirect_is_hidden_and_fails_closed() -> None:
    source = Path("apps/gateway/app/platform_owner.py").read_text(
        encoding="utf-8"
    )
    assert '@router.get("/auth/step-up", include_in_schema=False)' in source
    assert "platform_owner_step_up_flow_binding_required" in source
    assert "_authorization_url(" not in source

    with pytest.raises(HTTPException) as denied:
        platform_owner.platform_owner_step_up(
            _ctx={"sub": "owner-candidate"}
        )

    assert denied.value.status_code == 503
    assert denied.value.detail == "platform_owner_step_up_flow_binding_required"
    assert denied.value.headers == {"Cache-Control": "no-store"}


def test_runtime_guard_blocks_before_a_browser_api_handler(monkeypatch) -> None:
    def deny(_session, _item):
        raise PlatformOwnerError(403, "platform_owner_identity_mismatch")

    app = _runtime_app(monkeypatch, deny)
    with TestClient(app) as client:
        response = client.post(
            "/app/api/credits",
            headers={"Cookie": f"{SESSION_COOKIE}=opaque-session"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "platform_owner_identity_mismatch"}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-test-instrumented"] == "true"
    assert response.headers["x-request-id"] == "test-request-id"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert app.state.instrumented_responses == [("/app/api/credits", 403)]


def test_runtime_guard_fails_closed_on_missing_owner_configuration(
    monkeypatch,
) -> None:
    def unavailable(_session, _item):
        raise PlatformOwnerError(503, "platform_owner_not_configured")

    app = _runtime_app(monkeypatch, unavailable)
    with TestClient(app) as client:
        response = client.post(
            "/app/api/credits",
            headers={"Cookie": f"{SESSION_COOKIE}=opaque-session"},
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "platform_owner_not_configured"}
    assert response.headers["x-test-instrumented"] == "true"
    assert app.state.instrumented_responses == [("/app/api/credits", 503)]


def test_owner_lookup_runs_through_threadpool(monkeypatch) -> None:
    offloaded = []

    async def fake_run_in_threadpool(function, *args):
        offloaded.append((function, args))
        return function(*args)

    monkeypatch.setattr(
        platform_owner,
        "run_in_threadpool",
        fake_run_in_threadpool,
    )
    app = _runtime_app(monkeypatch, lambda _session, _item: None)

    with TestClient(app) as client:
        response = client.post(
            "/app/api/credits",
            headers={"Cookie": f"{SESSION_COOKIE}=opaque-session"},
        )

    assert response.status_code == 200
    assert offloaded == [
        (platform_owner._validate_raw_session, ("opaque-session",))
    ]


def test_runtime_guard_allows_a_validated_owner_to_reach_handler(
    monkeypatch,
) -> None:
    app = _runtime_app(monkeypatch, lambda _session, _item: None)
    with TestClient(app) as client:
        response = client.post(
            "/app/api/credits",
            headers={"Cookie": f"{SESSION_COOKIE}=opaque-session"},
        )

    assert response.status_code == 200
    assert response.json() == {"handler": "ran"}
    assert response.headers["x-test-instrumented"] == "true"


def test_runtime_guard_does_not_wrap_non_browser_api_routes(
    monkeypatch,
) -> None:
    def must_not_run(_session, _item):
        raise AssertionError("owner guard ran outside /app/api/")

    app = _runtime_app(monkeypatch, must_not_run)
    with TestClient(app) as client:
        response = client.get(
            "/health/live",
            headers={"Cookie": f"{SESSION_COOKIE}=opaque-session"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-test-instrumented"] == "true"


def test_guard_refuses_late_installation_after_stack_build() -> None:
    app = FastAPI()

    @app.get("/")
    def root():
        return {"status": "ok"}

    with TestClient(app) as client:
        assert client.get("/").status_code == 200

    with pytest.raises(
        RuntimeError,
        match="before the ASGI stack is built",
    ):
        platform_owner.install_platform_owner_guard(app)
