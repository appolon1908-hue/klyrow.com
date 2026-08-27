from pathlib import Path

from apps.gateway.app import service_worker


ROOT = Path(__file__).parents[1]


def test_released_global_postal_delivery_is_the_default(monkeypatch):
    monkeypatch.delenv("KLYROW_TENANT_POSTAL_PROVISIONING_ENABLED", raising=False)
    assert service_worker.tenant_postal_delivery_enabled() is False
    assert service_worker.selected_mail_delivery_loop() is service_worker.email_outbox_loop


def test_tenant_postal_delivery_requires_explicit_complete_stack(monkeypatch):
    monkeypatch.setenv("KLYROW_TENANT_POSTAL_PROVISIONING_ENABLED", "true")
    assert service_worker.tenant_postal_delivery_enabled() is True
    assert (
        service_worker.selected_mail_delivery_loop()
        is service_worker.tenant_email_outbox_loop
    )


def test_postal_provisioning_overlay_enables_tenant_delivery_explicitly():
    overlay = (
        ROOT / "docker-compose.postal-provisioning.yml"
    ).read_text(encoding="utf-8")
    assert overlay.count('KLYROW_TENANT_POSTAL_PROVISIONING_ENABLED: "true"') >= 2
    assert "KLYROW_PROVIDER_CREDENTIAL_KEY_FILE" in overlay
    assert "provisioning-worker:" in overlay
    assert "postal-provisioner:" in overlay
