"""Starlette app factory.

Use ``create_app(dsn=...)`` (re-exported as :func:`roost_web.dashboard`)
to mount the dashboard inside any ASGI host::

    from fastapi import FastAPI
    from roost_web import dashboard

    app = FastAPI()
    app.mount("/jobs", dashboard(dsn="postgresql://..."))
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from roost_web.api.v1 import api_routes
from roost_web.db import close_pool, open_pool
from roost_web.routes import cron as cron_routes
from roost_web.routes import jobs as jobs_routes
from roost_web.routes import overview as overview_routes
from roost_web.routes import queues as queues_routes
from roost_web.routes import sse as sse_routes
from roost_web.routes import workers as workers_routes

_STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(
    dsn: str,
    *,
    read_only: bool = False,
    pool_size: int = 5,
    title: str = "Roost",
) -> Starlette:
    """Build a Starlette app for the dashboard.

    :param dsn: Postgres DSN — same database your Roost workers use.
    :param read_only: When True, mutating actions (retry / cancel /
        pause) return ``403`` so the dashboard is safe to expose in
        staging or to read-only operators.
    :param pool_size: Max connections in the dashboard's own pool.
    :param title: Banner shown in the navbar — useful for distinguishing
        environments in screenshots.
    """

    @asynccontextmanager
    async def lifespan(starlette_app: Starlette) -> AsyncIterator[None]:
        await open_pool(starlette_app)
        try:
            yield
        finally:
            await close_pool(starlette_app)

    routes = [
        Route("/", overview_routes.index, name="overview"),
        Route("/jobs", jobs_routes.list_jobs, name="jobs.list"),
        Route("/jobs/bulk", jobs_routes.bulk_action, methods=["POST"], name="jobs.bulk"),
        Route("/jobs/{job_id:int}", jobs_routes.show_job, name="jobs.show"),
        Route("/jobs/{job_id:int}/retry", jobs_routes.retry_job, methods=["POST"], name="jobs.retry"),
        Route(
            "/jobs/{job_id:int}/cancel",
            jobs_routes.cancel_job,
            methods=["POST"],
            name="jobs.cancel",
        ),
        Route("/queues", queues_routes.list_queues, name="queues.list"),
        Route("/queues/pause", queues_routes.pause, methods=["POST"], name="queues.pause"),
        Route("/queues/resume", queues_routes.resume, methods=["POST"], name="queues.resume"),
        Route("/workers", workers_routes.list_workers, name="workers.list"),
        Route("/workers/{worker_id:path}", workers_routes.show_worker, name="workers.show"),
        Route("/cron", cron_routes.list_cron, name="cron.list"),
        Route("/events/jobs", sse_routes.stream_jobs, name="events.jobs"),
        Mount("/api/v1", routes=api_routes(), name="api"),
        Mount("/static", app=StaticFiles(directory=str(_STATIC_DIR)), name="static"),
    ]

    app = Starlette(routes=routes, lifespan=lifespan)
    app.state.dsn = dsn
    app.state.pool_size = pool_size
    app.state.read_only = read_only
    app.state.title = title

    app.add_middleware(_ReadOnlyEnforcer)
    return app


class _ReadOnlyEnforcer:
    """Reject mutating routes when ``state.read_only`` is set.

    Cheap content-negotiated 403: HTML clients get an error page,
    JSON clients get a JSON body.
    """

    _MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive)
        starlette_app: Starlette = scope["app"]
        if getattr(starlette_app.state, "read_only", False) and request.method in self._MUTATING_METHODS:
            from starlette.responses import JSONResponse, PlainTextResponse

            wants_json = "application/json" in request.headers.get("accept", "")
            response = (
                JSONResponse({"error": "dashboard is read-only"}, status_code=403)
                if wants_json
                else PlainTextResponse("dashboard is read-only", status_code=403)
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


__all__ = ["create_app"]
