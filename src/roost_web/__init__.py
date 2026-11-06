"""roost-web — dashboard for Roost.

Public API::

    from roost_web import dashboard

    app.mount("/jobs", dashboard(dsn="postgresql://..."))
"""

from __future__ import annotations

from importlib.metadata import version

from roost_web.app import create_app as dashboard

__version__ = version("roost-web")

__all__ = ["__version__", "dashboard"]
