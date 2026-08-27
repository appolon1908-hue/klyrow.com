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
# clones anything onto the production application.
for route in list(tenancy_onboarding_router.routes):
    if getattr(route, "path", "") in SHELL_PATHS:
        tenancy_onboarding_router.routes.remove(route)

# Remove legacy/product shell routes that may already exist on the core app.
# `/admin` is intentionally replaced by the Vue admin shell below; the legacy
# main.py HTML endpoint otherwise wins first-match routing.
for route in list(app.router.routes):
    if getattr(route, "path", "") in SHELL_PATHS or (
        getattr(route, "path", "") == "/admin" and getattr(route, "name", "") == "admin_portal"
    ):
        app.router.routes.remove(route)

# Register browser APIs once. FastAPI 0.141 represents include_router() calls as
# nested _IncludedRouter entries, which hides their concrete paths from
# app.routes and breaks release-time route inventory checks. These routers have
# no prefixes or router-level dependencies, so registering their APIRoute
# objects directly preserves their metadata and runtime behavior while keeping
# the production route table inspectable.
if not getattr(app.state, "klyrow_browser_api_routes_registered", False):
    auth_bff._identity_context = resolve_identity_context_with_provisioning
    for browser_router in (
        auth_bff_router,
        tenancy_onboarding_router,
        browser_email_setup_router,
        postal_provisioning_router,
    ):
        app.router.routes.extend(browser_router.routes)
    app.state.klyrow_browser_api_routes_registered = True
else:
    auth_bff._identity_context = resolve_identity_context_with_provisioning

# The core app may have generated OpenAPI before browser composition. FastAPI
# caches that schema, so invalidate it whenever this composition module loads.
app.openapi_schema = None


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
