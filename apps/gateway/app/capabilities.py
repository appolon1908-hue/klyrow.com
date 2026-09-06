"""Shared capability checks after authentication establishes tenant authority."""
from typing import Any

from fastapi import HTTPException


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
