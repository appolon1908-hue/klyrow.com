from pathlib import Path

from apps.gateway.app import auth_bff


ROOT = Path(__file__).parents[1]


def _env_value(name: str) -> str:
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1]
    raise AssertionError(f"missing {name}")


def test_base_gateway_image_bundles_reviewed_vue_application():
    dockerfile = (ROOT / "apps/gateway/Dockerfile").read_text(encoding="utf-8")
    assert "FROM node:22-bookworm-slim AS web-build" in dockerfile
    assert "RUN pnpm build" in dockerfile
    assert "COPY --from=web-build /build/dist ./app/auth_web" in dockerfile
    assert '"app.platform:app"' in dockerfile


def test_example_uses_public_pkce_client_without_unmounted_secret(monkeypatch):
    assert _env_value("KLYROW_OIDC_CLIENT_SECRET_FILE") == ""
    monkeypatch.setenv("KLYROW_OIDC_CLIENT_SECRET_FILE", "")
    assert auth_bff._client_secret() is None
