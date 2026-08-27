import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
EXPECTED = {
    "beyvra.com",
    "breero.com",
    "breero.shop",
    "codestra.agency",
    "codestra.cloud",
    "codestra.co",
    "codestra.digital",
    "codestra.media",
    "klyrow.com",
    "kyqra.com",
    "moneybee.loan",
    "moneybeeloan.com",
    "nativoenglish.com",
    "telnexa.co",
}


def test_sending_domain_inventory_is_exact_normalized_and_enabled():
    payload = json.loads(
        (
            ROOT / "config/runtime/klyrow-sending-domains.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["schema_version"] == "1.0"
    assert payload["required_state"] == "SENDING_ENABLED"
    rows = payload["domains"]
    names = [row["name"] for row in rows]
    assert len(rows) == 14
    assert set(names) == EXPECTED
    assert len(names) == len(set(names))
    assert names == sorted(names)
    assert all(
        row["verified"] is True and row["sending_enabled"] is True
        for row in rows
    )


def test_domain_inventory_verifier_targets_only_the_domain_claim_read_model():
    source = (
        ROOT / "scripts/ops/verify-klyrow-sending-domains"
    ).read_text(encoding="utf-8")
    assert "FROM domain_claims" in source
    assert "required_state" in source
    assert "unexpected_sending_enabled" in source
