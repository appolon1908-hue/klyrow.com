"""Shared capability checks after authentication establishes tenant authority."""
from typing import Any

from fastapi import HTTPException


def mutation_permission(method: str, path: str) -> str | None:
    """Request the same exact capability from the external tenant resolver."""
    if method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    for prefix, permission in (
        ("/v1/internal/email/domains", "domain.manage"),
        ("/v1/internal/email/senders", "sender.manage"),
        ("/v1/internal/email/smtp/credentials", "credential.manage"),
        ("/v1/domains", "domain.manage"),
        ("/v1/senders", "sender.manage"),
        ("/v1/templates", "template.manage"),
        ("/v1/contacts", "contact.manage"),
        ("/v1/lists", "contact.manage"),
        ("/v1/suppressions", "contact.manage"),
        ("/v1/campaigns", "campaign.manage"),
        ("/v1/campaign-definitions", "campaign.manage"),
    ):
        if path == prefix or path.startswith(prefix + "/"):
            return permission
    return None


def has_permission(ctx: dict[str, Any], permission: str) -> bool:
    # Import lazily: tenancy models depend on the composed gateway's Base.
    from .tenancy import ROLE_PERMISSIONS

    role = str(ctx.get("role") or "").upper()
    if role in {"OWNER", "ADMIN", "PLATFORM_ADMIN", "TENANT_ADMIN"}:
        return True
    granted = set(ROLE_PERMISSIONS.get(role, set()))
    for field in ("permissions", "scopes"):
        values = ctx.get(field) or []
        granted.update(values.split() if isinstance(values, str) else values)
    return "*" in granted or permission in granted


def require_permission(ctx: dict[str, Any], permission: str) -> None:
    if not has_permission(ctx, permission):
        raise HTTPException(403, "permission_denied")
