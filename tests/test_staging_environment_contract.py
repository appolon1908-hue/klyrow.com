import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "deploy" / "staging"


def test_staging_images_are_required_as_immutable_digests():
    script = (ROOT / "scripts" / "staging-preflight").read_text()
    assert "@sha256:" in script
    for image in ("GATEWAY", "WEB", "MIGRATE", "SEARCH", "CADDY", "POSTGRES", "PROMETHEUS", "GRAFANA"):
        assert f"KLYROW_{image}_IMAGE" in script


def test_only_caddy_publishes_public_ports():
    compose = yaml.safe_load((STAGING / "compose.yml").read_text())
    assert compose["services"]["edge"]["ports"] == ["80:80", "443:443"]
    for name, service in compose["services"].items():
        if name != "edge":
            assert "ports" not in service, name
    assert compose["networks"]["data"]["internal"] is True
    assert compose["networks"]["observability"]["internal"] is True
    caddy = (STAGING / "Caddyfile").read_text()
    assert "grafana:" not in caddy
    assert "prometheus:" not in caddy


def test_staging_is_fail_closed_for_external_delivery():
    compose = yaml.safe_load((STAGING / "compose.yml").read_text())
    env = compose["services"]["gateway"]["environment"]
    assert env["KLYROW_ENV"] == "staging"
    assert env["KLYROW_SAFE_MODE"] == "true"
    assert env["LIVE_EMAIL_DELIVERY"] == "false"
    assert env["EXTERNAL_EMAIL_DELIVERY"] == "false"
    assert env["PRODUCTION_PROVIDER_ROUTING"] == "false"


def test_keycloak_realm_requires_pkce_and_disables_password_grant():
    realm = json.loads((STAGING / "keycloak" / "kyyow-realm.json").read_text())
    client = next(item for item in realm["clients"] if item["clientId"] == "kyyow-portal")
    assert realm["realm"] == "kyyow"
    assert client["publicClient"] is True
    assert client["standardFlowEnabled"] is True
    assert client["directAccessGrantsEnabled"] is False
    assert client["attributes"]["pkce.code.challenge.method"] == "S256"


def test_openbao_policy_explicitly_denies_odoo_writer_secret():
    policy = (STAGING / "openbao" / "klyrow-staging.hcl").read_text()
    assert re.search(r'odoo-writer/\*"\s*\{\s*capabilities\s*=\s*\["deny"\]', policy, re.S)
