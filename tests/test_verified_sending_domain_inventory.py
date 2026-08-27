import json
import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
INVENTORY = ROOT / "evidence/runtime/verified-sending-domains-20260827.json"
EXPECTED = [
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
]
DOMAIN = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)


def test_verified_sending_domain_inventory_is_complete_and_non_authorizing():
    data = json.loads(INVENTORY.read_text(encoding="utf-8"))
    assert data["status"] == "VERIFIED_SENDING_ENABLED"
    assert data["domain_count"] == 14
    assert data["domains"] == EXPECTED
    assert data["domains"] == sorted(set(data["domains"]))
    assert all(DOMAIN.fullmatch(domain) for domain in data["domains"])
    assert data["authorization_effect"] == "NONE"
    assert all(value is False for value in data["safety"].values())
