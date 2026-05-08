# Security policy

## Supported versions

Until `1.0`, only the latest minor release receives security fixes. Pin exactly in production.

| Version | Status        |
| ------- | ------------- |
| `0.1.x` | active        |
| `< 0.1` | not supported |

## Reporting

**Don't file a public issue for security problems.**

Email `ashhadahsan@gmail.com` with:

- a description of the issue,
- the affected version(s),
- a minimal reproducer,
- any disclosure deadline.

You'll get an acknowledgment within three business days.

## Auth is not in scope

`roost-web` deliberately does **not** ship auth. The dashboard is meant to mount inside a host app that already has auth (FastAPI dependencies, Django middleware, Flask-Login, etc.). Hosting it without authentication is a configuration error, not a vulnerability in `roost-web`.

If you need a hardening checklist:

- Mount the dashboard behind your existing auth middleware.
- Use `dashboard(dsn=..., read_only=True)` in any environment where mutating actions shouldn't be available.
- Restrict the database role used by the dashboard to `SELECT` and the specific `UPDATE`s on `roost.jobs` and `roost.queues`.
- Use TLS to Postgres in production.

## Out of scope

Vulnerabilities in `roost` (the core), `starlette`, `asyncpg`, `jinja2`, or PostgreSQL itself — please report to those upstreams.
