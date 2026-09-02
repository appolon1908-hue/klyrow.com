from apps.gateway.app.delivery_safety import (
    live_email_delivery_enabled,
    safe_mode_enabled,
)


def set_controls(monkeypatch, *, safe_mode, approved, live_delivery):
    monkeypatch.setenv("KLYROW_SAFE_MODE", safe_mode)
    monkeypatch.setenv("KLYROW_PRODUCTION_GATE_APPROVED", approved)
    monkeypatch.setenv("LIVE_EMAIL_DELIVERY", live_delivery)


def test_safe_mode_blocks_delivery_even_with_other_controls_enabled(monkeypatch):
    set_controls(
        monkeypatch, safe_mode="true", approved="true", live_delivery="true"
    )
    assert safe_mode_enabled() is True
    assert live_email_delivery_enabled() is False


def test_disabled_delivery_flag_blocks_delivery(monkeypatch):
    set_controls(
        monkeypatch, safe_mode="false", approved="true", live_delivery="false"
    )
    assert safe_mode_enabled() is True
    assert live_email_delivery_enabled() is False


def test_gate_approval_alone_cannot_open_delivery(monkeypatch):
    set_controls(
        monkeypatch, safe_mode="true", approved="true", live_delivery="false"
    )
    assert safe_mode_enabled() is True
    assert live_email_delivery_enabled() is False


def test_delivery_requires_all_three_explicit_opt_ins(monkeypatch):
    set_controls(
        monkeypatch, safe_mode="false", approved="true", live_delivery="true"
    )
    assert safe_mode_enabled() is False
    assert live_email_delivery_enabled() is True
