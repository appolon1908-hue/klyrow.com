from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_runtime_secret_bootstrap_never_prints_credentials():
    script = (ROOT / "scripts/generate-env").read_text()
    assert "secrets/runtime/session-secret" in script
    assert "secrets/runtime/metrics-token" in script
    assert "Initial admin password:" not in script
    assert "chmod 0600" in script


def test_schema_migration_is_a_required_gateway_dependency():
    compose = (ROOT / "docker-compose.yml").read_text()
    assert "gateway-migrate: {condition: service_completed_successfully}" in compose
    assert "2026082201_email_outbox_and_tenant_idempotency.sql" in compose
    assert "ON_ERROR_STOP=1" in compose


def test_outbox_recovers_abandoned_sending_leases():
    source = (ROOT / "apps/gateway/app/main.py").read_text()
    assert 'EmailOutbox.state=="sending"' in source
    assert "EmailOutbox.updated_at<stale" in source
    assert '"Idempotency-Key":"klyrow:"+snapshot[1]' in source


def test_prometheus_uses_the_private_metrics_credential():
    compose = (ROOT / "docker-compose.yml").read_text()
    prometheus = (ROOT / "config/prometheus.yml").read_text()
    assert "secrets: [klyrow_metrics_token]" in compose
    assert "credentials_file: /run/secrets/klyrow_metrics_token" in prometheus
