import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
CANONICAL = "https://middleware-email-events.internal.codestra.agency:18080"
OVERLAY = "deploy/docker-compose.middleware-mtls.yml"


def _migration_module():
    path = ROOT / "scripts/migrate-runtime-secrets"
    loader = SourceFileLoader("migrate_runtime_secrets", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_runtime_migration_upgrades_only_known_plaintext_authority():
    migration = _migration_module()
    assert migration.reconcile_middleware_url("") == CANONICAL
    assert migration.reconcile_middleware_url(CANONICAL + "/") == CANONICAL
    assert migration.reconcile_middleware_url("http://10.40.0.1:8095") == CANONICAL
    assert migration.reconcile_middleware_url("http://10.40.0.1:18080/") == CANONICAL
    assert migration.reconcile_middleware_url("https://middleware-staging.internal:18080/") == (
        "https://middleware-staging.internal:18080"
    )
    with pytest.raises(SystemExit):
        migration.reconcile_middleware_url("http://unexpected.internal:18080")
    with pytest.raises(SystemExit):
        migration.reconcile_middleware_url("file:///run/secrets/middleware")
    with pytest.raises(SystemExit):
        migration.reconcile_middleware_url("https://user:secret@middleware.internal")


def test_first_upgrade_runs_the_new_migration_after_pull():
    update = (ROOT / "scripts/update").read_text(encoding="utf-8")
    marker = "scripts/migrate-runtime-secrets"
    assert update.count(marker) == 2
    first = update.index(marker)
    pull = update.index("git pull --ff-only")
    second = update.rindex(marker)
    compose = update.index("COMPOSE=(")
    assert first < pull < second < compose


def test_deploy_and_update_always_apply_the_mtls_overlay():
    for script_name in ("deploy", "update"):
        source = (ROOT / f"scripts/{script_name}").read_text(encoding="utf-8")
        assert f"-f {OVERLAY}" in source
        assert source.index("-f docker-compose.yml") < source.index(f"-f {OVERLAY}")

    overlay = (ROOT / OVERLAY).read_text(encoding="utf-8")
    assert overlay.count(f"KLYROW_MIDDLEWARE_URL: {CANONICAL}") == 2
    assert overlay.count(
        f"KLYROW_EMAIL_EVENT_URL: {CANONICAL}/internal/provider-events/klyrow"
    ) == 2
    assert overlay.count(
        '"middleware-email-events.internal.codestra.agency:10.40.0.1"'
    ) == 2


def test_documented_outbound_transport_is_mtls_only():
    docs = (ROOT / "docs/MIDDLEWARE_INTEGRATION.md").read_text(encoding="utf-8")
    assert CANONICAL in docs
    assert "historical plaintext `:8095` endpoint is rejected" in docs
    assert "Delivery to middleware `:8095`" not in docs
