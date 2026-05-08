"""roost-web — dashboard for Roost.

Public API::

    from roost_web import dashboard

    app.mount("/jobs", dashboard(dsn="postgresql://..."))
"""

from __future__ import annotations

from roost_web.app import create_app as dashboard

__version__ = "0.1.0.dev0"

__all__ = ["__version__", "dashboard"]
