"""Fail-closed production email delivery contract."""

import os


def live_email_delivery_enabled() -> bool:
    """Require every independent delivery control to opt in explicitly."""

    return (
        os.getenv("KLYROW_SAFE_MODE", "true").strip().lower() == "false"
        and os.getenv("KLYROW_PRODUCTION_GATE_APPROVED", "false").strip().lower()
        == "true"
        and os.getenv("LIVE_EMAIL_DELIVERY", "false").strip().lower() == "true"
    )


def safe_mode_enabled() -> bool:
    return not live_email_delivery_enabled()
