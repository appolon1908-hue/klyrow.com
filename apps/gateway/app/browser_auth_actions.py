"""Safe browser account actions and stable per-session CSRF authority."""
from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import timezone
from typing import Optional
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import auth_bff
from .auth_bff import BrowserSession, OidcLoginTransaction
from .main import SECRET, User, auth_rate, db, sha
from .tenancy import OidcIdentity, TenantInvitation

router = APIRouter(tags=["Browser account actions"])
_ORIGINAL_NEW_SESSION = auth_bff._new_session
_ORIGINAL_GET_BROWSER_SESSION = auth_bff._get_browser_session
_INSTALLED = False
_ACTION_MODES = {"update-password", "verify-email"}


class RecoveryRequest(BaseModel):
    email: EmailStr


class InvitationValidationRequest(BaseModel):
    token: str = Field(min_length=16, max_length=512)


def stable_csrf_token(session_id: str) -> str:
    """Derive one unguessable CSRF token for the lifetime of a browser session."""

    digest = hmac.new(
        SECRET.encode(),
        ("klyrow-browser-csrf-v1:" + session_id).encode(),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _active_principal(
    session: Session, item: BrowserSession
) -> tuple[OidcIdentity, User]:
    """Fail closed and revoke the session when either local principal is disabled."""

    identity = session.get(OidcIdentity, item.identity_id)
    user = session.get(User, item.user_id)
    if identity is not None:
        session.refresh(identity)
    if user is not None:
        session.refresh(user)
    if (
        identity is None
        or not identity.enabled
        or user is None
        or not user.enabled
    ):
        item.revoked_at = auth_bff.now()
        session.commit()
        raise HTTPException(401, "principal_disabled")
    return identity, user


def _get_browser_session_with_principal_validation(
    request: Request, session: Session, touch: bool = True
) -> BrowserSession:
    item = _ORIGINAL_GET_BROWSER_SESSION(request, session, touch=touch)
    _active_principal(session, item)
    return item


def _new_session_with_stable_csrf(*args, **kwargs):
    session: Session = args[0] if args else kwargs["s"]
    identity = args[2] if len(args) > 2 else kwargs["identity"]
    user = args[3] if len(args) > 3 else kwargs["user"]

    # Re-read both records immediately before issuing or rotating a browser
    # session. This closes the refresh race where an administrator disables a
    # principal while Keycloak is completing a token exchange.
    identity_item = session.get(OidcIdentity, identity.id)
    user_item = session.get(User, user.id)
    if identity_item is not None:
        session.refresh(identity_item)
    if user_item is not None:
        session.refresh(user_item)
    if (
        identity_item is None
        or not identity_item.enabled
        or user_item is None
        or not user_item.enabled
    ):
        raise HTTPException(401, "principal_disabled")

    item, raw, _csrf = _ORIGINAL_NEW_SESSION(*args, **kwargs)
    csrf = stable_csrf_token(item.id)
    item.csrf_hash = sha(csrf)
    session.commit()
    return item, raw, csrf


def _identity_action_url(
    request: Request,
    session: Session,
    *,
    mode: str,
    return_to: str,
    action: Optional[str] = None,
    forgot_credentials: bool = False,
) -> str:
    url = auth_bff._authorization_url(request, session, mode, return_to)
    parsed = urlsplit(url)
    path = parsed.path
    if forgot_credentials:
        # Keycloak's supported client-initiated Reset Credentials flow replaces
        # only the terminal OIDC `/auth` segment with `/forgot-credentials`.
        suffix = "/protocol/openid-connect/auth"
        if not path.endswith(suffix):
            raise HTTPException(503, "canonical_oidc_misconfigured")
        path = path[: -len(suffix)] + "/protocol/openid-connect/forgot-credentials"
    query = parse_qsl(parsed.query, keep_blank_values=True)
    if action:
        query.append(("kc_action", action))
    return urlunsplit((parsed.scheme, parsed.netloc, path, urlencode(query), ""))


def install_auth_extensions() -> None:
    """Replace historical routes and session helpers exactly once."""

    global _INSTALLED
    if _INSTALLED:
        return
    for route in list(auth_bff.router.routes):
        if getattr(route, "path", "") in {"/auth/session", "/auth/callback"}:
            auth_bff.router.routes.remove(route)
    auth_bff._get_browser_session = _get_browser_session_with_principal_validation
    auth_bff._new_session = _new_session_with_stable_csrf
    _INSTALLED = True


@router.get("/auth/callback")
def oidc_callback(
    request: Request,
    state: str,
    code: Optional[str] = None,
    kc_action_status: Optional[str] = None,
    error: Optional[str] = None,
    session: Session = Depends(db),
):
    transaction = session.scalar(
        select(OidcLoginTransaction).where(
            OidcLoginTransaction.state_hash == sha(state)
        )
    )
    if not transaction or transaction.used_at:
        raise HTTPException(410, "oidc_state_invalid_or_used")
    expiry = transaction.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= auth_bff.now():
        raise HTTPException(410, "oidc_state_expired")
    transaction.used_at = auth_bff.now()
    session.commit()

    # Never turn a cancelled/omitted application-initiated action into a success
    # page. Keycloak documents kc_action_status as the completion signal.
    if error or not code or (
        transaction.mode in _ACTION_MODES and kc_action_status != "success"
    ):
        return RedirectResponse(
            "/service-error", status_code=303, headers={"Cache-Control": "no-store"}
        )

    verifier = auth_bff._decrypt(transaction.verifier_ciphertext)
    nonce = auth_bff._decrypt(transaction.nonce_ciphertext)
    tokens = auth_bff._exchange_code(code, verifier, request)
    claims = auth_bff._validate_id_token(tokens["id_token"], nonce)
    if transaction.mode.startswith("invite:"):
        from .invitation_flow import resolve_selected_identity_context
        from .postal_provisioning import enqueue_postal_provisioning

        invitation_id = transaction.mode.split(":", 1)[1]
        identity, user, membership = resolve_selected_identity_context(
            session, claims, invitation_id
        )
        enqueue_postal_provisioning(session, membership.tenant_id)
    else:
        identity, user, membership = auth_bff._identity_context(session, claims)
    item, raw, _csrf = auth_bff._new_session(
        session, request, identity, user, membership, tokens
    )
    response = RedirectResponse(
        auth_bff._safe_return_to(transaction.return_url), status_code=303
    )
    auth_bff._set_session_cookie(response, raw)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Klyrow-Session-Id"] = item.id
    return response


@router.get("/auth/session")
def session_status(request: Request, session: Session = Depends(db)):
    try:
        item = auth_bff._get_browser_session(request, session)
    except HTTPException as exc:
        if exc.status_code == 401:
            return JSONResponse(
                {"authenticated": False},
                status_code=200,
                headers={"Cache-Control": "no-store"},
            )
        raise
    csrf = stable_csrf_token(item.id)
    expected_hash = sha(csrf)
    if not hmac.compare_digest(item.csrf_hash, expected_hash):
        item.csrf_hash = expected_hash
        session.commit()
    return JSONResponse(
        auth_bff._session_body(session, item, csrf),
        headers={"Cache-Control": "no-store"},
    )


@router.post("/auth/actions/recover", status_code=202)
def begin_recovery(
    payload: RecoveryRequest,
    request: Request,
    session: Session = Depends(db),
):
    # Validate shape, but never look up the address. Keycloak owns account
    # discovery and emits the same response whether an account exists or not.
    del payload
    auth_rate(request, "browser-recovery")
    return {
        "status": "accepted",
        "redirect_to": _identity_action_url(
            request,
            session,
            mode="recover",
            return_to="/reset-success",
            forgot_credentials=True,
        ),
    }


@router.post("/auth/actions/update-password", status_code=202)
def begin_password_update(request: Request, session: Session = Depends(db)):
    auth_rate(request, "browser-password-update")
    return {
        "status": "accepted",
        "redirect_to": _identity_action_url(
            request,
            session,
            mode="update-password",
            return_to="/reset-success",
            action="UPDATE_PASSWORD",
        ),
    }


@router.post("/auth/actions/verify-email", status_code=202)
def begin_email_verification(request: Request, session: Session = Depends(db)):
    auth_rate(request, "browser-email-verification")
    return {
        "status": "accepted",
        "redirect_to": _identity_action_url(
            request,
            session,
            mode="verify-email",
            return_to="/verification-success",
            action="VERIFY_EMAIL",
        ),
    }


@router.post("/auth/actions/invitation")
def validate_invitation(
    payload: InvitationValidationRequest,
    request: Request,
    session: Session = Depends(db),
):
    auth_rate(request, "browser-invitation")
    item = session.scalar(
        select(TenantInvitation).where(TenantInvitation.token_hash == sha(payload.token))
    )
    valid = False
    if item and not item.revoked_at and not item.accepted_at:
        expiry = item.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        valid = expiry > auth_bff.now()
    if not valid:
        return {"valid": False, "redirect_to": None}

    redirect_to = auth_bff._authorization_url(
        request, session, "signup", "/onboarding"
    )
    state_values = parse_qs(urlsplit(redirect_to).query).get("state", [])
    if len(state_values) != 1:
        raise HTTPException(503, "oidc_invitation_state_unavailable")
    transaction = session.scalar(
        select(OidcLoginTransaction).where(
            OidcLoginTransaction.state_hash == sha(state_values[0])
        )
    )
    if transaction is None:
        raise HTTPException(503, "oidc_invitation_state_unavailable")
    transaction.mode = "invite:" + item.id
    session.commit()
    return {"valid": True, "redirect_to": redirect_to}
