"""Server-Sent Events bridge from ``LISTEN/NOTIFY`` to the browser.

Each connected client gets a dedicated asyncpg connection that listens on
``roost_inserted`` and ``roost_updated`` and pushes ``data: {...}`` frames
through the open HTTP connection. HTMX picks them up via ``hx-sse``.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import TYPE_CHECKING, Any

from roost._core.notify import CHANNEL_INSERTED, CHANNEL_UPDATED
from roost._core.repo import init_connection
from starlette.requests import Request
from starlette.responses import StreamingResponse

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import AsyncIterator

_HEARTBEAT_INTERVAL = 15.0


async def stream_jobs(request: Request) -> StreamingResponse:
    dsn = request.app.state.dsn
    return StreamingResponse(
        _event_stream(request, dsn),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx — disable proxy buffering
            "Connection": "keep-alive",
        },
    )


async def _event_stream(request: Request, dsn: str) -> AsyncIterator[bytes]:
    import asyncpg

    queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=1024)
    loop = asyncio.get_running_loop()

    def _enqueue(payload: bytes) -> None:
        # add_listener callbacks fire in asyncpg's protocol thread context;
        # use call_soon_threadsafe to hop back to the loop.
        loop.call_soon_threadsafe(_safe_put, payload)

    def _safe_put(payload: bytes) -> None:
        # Slow client → drop the frame rather than blocking the listener.
        with contextlib.suppress(asyncio.QueueFull):
            queue.put_nowait(payload)

    def _on_inserted(_conn: object, _pid: int, _channel: str, payload: str) -> None:
        _enqueue(_format_event("inserted", {"queue": payload}))

    def _on_updated(_conn: object, _pid: int, _channel: str, payload: str) -> None:
        _enqueue(_format_event("updated", {"id": payload}))

    conn: asyncpg.Connection | None = None
    try:
        conn = await asyncpg.connect(dsn)
        await init_connection(conn)
        await conn.add_listener(CHANNEL_INSERTED, _on_inserted)
        await conn.add_listener(CHANNEL_UPDATED, _on_updated)

        # Initial event so EventSource considers the stream open.
        yield _format_event("ready", {"channels": [CHANNEL_INSERTED, CHANNEL_UPDATED]})

        while True:
            if await request.is_disconnected():
                return
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL)
                yield payload
            except asyncio.TimeoutError:
                # SSE comment line keeps proxies from idling the connection.
                yield b": keepalive\n\n"
    finally:
        if conn is not None:
            with contextlib.suppress(Exception):
                await conn.remove_listener(CHANNEL_INSERTED, _on_inserted)
            with contextlib.suppress(Exception):
                await conn.remove_listener(CHANNEL_UPDATED, _on_updated)
            with contextlib.suppress(Exception):
                await conn.close()


def _format_event(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()
