"""Overview page — counters per state per queue."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from roost._core import repo
from starlette.requests import Request
from starlette.responses import Response

from roost_web.templating import templates

# State columns we always render so the table is stable even when no row exists.
_STATE_ORDER = ("available", "executing", "retryable", "completed", "discarded", "cancelled")


async def index(request: Request) -> Response:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await repo.status_counts_async(conn)
        workers = await repo.list_workers_async(conn)
        queue_rows = await repo.list_queues_async(conn)

    paused = {q for q, paused_at in queue_rows if paused_at is not None}
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(_STATE_ORDER, 0))
    for queue, state, count in rows:
        grouped[queue][state] = count

    queues = sorted(grouped.keys())
    totals = dict.fromkeys(_STATE_ORDER, 0)
    for state_counts in grouped.values():
        for state, n in state_counts.items():
            totals[state] += n

    context: dict[str, Any] = {
        "request": request,
        "title": request.app.state.title,
        "states": _STATE_ORDER,
        "queues": queues,
        "grouped": grouped,
        "totals": totals,
        "workers": workers,
        "paused": paused,
        "read_only": request.app.state.read_only,
    }
    return templates.TemplateResponse(request, "overview.html", context)
