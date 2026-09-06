import os
from pathlib import Path

import pytest

from test_middleware_transport_migration import _migration_module


@pytest.fixture
def migration(tmp_path, monkeypatch):
    module = _migration_module()
    # Exercise the real script against only an isolated synthetic repository.
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(module, "__file__", str(tmp_path / "scripts/migrate-runtime-secrets"))
    monkeypatch.setenv("KLYROW_RUNTIME_SECRET_DIR", str(tmp_path / "secrets"))
    monkeypatch.setattr(module.os, "geteuid", lambda: 0)
    # Non-root CI cannot chown; assert requested ownership without changing it.
    ownership = []
    monkeypatch.setattr(module.os, "chown", lambda path, uid, gid: ownership.append((Path(path), uid, gid)))
    return module, tmp_path, ownership


@pytest.mark.parametrize("provided", [False, True])
def test_mautic_bootstrap_is_private_silent_and_idempotent(migration, capsys, provided):
    module, root, ownership = migration
    values = {"KLYROW_MAUTIC_API_CLIENT_ID": "synthetic-client-id",
              "KLYROW_MAUTIC_API_CLIENT_SECRET": "synthetic-client-secret"} if provided else {}
    env = root / ".env"
    env.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
    module.main()
    first = env.read_bytes()
    module.main()
    assert env.read_bytes() == first
    for name, basename in (("KLYROW_MAUTIC_API_CLIENT_ID", "mautic-api-client-id"),
                           ("KLYROW_MAUTIC_API_CLIENT_SECRET", "mautic-api-client-secret")):
        target = root / "secrets" / basename
        assert target.read_text() == values.get(name, "")
        assert target.stat().st_mode & 0o777 == 0o600
        assert f"{name}_FILE={target}" in env.read_text()
        assert f"{name}=" not in env.read_text()
        assert (target, 0, 0) in ownership
    assert env.stat().st_mode & 0o777 == 0o600
    output = capsys.readouterr()
    assert "synthetic-client" not in output.out + output.err


def test_existing_oauth_file_authority_is_preserved(migration):
    module, root, _ = migration
    target = root / "approved-client-secret"
    target.write_text("existing-synthetic-secret")
    env = root / ".env"
    env.write_text(f"KLYROW_MAUTIC_API_CLIENT_SECRET_FILE={target}\n")
    module.main()
    module.main()
    assert target.read_text() == "existing-synthetic-secret"
    assert f"KLYROW_MAUTIC_API_CLIENT_SECRET_FILE={target}" in env.read_text()
    assert not (root / "secrets/mautic-api-client-secret").exists()


@pytest.mark.parametrize("kind", ["missing", "symlink", "directory"])
def test_invalid_existing_secret_reference_fails_without_replacing_env(migration, kind):
    module, root, _ = migration
    target = root / "configured-secret"
    if kind == "directory":
        target.mkdir()
    elif kind == "symlink":
        original = root / "original"
        original.write_text("must-not-change")
        target.symlink_to(original)
    env = root / ".env"
    original_env = f"KLYROW_MAUTIC_API_CLIENT_SECRET_FILE={target}\n"
    env.write_text(original_env)
    with pytest.raises(SystemExit):
        module.main()
    assert env.read_text() == original_env
    if kind == "symlink":
        assert (root / "original").read_text() == "must-not-change"
