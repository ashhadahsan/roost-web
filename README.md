<!-- markdownlint-disable MD033 MD041 -->
<p align="center">
  <img src="src/roost_web/static/logo.svg" alt="Roost" width="180"/>
</p>

<h1 align="center">roost-web</h1>

<p align="center">
  <em>Drop-in dashboard for <a href="https://github.com/ashhadahsan/roost">Roost</a>, the Postgres-backed background job queue.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/roost-web/"><img src="https://img.shields.io/pypi/v/roost-web.svg" alt="PyPI"/></a>
  <a href="https://pypi.org/project/roost-web/"><img src="https://img.shields.io/pypi/pyversions/roost-web.svg" alt="Python versions"/></a>
  <a href="https://github.com/ashhadahsan/roost-web/actions/workflows/ci.yml"><img src="https://github.com/ashhadahsan/roost-web/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/pypi/l/roost-web.svg" alt="MIT"/></a>
</p>

> 🚧 **Alpha** — under active development. Pin exactly.

## What is this?

A dashboard you mount inside your existing Python app:

```python
from fastapi import FastAPI
from roost_web import dashboard

app = FastAPI()
app.mount("/jobs", dashboard(dsn="postgresql://..."))
```

Three lines, no separate deploy, no Node.js. Inherits your host app's auth.

## Why HTMX, not React?

This is an *embedded* admin dashboard for a Python queue. Audience is developers and oncall engineers, not consumers. The killer property is "pure Python pip install, mount, done." A React/Next.js dashboard would force every Python shop to deploy a separate SPA + API + configure CORS. We picked the same trade-off Oban Web (LiveView) and Django Admin make.

If you want a custom UI: there's a stable `JSON API at /api/v1` you can build whatever you like against.

## Features

| | |
|---|---|
| Drop-in mount | `app.mount("/jobs", dashboard(dsn=...))` |
| Live updates | Server-Sent Events backed by Postgres `LISTEN`/`NOTIFY` |
| Read-only mode | `dashboard(dsn=..., read_only=True)` for staging |
| JSON API | `GET /api/v1/jobs`, `POST /api/v1/jobs/{id}/retry`, etc. |
| Pages | Overview · Jobs (filterable, paginated) · Job detail · Queues (pause/resume) · Workers |
| Auth | Delegated to host app — wire your own middleware |
| Bundle | HTMX + hand-written CSS · ~60KB total · no Node toolchain |

## Compatibility

- **Python:** 3.10, 3.11, 3.12, 3.13.
- **PostgreSQL:** 13, 14, 15, 16.
- **Roost:** `>=0.1.0`.
- **Hosts:** any ASGI app — FastAPI, Starlette, Django (via ASGI mount), Litestar, Quart.

## Mounting examples

### FastAPI

```python
from fastapi import FastAPI
from roost_web import dashboard

app = FastAPI()
app.mount("/jobs", dashboard(dsn="postgresql://..."))
```

### Starlette

```python
from starlette.applications import Starlette
from starlette.routing import Mount
from roost_web import dashboard

app = Starlette(routes=[Mount("/jobs", app=dashboard(dsn="..."))])
```

### Standalone

```bash
uvicorn examples.standalone:app --port 8000
```

## Project structure

| Concern | File |
|---|---|
| Public factory | `src/roost_web/__init__.py` |
| Starlette app | `src/roost_web/app.py` |
| HTMX routes | `src/roost_web/routes/*.py` |
| JSON API v1 | `src/roost_web/api/v1.py` |
| SSE bridge | `src/roost_web/routes/sse.py` |
| Templates | `src/roost_web/templates/` |
| Static assets (HTMX, CSS, logo) | `src/roost_web/static/` |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security: [SECURITY.md](SECURITY.md). All participants are expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

MIT — see [LICENSE](LICENSE).
