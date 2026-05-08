"""Workers heartbeat list."""

from __future__ import annotations

from typing import Any

from roost._core import repo
from starlette.requests import Request
from starlette.responses import Response

from roost_web.templating import templates


async def list_workers(request: Request) -> Response:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await repo.list_workers_async(conn)
    context: dict[str, Any] = {
        "request": request,
        "title": request.app.state.title,
        "rows": rows,
    }
    return templates.TemplateResponse(request, "workers.html", context)
