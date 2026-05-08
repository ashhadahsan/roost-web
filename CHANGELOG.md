# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial scaffold: Starlette app, HTMX-driven UI, vendored HTMX + SSE extension, hand-written CSS (no Node toolchain).
- HTMX pages: overview, jobs (filterable, paginated), job detail, queues (pause/resume), workers.
- SSE live updates bridged from Postgres `LISTEN roost_inserted` / `LISTEN roost_updated`.
- JSON API v1: `/api/v1/health`, `/status`, `/jobs`, `/jobs/{id}`, `/jobs/{id}/retry`, `/jobs/{id}/cancel`, `/queues`, `/queues/{name}/pause`, `/queues/{name}/resume`, `/workers`.
- `read_only=True` mode that returns 403 for any mutating route.
- testcontainers-based test suite covering pages, JSON API, read-only mode, and static asset serving.
- CI workflow (Python 3.10–3.13 × Postgres 13–16) and release workflow (PyPI Trusted Publisher OIDC).
- Community files: SECURITY.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md, issue + PR templates.

[Unreleased]: https://github.com/ashhadahsan/roost-web/compare/v0.0.0...HEAD
