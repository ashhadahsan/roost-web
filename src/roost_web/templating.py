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
    seconds = int((datetime.now(tz=timezone.utc) - value.astimezone(timezone.utc)).total_seconds())
    n = abs(seconds)
    if n < 60:
        span = f"{n}s"
    elif n < 3600:
        span = f"{n // 60}m"
    elif n < 86400:
        span = f"{n // 3600}h"
    else:
        span = f"{n // 86400}d"
    return f"in {span}" if seconds < 0 else f"{span} ago"


def _to_json(value: Any) -> str:
    return json.dumps(value, indent=2, default=str)


templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
templates.env.filters["humanize_dt"] = _humanize_dt
templates.env.filters["relative_dt"] = _relative_dt
templates.env.filters["to_json"] = _to_json


__all__ = ["templates"]
