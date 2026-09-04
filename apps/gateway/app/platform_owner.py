"""Browser integration for exact Klyrow platform-owner authorization."""

from __future__ import annotations

import time

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

from . import auth_bff
from .auth_bff import BrowserSession, SESSION_COOKIE, browser_context
from .main import DB, User, sha
from .platform_owner_policy import (
    PlatformOwnerConfig,
    PlatformOwnerError,
    validate_platform_owner_claims,
)
from .tenancy import OidcIdentity, TenantMember

router = APIRouter(tags=["Platform owner security"])
# Every browser API request made by a platform administrator is covered. The
# normal route dependency remains responsible for operation-specific roles and
# capabilities; this middleware adds the exact-owner identity requirement.
PLATFORM_OWNER_PATH_PREFIXES = ("/app/api/",)


def _stored_claims(item: BrowserSession) -> dict:
    if not item.id_token_ciphertext:
        raise PlatformOwnerError(403, "platform_owner_reauthentication_required")
    try:
        raw = auth_bff._decrypt(item.id_token_ciphertext)
        claims = jwt.decode(
            raw,
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": False,
            },
        )
    except Exception as exc:
        raise PlatformOwnerError(
            403, "platform_owner_reauthentication_required"
        ) from exc
    if not isinstance(claims, dict):
        raise PlatformOwnerError(403, "platform_owner_claims_invalid")
    return claims


def _platform_role_present(
    session: BrowserSession, user: User | None, member: TenantMember | None
) -> bool:
    roles = {
        str(session.role or "").lower(),
        str(user.role if user else "").lower(),
        str(member.role if member else "").lower(),
    }
    return "platform_admin" in roles


def _validate_session(s: Session, item: BrowserSession) -> None:
    user = s.get(User, item.user_id)
    member = s.scalar(
        select(TenantMember).where(
            TenantMember.tenant_id == item.tenant_id,
            TenantMember.user_id == item.user_id,
            TenantMember.active == True,
        )
    )
    if not _platform_role_present(item, user, member):
        return
    if not user or not user.enabled:
        raise PlatformOwnerError(403, "platform_owner_account_disabled")
    identity = s.get(OidcIdentity, item.identity_id)
    if not identity or not identity.enabled or identity.user_id != item.user_id:
        raise PlatformOwnerError(403, "platform_owner_identity_mismatch")
    try:
        canonical_issuer = auth_bff._canonical_issuer()
    except HTTPException as exc:
        raise PlatformOwnerError(
            503, "platform_owner_issuer_misconfigured"
        ) from exc
    config = PlatformOwnerConfig.from_env(canonical_issuer=canonical_issuer)
    validate_platform_owner_claims(
        config,
        identity_issuer=identity.issuer,
        identity_subject=identity.subject,
        claims=_stored_claims(item),
        now_epoch=int(time.time()),
    )


def _validate_raw_session(raw: str) -> None:
    """Perform synchronous owner lookup and validation in one worker thread."""

    with DB() as s:
        item = s.scalar(
            select(BrowserSession).where(BrowserSession.token_hash == sha(raw))
        )
        if item and item.revoked_at is None:
            _validate_session(s, item)


def install_platform_owner_guard(app) -> None:
    """Install inside existing instrumentation before the ASGI stack is built."""

    if getattr(app.state, "klyrow_platform_owner_guard_installed", False):
        return
    if app.middleware_stack is not None:
        raise RuntimeError(
            "platform owner guard must be installed before the ASGI stack is built"
        )

    async def platform_owner_guard(request: Request, call_next):
        if request.url.path.startswith(PLATFORM_OWNER_PATH_PREFIXES):
            raw = request.cookies.get(SESSION_COOKIE, "")
            if raw:
                try:
                    await run_in_threadpool(_validate_raw_session, raw)
                except PlatformOwnerError as exc:
                    return JSONResponse(
                        {"detail": exc.detail},
                        status_code=exc.status_code,
                        headers={"Cache-Control": "no-store"},
                    )
        return await call_next(request)

    # Starlette inserts decorator/add_middleware registrations at the front,
    # making the latest registration outermost. Appending this middleware keeps
    # the existing request-ID, security-header, metric, and latency middleware
    # outside the owner guard, so even early denials receive full instrumentation.
    app.user_middleware.append(
        Middleware(BaseHTTPMiddleware, dispatch=platform_owner_guard)
    )
    app.state.klyrow_platform_owner_guard_installed = True


@router.get("/auth/step-up", include_in_schema=False)
def platform_owner_step_up(
    return_to: str = "/admin",
    _ctx: dict = Depends(browser_context),
):
    """Remain fail closed until the pre-session flow is browser-bound.

    Issue #83 owns the secure host-only flow-cookie prerequisite. Starting a
    fresh authorization transaction before that prerequisite lands would leave
    the step-up state vulnerable to login-CSRF/session-swap attacks. The route
    remains outside generated clients until that prerequisite is protected.
    """

    del return_to, _ctx
    raise HTTPException(
        status_code=503,
        detail="platform_owner_step_up_flow_binding_required",
        headers={"Cache-Control": "no-store"},
    )
