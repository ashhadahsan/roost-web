# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-06

First release on PyPI.

### Added

- Initial scaffold: Starlette app, HTMX-driven UI, vendored HTMX + SSE extension, hand-written CSS (no Node toolchain).
- HTMX pages: overview, jobs (filterable, paginated), job detail, queues (pause/resume), workers.
- SSE live updates bridged from Postgres `LISTEN roost_inserted` / `LISTEN roost_updated`.
- JSON API v1: `/api/v1/health`, `/status`, `/jobs`, `/jobs/{id}`, `/jobs/{id}/retry`, `/jobs/{id}/cancel`, `/queues`, `/queues/{name}/pause`, `/queues/{name}/resume`, `/workers`.
- `read_only=True` mode that returns 403 for any mutating route.
- testcontainers-based test suite covering pages, JSON API, read-only mode, and static asset serving.
- Cron page, worker detail, completed-per-minute sparkline, bulk retry and cancel, and search by args JSON.
- Screenshots in the README.
- CI: every Python 3.10 to 3.14 on Postgres 18 and every Postgres 13 to 18 on Python 3.13, locked installs, pinned actions, package metadata check and workflow security lint. Release builds once, checks the tag matches the version, and publishes through the `pypi` environment (TestPyPI on a manual run).
- Community files: SECURITY.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md, issue + PR templates.

### Fixed

- Times in the future showed raw seconds ("in 276961s"). They now use the same units as past times ("in 3d").
- Overview column headers lined up with the wrong numbers; numeric headers are right-aligned like their values.
- The jobs Filter button was unstyled.
- `roost_web.__version__` reads the installed version instead of a hardcoded `0.1.0.dev0`.

### Changed

- Depends on `pgroost>=0.1.1,<0.2` from PyPI. roost-web uses `roost._core`, which can change in any pgroost minor release, so the upper bound is deliberate. The local `../roost` path source is gone; see CONTRIBUTING for working against a local checkout.
- Dropped the unused `docs` extra and the Read the Docs link (no docs site exists; the README is the documentation).

[Unreleased]: https://github.com/ashhadahsan/roost-web/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ashhadahsan/roost-web/releases/tag/v0.1.0
