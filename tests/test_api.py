"""JSON API v1 smoke tests."""

from __future__ import annotations

import psycopg
from starlette.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_status_returns_counts(seeded_client: TestClient) -> None:
    r = seeded_client.get("/api/v1/status")
    assert r.status_code == 200
    counts = r.json()["counts"]
    assert any(c["queue"] == "default" and c["state"] == "available" for c in counts)


def test_jobs_list_pagination_and_filter(seeded_client: TestClient) -> None:
    r = seeded_client.get("/api/v1/jobs", params={"page_size": 2})
    body = r.json()
    assert r.status_code == 200
    assert body["total"] >= 5
    assert body["page_size"] == 2
    assert len(body["items"]) == 2

    r = seeded_client.get("/api/v1/jobs", params={"state": "discarded"})
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["state"] == "discarded"


def test_get_job_returns_full_row(seeded_client: TestClient, fresh_dsn: str) -> None:
    with psycopg.connect(fresh_dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM roost.jobs ORDER BY id LIMIT 1")
        row = cur.fetchone()
        assert row is not None
        job_id = row[0]
    r = seeded_client.get(f"/api/v1/jobs/{job_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == job_id
    assert "task" in body
    assert "tags" in body


def test_get_job_404(client: TestClient) -> None:
    r = client.get("/api/v1/jobs/99999")
    assert r.status_code == 404


def test_retry_endpoint(seeded_client: TestClient, fresh_dsn: str) -> None:
    with psycopg.connect(fresh_dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM roost.jobs WHERE state = 'discarded' LIMIT 1")
        row = cur.fetchone()
        assert row is not None
        job_id = row[0]
    r = seeded_client.post(f"/api/v1/jobs/{job_id}/retry")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # State has flipped to available.
    with psycopg.connect(fresh_dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT state FROM roost.jobs WHERE id = $1".replace("$1", "%s"), (job_id,))
        row = cur.fetchone()
        assert row is not None and row[0] == "available"


def test_pause_and_resume_queue(seeded_client: TestClient) -> None:
    r = seeded_client.post("/api/v1/queues/emails/pause")
    assert r.status_code == 200
    body = r.json()
    assert body["paused"] is True

    r = seeded_client.get("/api/v1/queues")
    items = {item["name"]: item for item in r.json()["items"]}
    assert items.get("emails", {}).get("paused_at") is not None

    r = seeded_client.post("/api/v1/queues/emails/resume")
    assert r.status_code == 200
    assert r.json()["paused"] is False


def test_workers_endpoint(client: TestClient) -> None:
    r = client.get("/api/v1/workers")
    assert r.status_code == 200
    assert r.json() == {"items": []}


def test_read_only_rejects_mutations(read_only_client: TestClient, fresh_dsn: str) -> None:
    r = read_only_client.post(
        "/api/v1/queues/default/pause",
        headers={"Accept": "application/json"},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "dashboard is read-only"
