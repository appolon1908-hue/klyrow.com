import hashlib
from pathlib import Path


def test_fresh_install_provider_smtp_contract_is_completed() -> None:
    migration = Path("migrations/010_complete_provider_smtp_contract.sql").read_text()
    for column in ("allowed_senders_json", "allowed_streams_json", "status"):
        assert f"ADD COLUMN IF NOT EXISTS {column}" in migration


def test_released_provider_registry_migration_remains_immutable() -> None:
    payload = Path("migrations/008_provider_saas_registry_separation.sql").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == (
        "c00bccee64e727257a7802b056c09ea98d2ffb839204536a759b3400cb642e61"
    )
    assert "RENAME COLUMN verifier_hash TO secret_hash" in payload.decode()
