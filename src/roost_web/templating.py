"""Jinja2 environment + datetime/JSON filters."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from starlette.templating import Jinja2Templates

_ROOT = Path(__file__).resolve().parent
_TEMPLATES_DIR = _ROOT / "templates"


def _humanize_dt(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _relative_dt(value: datetime | None) -> str:
    if value is None:
        return "—"
    delta = datetime.now(tz=timezone.utc) - value.astimezone(timezone.utc)
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return f"in {-seconds}s"
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


def _to_json(value: Any) -> str:
    return json.dumps(value, indent=2, default=str)


templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
templates.env.filters["humanize_dt"] = _humanize_dt
templates.env.filters["relative_dt"] = _relative_dt
templates.env.filters["to_json"] = _to_json


__all__ = ["templates"]
