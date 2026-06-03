"""
Backup / restore "light" — incluye solo el estado configurable, no los
plugins enteros ni sus runtimes/modelos pesados.

Contenido del tar.gz:

    metadata.json
    db.sqlite3
    .env          (del kernel)
    plugins/<folder>/.env  (uno por plugin con .env)

El restore extrae a `staging/`, valida y queda listo para swap manual.
El kernel debe reiniciarse después de un restore para que Django recargue
el db.sqlite3.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import tarfile
import time
from pathlib import Path

from django.conf import settings

from . import __name__ as _pkg  # noqa: F401  (asegura que core está importado)

METADATA_FILENAME = "metadata.json"
DB_NAME_IN_TAR = "db.sqlite3"
ENV_NAME_IN_TAR = ".env"


# ----------------------------------------------------------------------------
# BACKUP
# ----------------------------------------------------------------------------
def _base_dir() -> Path:
    return Path(settings.BASE_DIR)


def _plugins_dir() -> Path:
    return Path(settings.PLUGINS_DIR)


def build_backup() -> bytes:
    """Construye el tar.gz en memoria y devuelve los bytes."""
    base = _base_dir()
    plugins = _plugins_dir()

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        plugin_envs = []
        for folder in sorted(os.listdir(plugins)) if plugins.exists() else []:
            env_path = plugins / folder / ".env"
            if env_path.is_file():
                tar.add(env_path, arcname=f"plugins/{folder}/.env")
                plugin_envs.append(folder)

        db_path = base / "db.sqlite3"
        if db_path.is_file():
            tar.add(db_path, arcname=DB_NAME_IN_TAR)

        env_path = base / ".env"
        if env_path.is_file():
            tar.add(env_path, arcname=ENV_NAME_IN_TAR)

        metadata = {
            "kind": "queai-backup-light",
            "version": "1",
            "kernel_version": getattr(settings, "QUEAI_VERSION", "") or "",
            "created_at": int(time.time()),
            "includes": {
                "db_sqlite3": (base / "db.sqlite3").is_file(),
                "kernel_env": (base / ".env").is_file(),
                "plugin_envs": plugin_envs,
            },
        }
        meta_bytes = json.dumps(metadata, indent=2).encode("utf-8")
        info = tarfile.TarInfo(name=METADATA_FILENAME)
        info.size = len(meta_bytes)
        info.mtime = int(time.time())
        tar.addfile(info, io.BytesIO(meta_bytes))

    return buf.getvalue()


def backup_filename() -> str:
    return f"queai-backup-{time.strftime('%Y%m%d-%H%M%S')}.tar.gz"


# ----------------------------------------------------------------------------
# RESTORE
# ----------------------------------------------------------------------------
STAGING_DIR_NAME = "restore-staging"


def restore_to_staging(file_obj) -> dict:
    """
    Recibe un file-like (tar.gz) y extrae a BASE_DIR / restore-staging/.
    Valida que metadata.json exista y sea kind queai-backup-light.
    No toca el sistema en vivo (el swap es manual o por endpoint /apply).
    """
    base = _base_dir()
    staging = base / STAGING_DIR_NAME
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    try:
        with tarfile.open(fileobj=file_obj, mode="r:gz") as tar:
            for member in tar.getmembers():
                # Rechazar entradas absolutas o que escapen.
                if member.name.startswith("/") or ".." in Path(member.name).parts:
                    raise ValueError(f"path inseguro en tar: {member.name}")
            tar.extractall(staging)
    except tarfile.ReadError as e:
        raise ValueError(f"tar inválido: {e}") from e

    meta_path = staging / METADATA_FILENAME
    if not meta_path.is_file():
        raise ValueError("metadata.json ausente en el tar.")
    try:
        meta = json.loads(meta_path.read_text("utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"metadata.json inválido: {e}") from e
    if meta.get("kind") != "queai-backup-light":
        raise ValueError(f"kind inesperado: {meta.get('kind')!r}")

    return {
        "staging": str(staging),
        "metadata": meta,
    }


def apply_restore() -> dict:
    """
    Mueve el contenido de staging al sistema en vivo. Hace backup previo
    del db.sqlite3 actual a `db.sqlite3.pre-restore`. NO reinicia el
    kernel — el operador debe `docker compose restart django-kernel`
    después porque Django mantiene un handle abierto a la BD.
    """
    base = _base_dir()
    plugins = _plugins_dir()
    staging = base / STAGING_DIR_NAME

    if not staging.is_dir():
        raise ValueError("No hay staging para aplicar. Llama /restore primero.")

    moved = []

    staging_db = staging / DB_NAME_IN_TAR
    if staging_db.is_file():
        current = base / DB_NAME_IN_TAR
        if current.is_file():
            shutil.copy2(current, base / "db.sqlite3.pre-restore")
        shutil.copy2(staging_db, current)
        moved.append("db.sqlite3")

    staging_env = staging / ENV_NAME_IN_TAR
    if staging_env.is_file():
        current = base / ENV_NAME_IN_TAR
        if current.is_file():
            shutil.copy2(current, base / ".env.pre-restore")
        shutil.copy2(staging_env, current)
        moved.append(".env")

    staging_plugins = staging / "plugins"
    if staging_plugins.is_dir():
        for folder in os.listdir(staging_plugins):
            src = staging_plugins / folder / ".env"
            if src.is_file():
                dest_dir = plugins / folder
                if dest_dir.is_dir():
                    shutil.copy2(src, dest_dir / ".env")
                    moved.append(f"plugins/{folder}/.env")

    return {"applied": moved, "warning": "Reinicia el kernel para que Django recargue db.sqlite3."}
