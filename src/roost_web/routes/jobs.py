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
    tag_filter = request.query_params.get("tag", "").strip()

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
    if tag_filter:
        # GIN-indexed; ARRAY-contains via @> operator
        where.append(f"tags @> ARRAY[${len(args) + 1}]::text[]")
        args.append(tag_filter)

    # JSON-path containment: ?args_json={"user_id": 42} → args @> '{"user_id": 42}'
    args_json_filter = request.query_params.get("args_json", "").strip()
    if args_json_filter:
        try:
            import json

            json.loads(args_json_filter)  # syntax-check; reject anything else
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"args_json is not valid JSON: {exc}") from exc
        where.append(f"args @> ${len(args) + 1}::jsonb")
        args.append(args_json_filter)

    # Stuck filter: jobs in `available` that the worker can't fetch right now.
    stuck_filter = request.query_params.get("stuck", "").strip().lower() in {"1", "true", "yes"}
    if stuck_filter:
        where.append(
            "state = 'available' AND ("
            "scheduled_at > now() OR "
            "queue IN (SELECT name FROM roost.queues WHERE paused_at IS NOT NULL) OR "
            "EXISTS ("
            "  SELECT 1 FROM roost.jobs p "
            "   WHERE p.id = ANY(roost.jobs.depends_on) AND p.state <> 'completed'"
            "))"
        )

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
            "tag": tag_filter,
            "args_json": args_json_filter,
            "stuck": stuck_filter,
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
        explain = await repo.explain_job_async(conn, job_id)
    context: dict[str, Any] = {
        "request": request,
        "title": request.app.state.title,
        "job": dict(row),
        "explain": explain,
        "stuck_reasons": _stuck_reasons(dict(row), explain),
        "read_only": request.app.state.read_only,
    }
    return templates.TemplateResponse(request, "job_detail.html", context)


def _stuck_reasons(job: dict[str, Any], explain: dict[str, Any]) -> list[str]:
    """Plain-English reasons the job hasn't run yet. Empty if it's not stuck."""
    state = job.get("state")
    if state != "available":
        return []
    reasons: list[str] = []
    if explain.get("scheduled_in_future"):
        reasons.append(f"Scheduled in the future — scheduled_at is {job.get('scheduled_at')}.")
    if explain.get("queue_paused"):
        reasons.append(f"Queue {job.get('queue')!r} is paused. Resume it on the Queues page.")
    parents = explain.get("waiting_on_parents") or []
    if parents:
        reasons.append(
            "Waiting on parent job(s): "
            + ", ".join(f"#{p}" for p in parents)
            + " — child runs once every parent completes."
        )
    return reasons


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


async def bulk_action(request: Request) -> Response:
    """Apply ``retry`` or ``cancel`` to many job ids at once.

    Accepts a form body with repeated ``job_ids`` checkbox values + an
    ``action`` field. Errors on individual rows are tolerated — the
    response includes how many actually changed.
    """
    form = await request.form()
    action_raw = form.get("action") or ""
    if not isinstance(action_raw, str):
        raise HTTPException(status_code=400, detail="action must be a string")
    action = action_raw.strip()
    raw_ids = form.getlist("job_ids")
    try:
        job_ids = [int(x) for x in raw_ids if isinstance(x, str)]
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="job_ids must be integers") from exc
    if not job_ids:
        raise HTTPException(status_code=400, detail="no job_ids selected")
    if action not in {"retry", "cancel"}:
        raise HTTPException(status_code=400, detail="action must be retry or cancel")

    pool = request.app.state.pool
    changed = 0
    async with pool.acquire() as conn:
        for jid in job_ids:
            try:
                if action == "retry":
                    await repo.retry_job_async(conn, jid)
                else:
                    await repo.cancel_job_async(conn, jid)
                changed += 1
            except JobNotFoundError:
                continue

    if request.headers.get("HX-Request") == "true":
        return Response(
            status_code=204,
            headers={"HX-Refresh": "true", "X-Roost-Bulk-Changed": str(changed)},
        )
    return RedirectResponse(url=request.headers.get("referer") or ".", status_code=303)


def _post_action_response(request: Request, job_id: int) -> Response:
    """Either redirect (form post) or HX-trigger refresh (HTMX click)."""
    if request.headers.get("HX-Request") == "true":
        # Tell HTMX to reload the job detail block.
        return Response(
            status_code=204,
            headers={"HX-Refresh": "true"},
        )
    return RedirectResponse(url=f"./{job_id}", status_code=303)
