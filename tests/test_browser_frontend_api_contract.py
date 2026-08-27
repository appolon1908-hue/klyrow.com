from pathlib import Path

from fastapi.routing import APIRoute

from apps.gateway.app.platform import app


ROOT = Path(__file__).parents[1]


def _routes():
    rows = []
    for index, route in enumerate(app.router.routes):
        if isinstance(route, APIRoute):
            rows.append((index, route.path, set(route.methods or [])))
    return rows


def test_browser_api_contract_has_expected_methods():
    expected = {
        ("/auth/login", "GET"),
        ("/auth/signup", "GET"),
        ("/auth/google", "GET"),
        ("/auth/callback", "GET"),
        ("/auth/session", "GET"),
        ("/auth/refresh", "POST"),
        ("/auth/logout", "POST"),
        ("/auth/logout-all", "POST"),
        ("/auth/sessions", "GET"),
        ("/auth/sessions/{session_id}", "DELETE"),
        ("/app/api/context", "GET"),
        ("/app/api/dashboard", "GET"),
        ("/app/api/messages", "GET"),
        ("/app/api/email/send", "POST"),
        ("/app/api/onboarding", "GET"),
        ("/app/api/onboarding", "PATCH"),
        ("/app/api/onboarding/complete", "POST"),
        ("/app/api/organizations/{tenant_id}/switch", "POST"),
        ("/app/api/team", "GET"),
        ("/app/api/team/invitations", "POST"),
        ("/app/api/admin/dashboard", "GET"),
        ("/app/api/domains", "GET"),
        ("/app/api/domains", "POST"),
        ("/app/api/domains/{item_id}/verify", "POST"),
        ("/app/api/senders", "GET"),
        ("/app/api/senders", "POST"),
        ("/app/api/provisioning/postal", "GET"),
        ("/app/api/provisioning/postal", "POST"),
        ("/app/api/provisioning/postal/retry", "POST"),
        ("/app/api/admin/provisioning/postal", "GET"),
        ("/app/api/admin/provisioning/postal/{tenant_id}/retry", "POST"),
    }
    actual = {(path, method) for _, path, methods in _routes() for method in methods}
    assert expected <= actual


def test_spa_fallback_is_after_every_browser_api_route():
    rows = _routes()
    fallback = next(index for index, path, _ in rows if path == "/app/{path:path}")
    api_indexes = [index for index, path, _ in rows if path.startswith("/app/api/")]
    assert api_indexes
    assert all(index < fallback for index in api_indexes)


def test_frontend_only_calls_registered_browser_api_paths():
    source = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "apps/web/src/api.ts",
            "apps/web/src/Dashboard.vue",
            "apps/web/src/Onboarding.vue",
            "apps/web/src/AdminDashboard.vue",
            "apps/web/src/Provisioning.vue",
        )
    )
    required = {
        "/auth/session",
        "/auth/logout",
        "/app/api/dashboard",
        "/app/api/team",
        "/app/api/email/send",
        "/app/api/onboarding",
        "/app/api/onboarding/complete",
        "/app/api/admin/dashboard",
        "/app/api/provisioning/postal",
        "/app/api/provisioning/postal/retry",
        "/app/api/admin/provisioning/postal",
    }
    for path in required:
        assert path in source, path


def test_frontend_has_no_browser_token_storage_contract():
    source = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "apps/web/src/api.ts",
            "apps/web/src/Dashboard.vue",
            "apps/web/src/Onboarding.vue",
            "apps/web/src/AdminDashboard.vue",
            "apps/web/src/Provisioning.vue",
        )
    )
    forbidden = ("localStorage", "sessionStorage", "refresh_token", "access_token", "id_token")
    for marker in forbidden:
        assert marker not in source
