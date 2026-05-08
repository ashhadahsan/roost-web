"""JSON API v1 — for power users who want their own dashboard.

Stable contract for ``roost-web>=0.1``: any change here is a breaking
change and bumps the minor version (``v1`` → ``v2`` mounted alongside,
``v1`` deprecated for one release).

Auth is not in scope for this package — the host app is expected to
gate access via its own middleware.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from roost._core import repo
from roost.exceptions import JobNotFoundError
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

_STATES = ("available", "executing", "retryable", "completed", "discarded", "cancelled")


def api_routes() -> list[Route]:
    return [
        Route("/health", _health),
        Route("/status", _status),
        Route("/jobs", _list_jobs),
        Route("/jobs/{job_id:int}", _get_job),
        Route("/jobs/{job_id:int}/retry", _retry_job, methods=["POST"]),
        Route("/jobs/{job_id:int}/cancel", _cancel_job, methods=["POST"]),
        Route("/queues", _list_queues),
        Route("/queues/{name}/pause", _pause_queue, methods=["POST"]),
        Route("/queues/{name}/resume", _resume_queue, methods=["POST"]),
        Route("/workers", _list_workers),
    ]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _serialise(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        return {k: _serialise(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_serialise(v) for v in value]
    return value


def _json(payload: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(_serialise(payload), status_code=status_code)


# ---------------------------------------------------------------------------
# handlers
# ---------------------------------------------------------------------------


async def _health(_request: Request) -> Response:
    return _json({"ok": True})


async def _status(request: Request) -> Response:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await repo.status_counts_async(conn)
    return _json({"counts": [{"queue": q, "state": s, "count": n} for q, s, n in rows]})


async def _list_jobs(request: Request) -> Response:
    page = max(1, int(request.query_params.get("page", "1")))
    page_size = min(200, max(1, int(request.query_params.get("page_size", "50"))))
    state = request.query_params.get("state")
    queue = request.query_params.get("queue")
    task = request.query_params.get("task")

    where: list[str] = []
    args: list[Any] = []
    if state and state in _STATES:
        where.append(f"state = ${len(args) + 1}")
        args.append(state)
    if queue:
        where.append(f"queue = ${len(args) + 1}")
        args.append(queue)
    if task:
        where.append(f"task = ${len(args) + 1}")
        args.append(task)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    offset = (page - 1) * page_size

    sql_count = f"SELECT COUNT(*)::bigint FROM roost.jobs {clause}"
    sql_rows = (
        f"SELECT id, queue, task, state, priority, attempt, max_attempts, "
        f"       scheduled_at, attempted_at, completed_at, inserted_at, tags, "
        f"       unique_key, timeout_seconds, cancel_requested "
        f"  FROM roost.jobs {clause} "
        f" ORDER BY id DESC "
        f" LIMIT {page_size} OFFSET ${len(args) + 1}"
    )

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        total = int(await conn.fetchval(sql_count, *args))
        rows = [dict(r) for r in await conn.fetch(sql_rows, *args, offset)]

    return _json(
        {
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": rows,
        }
    )


async def _get_job(request: Request) -> Response:
    job_id = int(request.path_params["job_id"])
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM roost.jobs WHERE id = $1", job_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found")
    return _json(dict(row))


async def _retry_job(request: Request) -> Response:
    job_id = int(request.path_params["job_id"])
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        try:
            await repo.retry_job_async(conn, job_id)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _json({"ok": True, "id": job_id})


async def _cancel_job(request: Request) -> Response:
    job_id = int(request.path_params["job_id"])
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        try:
            await repo.cancel_job_async(conn, job_id)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _json({"ok": True, "id": job_id})


async def _list_queues(request: Request) -> Response:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await repo.list_queues_async(conn)
        counts = await repo.status_counts_async(conn)
    by_queue: dict[str, dict[str, int]] = {}
    for q, state, count in counts:
        by_queue.setdefault(q, {})[state] = count
    paused = {name: paused_at for name, paused_at in rows if paused_at is not None}
    return _json(
        {
            "items": [
                {
                    "name": name,
                    "paused_at": paused.get(name),
                    "counts": by_queue.get(name, {}),
                }
                for name in sorted({*by_queue.keys(), *(n for n, _ in rows)})
            ]
        }
    )


async def _pause_queue(request: Request) -> Response:
    name = request.path_params["name"]
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        await repo.pause_queue_async(conn, name)
    return _json({"ok": True, "queue": name, "paused": True})


async def _resume_queue(request: Request) -> Response:
    name = request.path_params["name"]
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        await repo.resume_queue_async(conn, name)
    return _json({"ok": True, "queue": name, "paused": False})


async def _list_workers(request: Request) -> Response:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await repo.list_workers_async(conn)
    return _json({"items": rows})
