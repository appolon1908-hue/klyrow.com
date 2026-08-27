"""Production ASGI composition root for Klyrow browser and API surfaces.

The browser SPA shell is composed here, never inside an API router. Starlette
uses first-match routing, so catch-all shell routes must be registered last.
"""
from fastapi import HTTPException
from fastapi.responses import FileResponse

from .main import AUTH_WEB_DIST, app
from . import auth_bff
from .auth_bff import router as auth_bff_router
from .tenancy_onboarding import router as tenancy_onboarding_router
from .browser_email_setup import router as browser_email_setup_router
from .postal_provisioning import resolve_identity_context_with_provisioning, router as postal_provisioning_router

SHELL_PATHS = {"/app", "/onboarding", "/app/{path:path}"}

# The historical onboarding router contains SPA shell routes before its API
# routes. Strip those routes from the source router *before* include_router()
# clones anything onto the production application. This is intentionally done
# at composition time so older stacked branches remain compatible.
for route in list(tenancy_onboarding_router.routes):
    if getattr(route, "path", "") in SHELL_PATHS:
        tenancy_onboarding_router.routes.remove(route)

# Also remove any shell routes that may have been registered by a previous
# composition/import. This makes composition idempotent under test reloads.
for route in list(app.router.routes):
    if getattr(route, "path", "") in SHELL_PATHS:
        app.router.routes.remove(route)

# Register browser APIs once. Re-importing this module must not duplicate route
# handlers or change first-match ordering.
if not getattr(app.state, "klyrow_browser_api_routes_registered", False):
    auth_bff._identity_context = resolve_identity_context_with_provisioning
    app.include_router(auth_bff_router)
    app.include_router(tenancy_onboarding_router)
    app.include_router(browser_email_setup_router)
    app.include_router(postal_provisioning_router)
    app.state.klyrow_browser_api_routes_registered = True
else:
    auth_bff._identity_context = resolve_identity_context_with_provisioning


def _ui_index():
    index = AUTH_WEB_DIST / "index.html"
    if not index.exists():
        raise HTTPException(503, "application_ui_not_built")
    return FileResponse(index, media_type="text/html", headers={"Cache-Control": "no-store"})


# Remove platform-owned shell routes too if this module is explicitly reloaded.
for route in list(app.router.routes):
    if getattr(route, "name", "") in {"platform_admin_ui", "product_app_ui"}:
        app.router.routes.remove(route)


@app.get("/admin", include_in_schema=False)
@app.get("/admin/{path:path}", include_in_schema=False)
def platform_admin_ui(path: str = ""):
    return _ui_index()


# Deliberately last: no /app/api/* route can ever be consumed by this catch-all.
@app.get("/app", include_in_schema=False)
@app.get("/onboarding", include_in_schema=False)
@app.get("/app/{path:path}", include_in_schema=False)
def product_app_ui(path: str = ""):
    return _ui_index()


__all__ = ["app"]
