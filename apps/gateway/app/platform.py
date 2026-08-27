"""Production ASGI composition root for browser BFF, onboarding and existing Klyrow API."""
from fastapi import HTTPException
from fastapi.responses import FileResponse

from .main import AUTH_WEB_DIST, app
from . import auth_bff
from .auth_bff import router as auth_bff_router
from .tenancy_onboarding import resolve_identity_context, router as tenancy_onboarding_router

auth_bff._identity_context = resolve_identity_context
app.include_router(auth_bff_router)
app.include_router(tenancy_onboarding_router)

@app.get("/admin", include_in_schema=False)
@app.get("/admin/{path:path}", include_in_schema=False)
def platform_admin_ui(path: str = ""):
    index = AUTH_WEB_DIST / "index.html"
    if not index.exists():
        raise HTTPException(503, "application_ui_not_built")
    return FileResponse(index, media_type="text/html", headers={"Cache-Control": "no-store"})

# Starlette routes are first-match. Keep the SPA fallback after the /app/api/* routes.
for route in list(app.router.routes):
    if getattr(route, "path", "") == "/app/{path:path}":
        app.router.routes.remove(route)
        app.router.routes.append(route)

__all__ = ["app"]
