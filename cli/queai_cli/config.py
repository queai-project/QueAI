"""
Manejo de `~/.config/queai/config.toml`.

Formato:

    endpoint = "http://localhost:8473"
    token    = "..."
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib  # type: ignore[import-not-found]
else:
    import tomli as tomllib  # type: ignore[no-redef]

import tomli_w


def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "queai" / "config.toml"


def load() -> dict[str, Any]:
    p = config_path()
    if not p.exists():
        return {}
    with open(p, "rb") as f:
        return tomllib.load(f)


def save(data: dict[str, Any]) -> Path:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        tomli_w.dump(data, f)
    try:
        p.chmod(0o600)
    except OSError:
        pass
    return p


def get_endpoint(override: str | None = None) -> str:
    if override:
        return override.rstrip("/")
    env = os.environ.get("QUEAI_ENDPOINT")
    if env:
        return env.rstrip("/")
    cfg = load().get("endpoint")
    if cfg:
        return str(cfg).rstrip("/")
    return "http://localhost:8473"


def get_token(override: str | None = None) -> str | None:
    if override:
        return override
    env = os.environ.get("QUEAI_API_TOKEN")
    if env:
        return env
    cfg = load().get("token")
    return str(cfg) if cfg else None
