"""Shared fixtures.

Spins up Postgres via testcontainers, applies the Roost schema, and
exposes the dashboard as a Starlette TestClient. Each test gets its own
database so state is isolated.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import psycopg
import pytest
from roost._core.repo import apply_schema_sync
from starlette.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from roost_web import dashboard


@pytest.fixture(scope="session")
def pg_container() -> Iterator[PostgresContainer]:
    image = os.environ.get("ROOST_TEST_PG_IMAGE", "postgres:16-alpine")
    with PostgresContainer(image) as container:
        yield container


@pytest.fixture(scope="session")
def base_dsn(pg_container: PostgresContainer) -> str:
    raw = pg_container.get_connection_url()
    if raw.startswith("postgresql+"):
        raw = "postgresql://" + raw.split("://", 1)[1]
    return raw


@pytest.fixture
def fresh_dsn(base_dsn: str, request: pytest.FixtureRequest) -> Iterator[str]:
    safe = request.node.name.replace("-", "_").replace("[", "_").replace("]", "_")[:40]
    suffix = abs(hash(request.node.nodeid)) % 10_000
    db_name = f"rweb_{safe}_{suffix}"

    with psycopg.connect(base_dsn, autocommit=True) as admin, admin.cursor() as cur:
        cur.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
        cur.execute(f'CREATE DATABASE "{db_name}"')

    parts = base_dsn.rsplit("/", 1)
    dsn = f"{parts[0]}/{db_name}"

    with psycopg.connect(dsn) as conn:
        apply_schema_sync(conn)
        conn.commit()

    yield dsn

    with psycopg.connect(base_dsn, autocommit=True) as admin, admin.cursor() as cur:
        cur.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')


@pytest.fixture
def client(fresh_dsn: str) -> Iterator[TestClient]:
    app = dashboard(dsn=fresh_dsn)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def read_only_client(fresh_dsn: str) -> Iterator[TestClient]:
    app = dashboard(dsn=fresh_dsn, read_only=True)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seeded_client(client: TestClient, fresh_dsn: str) -> TestClient:
    """Insert a handful of jobs across queues/states so list pages aren't empty."""
    with psycopg.connect(fresh_dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO roost.jobs (queue, task, state, attempt) VALUES "
            "  ('default', 'send_email', 'available', 0), "
            "  ('default', 'send_email', 'completed', 1), "
            "  ('emails',  'digest',     'retryable', 1), "
            "  ('emails',  'digest',     'discarded', 5), "
            "  ('reports', 'export',     'executing', 1)"
        )
        conn.commit()
    return client
