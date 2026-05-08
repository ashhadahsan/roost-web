"""Mount the Roost dashboard behind FastAPI auth.

Pattern: mount the dashboard at a protected path. FastAPI's middleware
runs *before* it forwards into the sub-app, so a 401/403 from auth
short-circuits before any dashboard route runs.

Run::

    pip install roost roost-web fastapi uvicorn 'python-jose[cryptography]'
    export ROOST_DSN=postgresql://...
    roost init --apply
    uvicorn examples.auth_fastapi:app --reload

Then:
* GET / → public landing
* GET /admin/jobs/ without a token → 401
* GET /admin/jobs/ with `Authorization: Bearer admin-token-xyz` → dashboard
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from roost_web import dashboard

DSN = os.environ["ROOST_DSN"]
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "admin-token-xyz")

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def landing() -> str:
    return "<h1>Public site</h1><p>Admin dashboard at <code>/admin/jobs/</code> (token required).</p>"


# ---------------------------------------------------------------------------
# Mount the dashboard behind a middleware that requires a bearer token.
# ---------------------------------------------------------------------------

dashboard_app = dashboard(dsn=DSN, read_only=False, title="Admin")


@app.middleware("http")
async def gate_admin(request: Request, call_next: Any) -> Any:
    """Reject unauthenticated requests under /admin/* before they reach the dashboard."""
    if not request.url.path.startswith("/admin/"):
        return await call_next(request)
    auth = request.headers.get("authorization", "")
    if auth != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or bad bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await call_next(request)


app.mount("/admin/jobs", dashboard_app)
