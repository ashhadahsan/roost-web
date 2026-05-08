"""Cron page — registered cron entries from ``roost.cron_runs``."""

from __future__ import annotations

from typing import Any

from roost._core import repo
from starlette.requests import Request
from starlette.responses import Response

from roost_web.templating import templates


async def list_cron(request: Request) -> Response:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await repo.list_cron_runs_async(conn)
    context: dict[str, Any] = {
        "request": request,
        "title": request.app.state.title,
        "rows": rows,
    }
    return templates.TemplateResponse(request, "cron.html", context)
