import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("alert_routing", ROOT / "scripts/render-alert-routing.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_private_route_preserves_scrapes_and_requires_mtls():
    source = yaml.safe_load((ROOT / "config/prometheus.yml").read_text())
    config = module.render(source, "10.20.30.40:9093", "aler.codestra.media", "production")
    assert config["scrape_configs"] == source["scrape_configs"]
    assert "alerting" not in source
    target = config["alerting"]["alertmanagers"][0]
    assert target["scheme"] == "https"
    assert target["tls_config"]["insecure_skip_verify"] is False
    assert target["tls_config"]["key_file"].startswith("/run/secrets/")
    assert config["global"]["external_labels"]["environment"] == "production"


@pytest.mark.parametrize("target", ["37.27.128.39:9093", "localhost:9093", "127.0.0.1:9093", "10.20.30.40:0", "http://10.20.30.40:9093", "10.20.30.40:65536"])
def test_public_or_invalid_targets_rejected(target):
    with pytest.raises(ValueError):
        module.render({}, target, "aler.codestra.media", "production")
