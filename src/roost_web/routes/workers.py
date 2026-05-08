"""Workers heartbeat list + per-worker detail page."""

from __future__ import annotations

from typing import Any

from roost._core import repo
from starlette.exceptions import HTTPException
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


async def show_worker(request: Request) -> Response:
    worker_id = request.path_params["worker_id"]
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # Look up the heartbeat row for this id, then fetch its job history.
        meta = await conn.fetchrow(
            "SELECT id, hostname, pid, queues, started_at, last_seen_at, metadata "
            "  FROM roost.workers WHERE id = $1",
            worker_id,
        )
        if meta is None:
            raise HTTPException(status_code=404, detail=f"worker {worker_id!r} not heartbeating")
        recent = await repo.list_jobs_for_worker_async(conn, worker_id, limit=50)
    context: dict[str, Any] = {
        "request": request,
        "title": request.app.state.title,
        "worker": dict(meta),
        "recent": recent,
    }
    return templates.TemplateResponse(request, "worker_detail.html", context)
