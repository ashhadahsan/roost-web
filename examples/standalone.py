"""Run the dashboard standalone for local hacking.

    uvicorn examples.standalone:app --reload --port 8000

Then open http://localhost:8000.

Reads ``ROOST_DSN`` (defaults to local Postgres). On first boot, applies the
Roost schema and seeds a handful of jobs across queues + states so the UI
isn't empty.
"""

from __future__ import annotations

import os
import random

import psycopg
from roost._core.repo import apply_schema_sync

from roost_web import dashboard

DSN = os.environ.get("ROOST_DSN", "postgresql://postgres:postgres@localhost:5432/postgres")


def _seed_demo_jobs(dsn: str) -> None:
    with psycopg.connect(dsn) as conn:
        apply_schema_sync(conn)
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM roost.jobs")
            row = cur.fetchone()
            if row and row[0] > 0:
                return
            tasks = [
                ("send_welcome_email", "default", "available"),
                ("send_welcome_email", "default", "completed"),
                ("send_welcome_email", "default", "completed"),
                ("send_welcome_email", "default", "executing"),
                ("nightly_digest", "emails", "available"),
                ("nightly_digest", "emails", "retryable"),
                ("nightly_digest", "emails", "completed"),
                ("nightly_digest", "emails", "discarded"),
                ("export_csv", "reports", "available"),
                ("export_csv", "reports", "executing"),
                ("export_csv", "reports", "completed"),
                ("resize_image", "images", "completed"),
                ("resize_image", "images", "completed"),
                ("resize_image", "images", "discarded"),
            ]
            for task, queue, state in tasks:
                cur.execute(
                    """
                    INSERT INTO roost.jobs (task, queue, state, attempt, max_attempts, args, tags)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::text[])
                    """,
                    (
                        task,
                        queue,
                        state,
                        random.randint(0, 3),
                        20,
                        '{"demo": true}',
                        random.choice([["demo"], ["demo", "hot"], []]),
                    ),
                )
        conn.commit()
        print(f"[roost-web demo] seeded sample jobs into {dsn}")


_seed_demo_jobs(DSN)
app = dashboard(dsn=DSN, title="Roost — demo")
