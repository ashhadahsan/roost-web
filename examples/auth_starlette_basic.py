"""Mount the dashboard behind HTTP Basic auth using pure Starlette middleware.

Useful for one-developer ops setups where you want a quick guard without
hooking into a full auth framework.

Run::

    export ROOST_DSN=postgresql://...
    roost init --apply
    uvicorn examples.auth_starlette_basic:app --port 8000

Then visit http://localhost:8000/jobs/ — your browser will prompt for the
configured username/password (defaults: ``admin`` / ``please-change-me``).
"""

from __future__ import annotations

import base64
import os
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount

from roost_web import dashboard

DSN = os.environ["ROOST_DSN"]
USERNAME = os.environ.get("ROOST_ADMIN_USER", "admin")
PASSWORD = os.environ.get("ROOST_ADMIN_PASS", "please-change-me")


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests without the right Basic credentials."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        header = request.headers.get("authorization", "")
        if not header.startswith("Basic "):
            return _challenge()
        try:
            decoded = base64.b64decode(header[6:]).decode("utf-8")
            user, _, password = decoded.partition(":")
        except Exception:
            return _challenge()
        if user != USERNAME or password != PASSWORD:
            return _challenge()
        return await call_next(request)


def _challenge() -> Response:
    return Response(
        "auth required",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Roost"'},
    )


app = Starlette(
    routes=[Mount("/jobs", app=dashboard(dsn=DSN, title="Roost (auth'd)"))],
    middleware=[Middleware(BasicAuthMiddleware)],
)
