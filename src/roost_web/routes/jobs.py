"""Jobs list, detail, retry, and cancel routes."""

from __future__ import annotations

from typing import Any

from roost._core import repo
from roost.exceptions import JobNotFoundError
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from roost_web.templating import templates

_STATES = ("available", "executing", "retryable", "completed", "discarded", "cancelled")
_PAGE_SIZE = 50


async def list_jobs(request: Request) -> Response:
    """Paginated, filterable jobs list."""
    pool = request.app.state.pool
    page = max(1, int(request.query_params.get("page", "1")))
    state_filter = request.query_params.get("state", "").strip()
    queue_filter = request.query_params.get("queue", "").strip()
    task_filter = request.query_params.get("task", "").strip()

    where: list[str] = []
    args: list[Any] = []
    if state_filter and state_filter in _STATES:
        where.append(f"state = ${len(args) + 1}")
        args.append(state_filter)
    if queue_filter:
        where.append(f"queue = ${len(args) + 1}")
        args.append(queue_filter)
    if task_filter:
        where.append(f"task = ${len(args) + 1}")
        args.append(task_filter)

    clause = ("WHERE " + " AND ".join(where)) if where else ""
    offset = (page - 1) * _PAGE_SIZE

    sql_count = f"SELECT COUNT(*)::bigint FROM roost.jobs {clause}"
    sql_rows = (
        f"SELECT id, queue, task, state, priority, attempt, max_attempts, scheduled_at, "
        f"       attempted_at, completed_at, inserted_at, tags, unique_key "
        f"  FROM roost.jobs {clause} "
        f" ORDER BY id DESC "
        f" LIMIT {_PAGE_SIZE} OFFSET ${len(args) + 1}"
    )
    args_with_offset = [*args, offset]

    async with pool.acquire() as conn:
        total = int(await conn.fetchval(sql_count, *args))
        rows = [dict(r) for r in await conn.fetch(sql_rows, *args_with_offset)]

    total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)

    template = "_jobs_table.html" if request.headers.get("HX-Request") == "true" else "jobs.html"
    context: dict[str, Any] = {
        "request": request,
        "title": request.app.state.title,
        "rows": rows,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "states": _STATES,
        "filters": {
            "state": state_filter,
            "queue": queue_filter,
            "task": task_filter,
        },
        "read_only": request.app.state.read_only,
    }
    return templates.TemplateResponse(request, template, context)


async def show_job(request: Request) -> Response:
    job_id = int(request.path_params["job_id"])
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM roost.jobs WHERE id = $1", job_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found")
    context: dict[str, Any] = {
        "request": request,
        "title": request.app.state.title,
        "job": dict(row),
        "read_only": request.app.state.read_only,
    }
    return templates.TemplateResponse(request, "job_detail.html", context)


async def retry_job(request: Request) -> Response:
    job_id = int(request.path_params["job_id"])
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        try:
            await repo.retry_job_async(conn, job_id)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _post_action_response(request, job_id)


async def cancel_job(request: Request) -> Response:
    job_id = int(request.path_params["job_id"])
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        try:
            await repo.cancel_job_async(conn, job_id)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _post_action_response(request, job_id)


def _post_action_response(request: Request, job_id: int) -> Response:
    """Either redirect (form post) or HX-trigger refresh (HTMX click)."""
    if request.headers.get("HX-Request") == "true":
        # Tell HTMX to reload the job detail block.
        return Response(
            status_code=204,
            headers={"HX-Refresh": "true"},
        )
    return RedirectResponse(url=f"./{job_id}", status_code=303)
