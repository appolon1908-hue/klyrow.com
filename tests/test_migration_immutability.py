import hashlib
from pathlib import Path


def test_published_migration_008_is_immutable():
    path = Path("migrations/008_provider_saas_registry_separation.sql")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == "c00bccee64e727257a7802b056c09ea98d2ffb839204536a759b3400cb642e61"
