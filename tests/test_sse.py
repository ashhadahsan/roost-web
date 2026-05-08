"""End-to-end SSE bridge test.

Opens a streaming GET on /events/jobs, then inserts and updates a job
via Postgres directly. The stream should emit ``event: inserted`` and
``event: updated`` frames within a few seconds.
"""

from __future__ import annotations

import asyncio
import contextlib

import httpx
import psycopg
import pytest

from roost_web import dashboard


async def _read_until(stream: httpx.Response, *needles: str, timeout: float = 5.0) -> list[str]:
    """Consume SSE frames until every needle has appeared (or timeout)."""
    seen: list[str] = []
    needles_left = set(needles)
    deadline = asyncio.get_event_loop().time() + timeout
    async for line in stream.aiter_lines():
        if not line:
            continue
        seen.append(line)
        for n in list(needles_left):
            if n in line:
                needles_left.discard(n)
        if not needles_left:
            return seen
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError(f"timed out waiting for {needles_left}; saw: {seen[-20:]}")
    raise AssertionError(f"stream ended early; missing {needles_left}; saw {seen[-20:]}")


@pytest.mark.asyncio
async def test_sse_emits_inserted_and_updated(fresh_dsn: str) -> None:
    app = dashboard(dsn=fresh_dsn)
    async with (
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client,
        client.stream("GET", "/events/jobs") as stream,
    ):
        assert stream.status_code == 200

        async def _drive() -> None:
            await asyncio.sleep(0.5)
            with psycopg.connect(fresh_dsn) as conn, conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO roost.jobs (task, queue, state) "
                    "VALUES ('demo','default','available') RETURNING id"
                )
                row = cur.fetchone()
                assert row is not None
                jid = row[0]
                conn.commit()
                cur.execute(
                    "UPDATE roost.jobs SET state = 'completed',     completed_at = now() WHERE id = %s",
                    (jid,),
                )
                conn.commit()

        driver = asyncio.create_task(_drive())
        try:
            lines = await _read_until(stream, "event: inserted", "event: updated", timeout=8.0)
        finally:
            driver.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await driver

    assert any("event: ready" in line for line in lines)


@pytest.mark.asyncio
async def test_sse_keepalive_when_idle(fresh_dsn: str) -> None:
    """No DB activity → the stream still emits a ``: keepalive`` heartbeat."""
    app = dashboard(dsn=fresh_dsn)

    from roost_web.routes import sse

    original = sse._HEARTBEAT_INTERVAL
    sse._HEARTBEAT_INTERVAL = 0.5
    try:
        async with (
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client,
            client.stream("GET", "/events/jobs") as stream,
        ):
            lines: list[str] = []
            async for line in stream.aiter_lines():
                lines.append(line)
                if any(": keepalive" in s for s in lines):
                    break
                if len(lines) > 50:
                    raise AssertionError(f"no keepalive seen; saw {lines}")
    finally:
        sse._HEARTBEAT_INTERVAL = original
