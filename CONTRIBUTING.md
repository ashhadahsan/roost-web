# Contributing to roost-web

Thanks for your interest in helping build the Roost dashboard.

## Setup

```bash
git clone https://github.com/ashhadahsan/roost-web.git
cd roost-web
uv sync
uv run pre-commit install
```

`uv sync` installs the published `pgroost` from PyPI, the same version CI tests against. To work against a local Roost checkout at `../roost` instead, run `uv pip install -e ../roost` after `uv sync` (the next `uv sync` puts the PyPI version back).

You will need Docker running for the test suite — we use `testcontainers[postgres]`.

## Running checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -n auto
```

## Style

- Ruff for lint + format. Configured in `pyproject.toml`.
- `mypy --strict` on `src/roost_web`. Tests are excluded from strict typing.
- Type hints on every public function. We ship a `py.typed` marker.

## Conventional Commits

- `feat:` user-visible feature
- `fix:` bug fix
- `docs:` documentation only
- `refactor:` internal change with no user impact
- `test:` tests only
- `chore:` tooling / housekeeping

## Pull requests

1. Fork + branch off `main`.
2. Focused changes — one feature/fix per PR.
3. Tests required. PRs without tests don't merge unless the change is genuinely untestable.
4. Update `CHANGELOG.md` under `## [Unreleased]`.
5. Open the PR; CI must be green.

## Schema coupling

The dashboard reads from `roost.jobs`, `roost.workers`, `roost.queues`. If you find yourself wanting a column that doesn't exist, file an issue against [`ashhadahsan/roost`](https://github.com/ashhadahsan/roost) first. Don't fork the schema or write to it from this side.
