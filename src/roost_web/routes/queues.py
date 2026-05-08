"""Queue admin: list + pause + resume."""

from __future__ import annotations

from typing import Any

from roost._core import repo
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from roost_web.templating import templates


async def list_queues(request: Request) -> Response:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await repo.list_queues_async(conn)
        counts = await repo.status_counts_async(conn)

    by_queue: dict[str, dict[str, int]] = {}
    for queue, state, count in counts:
        by_queue.setdefault(queue, {})[state] = count

    queue_names = sorted({*by_queue.keys(), *(name for name, _ in rows)})
    paused = {name: paused_at for name, paused_at in rows if paused_at is not None}

    context: dict[str, Any] = {
        "request": request,
        "title": request.app.state.title,
        "queue_names": queue_names,
        "by_queue": by_queue,
        "paused": paused,
        "read_only": request.app.state.read_only,
    }
    return templates.TemplateResponse(request, "queues.html", context)


async def pause(request: Request) -> Response:
    name = (await _form(request)).get("queue", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="queue name required")
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        await repo.pause_queue_async(conn, name)
    return _action_response(request, "/queues")


async def resume(request: Request) -> Response:
    name = (await _form(request)).get("queue", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="queue name required")
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        await repo.resume_queue_async(conn, name)
    return _action_response(request, "/queues")


async def _form(request: Request) -> dict[str, str]:
    form = await request.form()
    return {k: str(v) for k, v in form.items()}


def _action_response(request: Request, location: str) -> Response:
    if request.headers.get("HX-Request") == "true":
        return Response(status_code=204, headers={"HX-Refresh": "true"})
    return RedirectResponse(url=location, status_code=303)
