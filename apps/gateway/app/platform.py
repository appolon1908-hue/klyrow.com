"""Production ASGI composition root for browser BFF, onboarding, provisioning and existing Klyrow API."""
from fastapi import HTTPException
from fastapi.responses import FileResponse

from .main import AUTH_WEB_DIST, app
from . import auth_bff
from .auth_bff import router as auth_bff_router
from .tenancy_onboarding import router as tenancy_onboarding_router
from .browser_email_setup import router as browser_email_setup_router
from .postal_provisioning import resolve_identity_context_with_provisioning, router as postal_provisioning_router

auth_bff._identity_context = resolve_identity_context_with_provisioning
app.include_router(auth_bff_router)
app.include_router(tenancy_onboarding_router)
app.include_router(browser_email_setup_router)
app.include_router(postal_provisioning_router)

@app.get("/admin", include_in_schema=False)
@app.get("/admin/{path:path}", include_in_schema=False)
def platform_admin_ui(path: str = ""):
    index = AUTH_WEB_DIST / "index.html"
    if not index.exists():
        raise HTTPException(503, "application_ui_not_built")
    return FileResponse(index, media_type="text/html", headers={"Cache-Control": "no-store"})

# Starlette routes are first-match. Keep SPA fallbacks after every /app/api/* route.
for route in list(app.router.routes):
    if getattr(route, "path", "") == "/app/{path:path}":
        app.router.routes.remove(route)
        app.router.routes.append(route)

__all__ = ["app"]
