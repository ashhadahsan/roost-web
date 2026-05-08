"""Smoke tests for the HTMX-rendered pages."""

from __future__ import annotations

import psycopg
from starlette.testclient import TestClient


def test_overview_renders(seeded_client: TestClient) -> None:
    r = seeded_client.get("/")
    assert r.status_code == 200
    body = r.text
    assert "Overview" in body
    assert "default" in body
    assert "emails" in body
    assert "reports" in body


def test_jobs_list_renders_and_filters(seeded_client: TestClient) -> None:
    r = seeded_client.get("/jobs")
    assert r.status_code == 200
    assert "send_email" in r.text
    assert "digest" in r.text

    # Filter by state
    r = seeded_client.get("/jobs", params={"state": "discarded"})
    assert r.status_code == 200
    assert "digest" in r.text  # the only discarded
    assert "Showing" in r.text


def test_job_detail_404s_for_missing(client: TestClient) -> None:
    r = client.get("/jobs/9999")
    assert r.status_code == 404


def test_job_detail_renders(seeded_client: TestClient, fresh_dsn: str) -> None:
    with psycopg.connect(fresh_dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM roost.jobs ORDER BY id LIMIT 1")
        row = cur.fetchone()
        assert row is not None
        job_id = row[0]
    r = seeded_client.get(f"/jobs/{job_id}")
    assert r.status_code == 200
    assert f"Job {job_id}" in r.text


def test_retry_endpoint_redirects(seeded_client: TestClient, fresh_dsn: str) -> None:
    with psycopg.connect(fresh_dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM roost.jobs WHERE state = 'discarded' LIMIT 1")
        row = cur.fetchone()
        assert row is not None
        job_id = row[0]
    r = seeded_client.post(f"/jobs/{job_id}/retry", follow_redirects=False)
    assert r.status_code in (303, 204)


def test_retry_endpoint_htmx_returns_204(seeded_client: TestClient, fresh_dsn: str) -> None:
    with psycopg.connect(fresh_dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM roost.jobs WHERE state = 'discarded' LIMIT 1")
        row = cur.fetchone()
        assert row is not None
        job_id = row[0]
    r = seeded_client.post(
        f"/jobs/{job_id}/retry",
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 204
    assert r.headers.get("HX-Refresh") == "true"


def test_queues_page_lists_queues(seeded_client: TestClient) -> None:
    r = seeded_client.get("/queues")
    assert r.status_code == 200
    assert "default" in r.text
    assert "emails" in r.text


def test_workers_page_renders(client: TestClient) -> None:
    r = client.get("/workers")
    assert r.status_code == 200
    assert "Workers" in r.text


def test_static_assets_served(client: TestClient) -> None:
    for path in ("/static/style.css", "/static/htmx.min.js", "/static/htmx-sse.min.js", "/static/logo.svg"):
        r = client.get(path)
        assert r.status_code == 200, f"missing static: {path}"


def test_read_only_blocks_mutations(read_only_client: TestClient, fresh_dsn: str) -> None:
    # Seed inside the read_only_client's DSN so we have a row to act on.
    with psycopg.connect(fresh_dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO roost.jobs (queue, task, state) VALUES ('default','x','discarded') RETURNING id"
        )
        row = cur.fetchone()
        assert row is not None
        job_id = row[0]
        conn.commit()

    r = read_only_client.post(f"/jobs/{job_id}/retry")
    assert r.status_code == 403


def test_read_only_get_pages_still_render(read_only_client: TestClient) -> None:
    r = read_only_client.get("/")
    assert r.status_code == 200
    assert "read-only" in r.text
