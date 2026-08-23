from pathlib import Path


def test_fresh_install_provider_smtp_contract_is_completed() -> None:
    migration = Path("migrations/008_provider_saas_registry_separation.sql").read_text()
    for column in ("allowed_senders_json", "allowed_streams_json", "status"):
        assert f"ADD COLUMN IF NOT EXISTS {column}" in migration
    assert "RENAME COLUMN verifier_hash TO secret_hash" in migration
