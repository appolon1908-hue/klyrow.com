"""Production ASGI composition root for browser BFF plus existing Klyrow API."""
from .main import app
from .auth_bff import router as auth_bff_router

app.include_router(auth_bff_router)

__all__ = ["app"]
