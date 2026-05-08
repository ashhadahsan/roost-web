"""Postgres pool lifecycle for the dashboard.

The dashboard owns its own pool — separate from the host app's pool — so
the failure mode is local. ``init=`` on the pool registers the JSONB codec
that ``roost`` depends on for ``args`` / ``errors`` columns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from roost._core.repo import init_connection

if TYPE_CHECKING:  # pragma: no cover
    from starlette.applications import Starlette


async def open_pool(app: Starlette) -> None:
    import asyncpg

    dsn = app.state.dsn
    app.state.pool = await asyncpg.create_pool(
        dsn,
        min_size=1,
        max_size=app.state.pool_size,
        init=init_connection,
    )


async def close_pool(app: Starlette) -> None:
    pool = getattr(app.state, "pool", None)
    if pool is not None:
        await pool.close()


__all__ = ["close_pool", "open_pool"]
