"""
Funciones de serialización modelo → dict para las respuestas JSON.

Sin DRF: son funciones planas, fáciles de leer y de versionar.
"""

from __future__ import annotations

from module_manager.models import AvailableApp


def plugin_to_dict(app: AvailableApp, *, is_running: bool | None = None) -> dict:
    return {
        "name": app.name,
        "folder_name": app.folder_name,
        "display_name": app.display_name,
        "version": app.version,
        "description": app.description,
        "author": app.author,
        "license": app.lic,
        "logo": app.logo,
        "entry_points": {
            "ui": app.ui_entry_point,
            "config": app.configuration_entry_point,
            "docs": app.documentation_entry_point,
        },
        "state": {
            "installed": bool(app.is_installed),
            "running": bool(is_running) if is_running is not None else None,
        },
    }
