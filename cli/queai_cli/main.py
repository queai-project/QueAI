"""
CLI `queai`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import click

from . import __version__, config
from .client import APIError, QueaiClient


def _client(ctx) -> QueaiClient:
    endpoint = config.get_endpoint(ctx.obj.get("endpoint"))
    token = config.get_token(ctx.obj.get("token"))
    return QueaiClient(endpoint=endpoint, token=token)


def _handle(fn):
    """Decorator que pinta APIError como mensaje con color en vez de traceback."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except APIError as e:
            click.secho(f"✗ {e}", fg="red", err=True)
            sys.exit(1)

    return wrapper


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--endpoint", help="URL del kernel (default: http://localhost:8080 o ~/.config/queai/config.toml).")
@click.option("--token", help="Token API (default: ~/.config/queai/config.toml).")
@click.version_option(__version__, "-V", "--version", prog_name="queai")
@click.pass_context
def cli(ctx, endpoint, token):
    """Línea de comandos para el kernel QueAI."""
    ctx.ensure_object(dict)
    ctx.obj["endpoint"] = endpoint
    ctx.obj["token"] = token


# ----------------------------------------------------------------------------
# auth
# ----------------------------------------------------------------------------
@cli.command()
@click.argument("endpoint")
@click.option("--token", prompt="Token API", hide_input=True, help="QUEAI_API_TOKEN del kernel.")
def login(endpoint, token):
    """Guarda endpoint + token en ~/.config/queai/config.toml."""
    data = config.load()
    data["endpoint"] = endpoint.rstrip("/")
    data["token"] = token
    p = config.save(data)
    click.secho(f"✓ Guardado en {p}", fg="green")


@cli.command()
def logout():
    """Borra el token (no el endpoint) del config."""
    data = config.load()
    data.pop("token", None)
    config.save(data)
    click.secho("✓ Token borrado.", fg="green")


# ----------------------------------------------------------------------------
# meta
# ----------------------------------------------------------------------------
@cli.command()
@click.pass_context
@_handle
def health(ctx):
    """Estado del kernel (no requiere token)."""
    data = _client(ctx).health()
    click.echo(json.dumps(data, indent=2))


# ----------------------------------------------------------------------------
# catálogo + lifecycle
# ----------------------------------------------------------------------------
@cli.command(name="list")
@click.option("--folders", is_flag=True, help="Mostrar también la columna FOLDER (nombre largo del directorio).")
@click.pass_context
@_handle
def list_cmd(ctx, folders):
    """Lista plugins instalados y disponibles. Cualquier `NAME` o `FOLDER`
    es válido como identificador en el resto de comandos."""
    data = _client(ctx).plugins_list()
    items = data.get("plugins", [])
    if not items:
        click.echo("(sin plugins detectados)")
        return
    if folders:
        click.echo(f"{'NAME':22} {'STATE':10} {'VERSION':10} {'FOLDER':32} DESCRIPTION")
        for p in items:
            label = _state_label(p["state"])
            click.echo(
                f"{p['name'][:22]:22} {label:10} {p['version']:10} "
                f"{p['folder_name'][:32]:32} {p['description'][:40]}"
            )
    else:
        click.echo(f"{'NAME':22} {'STATE':10} {'VERSION':10} DESCRIPTION")
        for p in items:
            label = _state_label(p["state"])
            click.echo(f"{p['name'][:22]:22} {label:10} {p['version']:10} {p['description'][:60]}")


def _state_label(state: dict) -> str:
    if state["installed"]:
        return "running" if state["running"] else "stopped"
    return "fresh"


@cli.command()
@click.argument("folder")
@click.pass_context
@_handle
def show(ctx, folder):
    """Detalle de un plugin (JSON)."""
    click.echo(json.dumps(_client(ctx).plugin_detail(folder), indent=2))


@cli.command()
@click.argument("folder")
@click.pass_context
@_handle
def install(ctx, folder):
    """Instala un módulo ya descargado."""
    res = _client(ctx).install(folder)
    click.secho(f"✓ {res['folder_name']} → {res['status']}", fg="green")


@cli.command()
@click.argument("folder")
@click.pass_context
@_handle
def start(ctx, folder):
    """Inicia un módulo detenido."""
    res = _client(ctx).start(folder)
    click.secho(f"✓ {res['folder_name']} → {res['status']}", fg="green")


@cli.command()
@click.argument("folder")
@click.pass_context
@_handle
def stop(ctx, folder):
    """Detiene un módulo."""
    res = _client(ctx).stop(folder)
    click.secho(f"⏸ {res['folder_name']} → {res['status']}", fg="yellow")


@cli.command()
@click.argument("folder")
@click.confirmation_option(prompt="¿Desinstalar el módulo? (carpeta conservada)")
@click.pass_context
@_handle
def uninstall(ctx, folder):
    """Desinstala un módulo (conserva la carpeta del plugin)."""
    res = _client(ctx).uninstall(folder)
    click.secho(f"✓ {res['folder_name']} → {res['status']}", fg="green")


@cli.command()
@click.argument("folder")
@click.confirmation_option(prompt="Borrar TODO (contenedores + imágenes + carpeta) — ¿continuar?")
@click.pass_context
@_handle
def delete(ctx, folder):
    """Borra completamente un plugin (no reversible)."""
    res = _client(ctx).delete(folder)
    click.secho(f"✓ {res['folder_name']} → {res['status']}", fg="red")


# ----------------------------------------------------------------------------
# logs / stats
# ----------------------------------------------------------------------------
@cli.command()
@click.argument("folder")
@click.option("--tail", "-n", default=150, show_default=True, type=click.IntRange(1, 2000))
@click.option("--follow", "-f", is_flag=True, help="Stream en vivo (Ctrl+C para parar).")
@click.pass_context
@_handle
def logs(ctx, folder, tail, follow):
    """Logs del contenedor (último tail de líneas). Con -f hace follow vía SSE."""
    client = _client(ctx)
    if follow:
        # Tail limit del stream: usamos el min(tail, 500) que es el server-side limit.
        try:
            for line in client.logs_stream(folder, tail=min(tail, 500)):
                click.echo(line)
        except KeyboardInterrupt:
            click.secho("\n[stream interrumpido]", fg="yellow", err=True)
        return
    res = client.logs(folder, tail=tail)
    click.echo(res.get("logs", ""))


@cli.command()
@click.argument("folder")
@click.pass_context
@_handle
def stats(ctx, folder):
    """CPU / RAM / red por contenedor del módulo."""
    res = _client(ctx).stats(folder)
    containers = res.get("containers", [])
    if not containers:
        click.echo("(sin contenedores activos)")
        return
    click.echo(f"{'CONTAINER':14} {'CPU':8} {'MEMORY':24} NETWORK")
    for c in containers:
        click.echo(f"{c['id'][:12]:14} {c['cpu']:8} {c['mem']:24} {c['net']}")


# ----------------------------------------------------------------------------
# env
# ----------------------------------------------------------------------------
@cli.command()
@click.argument("folder")
@click.option("--edit", is_flag=True, help="Abre $EDITOR y guarda al cerrar.")
@click.option("--no-apply", is_flag=True, help="No recrear el contenedor al guardar.")
@click.pass_context
@_handle
def env(ctx, folder, edit, no_apply):
    """Muestra (o edita con --edit) el .env de un módulo."""
    client = _client(ctx)
    current = client.env_get(folder).get("content", "")

    if not edit:
        click.echo(current)
        return

    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile("w+", suffix=".env", delete=False) as f:
        f.write(current)
        f.flush()
        tmp_path = f.name
    try:
        subprocess.call([editor, tmp_path])
        with open(tmp_path) as f:
            new_content = f.read()
    finally:
        os.unlink(tmp_path)

    if new_content == current:
        click.secho("Sin cambios.", fg="yellow")
        return

    res = client.env_put(folder, new_content, apply=not no_apply)
    click.secho(f"✓ .env guardado{' (sin recreate)' if no_apply else ''} → applied={res['applied']}", fg="green")


# ----------------------------------------------------------------------------
# marketplace
# ----------------------------------------------------------------------------
@cli.command(name="marketplace")
@click.pass_context
@_handle
def marketplace_cmd(ctx):
    """Lista plugins del registry remoto."""
    data = _client(ctx).marketplace_list()
    items = data.get("plugins", [])
    if not items:
        click.echo("(registry vacío o sin conexión)")
        return
    click.echo(f"{'NAME':22} {'STATE':14} {'REMOTE':10} LOCAL")
    for p in items:
        state = "↑ update" if p.get("is_update_available") else ("✓ downloaded" if p.get("is_downloaded") else "  fresh")
        local = p.get("local_version") or "—"
        click.echo(f"{p.get('name','')[:22]:22} {state:14} {p.get('version','—'):10} {local}")


@cli.command()
@click.option("--action", help="Filtra por acción (install/start/stop/...).")
@click.option("--target", help="Sub-string contenido en target.")
@click.option("--source", type=click.Choice(["ui", "api", "cli", "system"]), help="Filtra por fuente.")
@click.option("--limit", "-n", default=50, show_default=True, type=click.IntRange(1, 1000))
@click.pass_context
@_handle
def audit(ctx, action, target, source, limit):
    """Audit log: quién hizo qué y cuándo."""
    data = _client(ctx).audit_list(action=action, target=target, source=source, limit=limit)
    events = data.get("events", [])
    if not events:
        click.echo("(sin eventos)")
        return
    click.echo(f"{'TIMESTAMP':20} {'SRC':5} {'ACTION':12} {'TARGET':28} {'OK':3} USER")
    for e in events:
        ts = e["timestamp"][:19].replace("T", " ")
        ok = "✓" if e["success"] else "✗"
        click.echo(
            f"{ts:20} {e['source']:5} {e['action']:12} {(e['target'] or '—')[:28]:28} "
            f"{ok:3} {e['user'] or '—'}"
        )


@cli.command()
@click.argument("dest", type=click.Path(dir_okay=False, writable=True))
@click.pass_context
@_handle
def backup(ctx, dest):
    """Descarga un backup light (db.sqlite3 + .env del kernel + .env de plugins)."""
    n = _client(ctx).backup_download(dest)
    click.secho(f"✓ Backup guardado en {dest} ({n // 1024} KiB)", fg="green")


@cli.command()
@click.argument("src", type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option("--apply", "apply_now", is_flag=True, help="Aplicar el restore tras stagear (requiere reiniciar el kernel).")
@click.pass_context
@_handle
def restore(ctx, src, apply_now):
    """Sube un backup al kernel y opcionalmente lo aplica."""
    client = _client(ctx)
    staged = client.restore_upload(src)
    meta = staged.get("metadata", {})
    click.secho(
        f"✓ Stage OK. Kernel v{meta.get('kernel_version','?')}, "
        f"creado {meta.get('created_at')}",
        fg="green",
    )
    if not apply_now:
        click.echo("(stage sin aplicar; pasa --apply para sobrescribir el sistema en vivo)")
        return
    applied = client.restore_apply()
    click.secho(f"✓ Restore aplicado: {', '.join(applied.get('applied', []))}", fg="green")
    click.secho("⚠ " + applied.get("warning", ""), fg="yellow")


@cli.command()
@click.argument("git_url")
@click.pass_context
@_handle
def download(ctx, git_url):
    """Clona un plugin desde una URL Git al kernel."""
    res = _client(ctx).marketplace_download(git_url)
    if res.get("downloaded"):
        click.secho(f"✓ {res['folder_name']} descargado.", fg="green")
    else:
        click.secho("✗ Descarga falló o manifest inválido.", fg="red")
        sys.exit(1)


if __name__ == "__main__":
    cli(obj={})
