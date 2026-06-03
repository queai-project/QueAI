"""
Endpoints REST del kernel — /api/v1/.

Reutilizan los helpers ya probados de module_manager.views y marketplace.views
para no duplicar la lógica de Docker. Cada endpoint devuelve JSON con códigos
HTTP estándar (200/201/202/400/401/403/404/409/500).
"""

from __future__ import annotations

import json
import shutil
import subprocess

import requests
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from marketplace.views import (
    _fetch_registry_plugins,
    _get_folder_name_from_git_url,
    _is_remote_version_newer,
    _load_local_manifest,
)
from module_manager.models import AvailableApp
from module_manager.views import (
    _compose_down_full,
    _delete_plugin_folder,
    _get_compose_command,
    _invalidate_running_cache,
    _is_app_running_cached,
    get_compose_path,
)

from .auth import api_token_required
from .openapi import build_schema
from .serializers import plugin_to_dict


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _get_app_or_404(identifier: str) -> AvailableApp | None:
    """Busca por folder_name (`QueAI-OCR-CPU-LOCAL-MS`) o slug (`ocr_local_cpu`).

    `queai list` muestra el slug corto, así que cualquier comando que el
    usuario escriba a partir de esa salida debe resolver al mismo plugin.
    """
    try:
        return AvailableApp.objects.get(folder_name=identifier)
    except AvailableApp.DoesNotExist:
        try:
            return AvailableApp.objects.get(name=identifier)
        except AvailableApp.DoesNotExist:
            return None


def _not_found(detail: str = "Plugin no encontrado.") -> JsonResponse:
    return JsonResponse({"error": "not_found", "detail": detail}, status=404)


def _bad_request(detail: str) -> JsonResponse:
    return JsonResponse({"error": "bad_request", "detail": detail}, status=400)


def _server_error(detail: str) -> JsonResponse:
    return JsonResponse({"error": "internal", "detail": detail}, status=500)


def _ok(data: dict, status: int = 200) -> JsonResponse:
    return JsonResponse(data, status=status)


# ----------------------------------------------------------------------------
# OpenAPI / Swagger UI
# ----------------------------------------------------------------------------
@require_GET
def openapi_schema(request: HttpRequest):
    """OpenAPI 3 schema. Público para que la CLI/IDE lo lean sin token."""
    return JsonResponse(build_schema())


@require_GET
def docs_ui(request: HttpRequest):
    """Swagger UI cargado desde unpkg. No requiere npm ni archivos estáticos."""
    from django.shortcuts import render

    return render(request, "api_docs.html")


# ----------------------------------------------------------------------------
# Meta
# ----------------------------------------------------------------------------
@require_GET
def health(request: HttpRequest):
    """Sin auth. Mismo contrato que /health pero bajo /api/v1/."""
    try:
        plugins_count = AvailableApp.objects.count()
        db_ok = True
    except Exception:
        plugins_count = None
        db_ok = False
    return JsonResponse(
        {
            "status": "ok" if db_ok else "degraded",
            "version": settings.QUEAI_VERSION or "unknown",
            "plugins": plugins_count,
        },
        status=200 if db_ok else 503,
    )


# ----------------------------------------------------------------------------
# Plugins / catálogo
# ----------------------------------------------------------------------------
@csrf_exempt
@api_token_required
@require_GET
def plugins_list(request: HttpRequest):
    apps = AvailableApp.objects.all().order_by("display_name")
    items = [
        plugin_to_dict(
            app,
            is_running=_is_app_running_cached(app.folder_name) if app.is_installed else False,
        )
        for app in apps
    ]
    return _ok({"plugins": items, "count": len(items)})


@csrf_exempt
@api_token_required
@require_GET
def plugin_detail(request: HttpRequest, folder_name: str):
    app = _get_app_or_404(folder_name)
    if app is None:
        return _not_found()
    is_running = _is_app_running_cached(app.folder_name) if app.is_installed else False
    return _ok(plugin_to_dict(app, is_running=is_running))


# ----------------------------------------------------------------------------
# Lifecycle
# ----------------------------------------------------------------------------
@csrf_exempt
@api_token_required
@require_POST
def plugin_install(request: HttpRequest, folder_name: str):
    app = _get_app_or_404(folder_name)
    if app is None:
        return _not_found()
    real = app.folder_name
    path = get_compose_path(real)
    try:
        subprocess.run(
            ["docker-compose", "-f", path, "up", "-d", "--build", "--force-recreate"],
            check=True,
        )
        AvailableApp.objects.filter(folder_name=real).update(is_installed=True)
        _invalidate_running_cache(real)
    except subprocess.CalledProcessError as e:
        return _server_error(f"docker compose up falló: {e}")
    return _ok({"status": "installed", "folder_name": real}, status=202)


@csrf_exempt
@api_token_required
@require_POST
def plugin_start(request: HttpRequest, folder_name: str):
    app = _get_app_or_404(folder_name)
    if app is None:
        return _not_found()
    real = app.folder_name
    path = get_compose_path(real)
    try:
        subprocess.run(_get_compose_command() + ["-f", path, "start"], check=True)
        _invalidate_running_cache(real)
    except subprocess.CalledProcessError as e:
        return _server_error(f"docker compose start falló: {e}")
    return _ok({"status": "started", "folder_name": real})


@csrf_exempt
@api_token_required
@require_POST
def plugin_stop(request: HttpRequest, folder_name: str):
    app = _get_app_or_404(folder_name)
    if app is None:
        return _not_found()
    real = app.folder_name
    path = get_compose_path(real)
    try:
        subprocess.run(_get_compose_command() + ["-f", path, "stop"], check=True)
        _invalidate_running_cache(real)
    except subprocess.CalledProcessError as e:
        return _server_error(f"docker compose stop falló: {e}")
    return _ok({"status": "stopped", "folder_name": real})


@csrf_exempt
@api_token_required
@require_POST
def plugin_uninstall(request: HttpRequest, folder_name: str):
    app = _get_app_or_404(folder_name)
    if app is None:
        return _not_found()
    real = app.folder_name
    path = get_compose_path(real)
    try:
        _compose_down_full(path)
        AvailableApp.objects.filter(folder_name=real).update(is_installed=False)
        _invalidate_running_cache(real)
    except Exception as e:
        return _server_error(str(e))
    return _ok({"status": "uninstalled", "folder_name": real})


@csrf_exempt
@api_token_required
@require_POST
def plugin_delete(request: HttpRequest, folder_name: str):
    app = _get_app_or_404(folder_name)
    if app is None:
        return _not_found()
    real = app.folder_name
    path = get_compose_path(real)
    try:
        _compose_down_full(path)
        AvailableApp.objects.filter(folder_name=real).delete()
        _delete_plugin_folder(real)
        _invalidate_running_cache(real)
    except Exception as e:
        return _server_error(str(e))
    return _ok({"status": "deleted", "folder_name": real})


# ----------------------------------------------------------------------------
# Logs / stats
# ----------------------------------------------------------------------------
@csrf_exempt
@api_token_required
@require_GET
def plugin_logs(request: HttpRequest, folder_name: str):
    app = _get_app_or_404(folder_name)
    if app is None:
        return _not_found()
    real = app.folder_name

    try:
        tail = int(request.GET.get("tail", "150"))
    except ValueError:
        return _bad_request("tail debe ser un entero.")
    tail = max(1, min(tail, 2000))

    path = get_compose_path(real)
    try:
        res = subprocess.run(
            _get_compose_command() + ["-f", path, "logs", f"--tail={tail}"],
            capture_output=True,
            text=True,
        )
        return _ok({"folder_name": real, "tail": tail, "logs": res.stdout + res.stderr})
    except Exception as e:
        return _server_error(str(e))


@csrf_exempt
@api_token_required
@require_GET
def plugin_stats(request: HttpRequest, folder_name: str):
    app = _get_app_or_404(folder_name)
    if app is None:
        return _not_found()
    real = app.folder_name
    try:
        ids_res = subprocess.run(
            [
                "docker", "ps",
                "--filter", f"label=com.docker.compose.project={real.lower()}",
                "--format", "{{.ID}}",
            ],
            capture_output=True, text=True,
        )
        container_ids = [c for c in ids_res.stdout.strip().splitlines() if c.strip()]
        if not container_ids:
            return _ok({"folder_name": real, "containers": []})

        stats_res = subprocess.run(
            [
                "docker", "stats", "--no-stream",
                "--format",
                '{"id":"{{.ID}}","cpu":"{{.CPUPerc}}","mem":"{{.MemUsage}}","net":"{{.NetIO}}"}',
                *container_ids,
            ],
            capture_output=True, text=True,
        )
        stats = [json.loads(line) for line in stats_res.stdout.strip().splitlines() if line.strip()]
        return _ok({"folder_name": real, "containers": stats})
    except Exception as e:
        return _server_error(str(e))


# ----------------------------------------------------------------------------
# .env (read / write)
# ----------------------------------------------------------------------------
@csrf_exempt
@api_token_required
@require_http_methods(["GET", "PUT"])
def plugin_env(request: HttpRequest, folder_name: str):
    import os

    app = _get_app_or_404(folder_name)
    if app is None:
        return _not_found()
    real = app.folder_name

    plugin_path = os.path.join(settings.PLUGINS_DIR, real)
    env_path = os.path.join(plugin_path, ".env")
    example_path = os.path.join(plugin_path, ".env.example")

    if request.method == "GET":
        if not os.path.exists(env_path):
            try:
                if os.path.exists(example_path):
                    shutil.copyfile(example_path, env_path)
                else:
                    with open(env_path, "w", encoding="utf-8") as f:
                        f.write("# Configuración del Módulo\n# Define tus variables aquí (KEY=VALUE)\n")
            except Exception as e:
                return _server_error(f"No se pudo crear .env: {e}")
        try:
            with open(env_path, encoding="utf-8") as f:
                return _ok({"folder_name": real, "content": f.read()})
        except Exception as e:
            return _server_error(str(e))

    # PUT
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return _bad_request("Body debe ser JSON válido.")

    content = payload.get("content")
    apply_now = bool(payload.get("apply", True))
    if content is None:
        return _bad_request("Falta campo 'content' (string).")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        return _server_error(f"Error escribiendo .env: {e}")

    if apply_now and os.path.exists(get_compose_path(real)):
        try:
            subprocess.run(
                _get_compose_command() + ["-f", get_compose_path(real), "up", "-d", "--force-recreate"],
                check=True,
            )
            _invalidate_running_cache(real)
        except subprocess.CalledProcessError as e:
            return _server_error(f".env guardado pero falló el recreate: {e}")

    return _ok({"folder_name": real, "applied": apply_now})


# ----------------------------------------------------------------------------
# Marketplace
# ----------------------------------------------------------------------------
@csrf_exempt
@api_token_required
@require_GET
def marketplace_list(request: HttpRequest):
    try:
        remote = _fetch_registry_plugins()
    except requests.RequestException as e:
        return _server_error(f"Registry no disponible: {e}")

    enriched = []
    for plugin in remote:
        git_url = plugin.get("git_url", "")
        folder = _get_folder_name_from_git_url(git_url)
        local = _load_local_manifest(folder)
        entry = {**plugin, "folder_name": folder, "is_downloaded": False, "local_version": None, "is_update_available": False}
        if local:
            local_v = local.get("version", "0.0.0")
            entry["is_downloaded"] = True
            entry["local_version"] = local_v
            entry["is_update_available"] = _is_remote_version_newer(local_v, plugin.get("version", "0.0.0"))
        enriched.append(entry)
    return _ok({"plugins": enriched, "count": len(enriched)})


@csrf_exempt
@api_token_required
@require_POST
def marketplace_download(request: HttpRequest):
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return _bad_request("Body debe ser JSON válido.")

    git_url = (payload.get("git_url") or "").strip()
    if not git_url:
        return _bad_request("Falta 'git_url' en el body.")

    # Delegamos al flujo existente de marketplace.views.download_plugin
    # construyendo un POST artificial — más adelante extraemos la lógica común.
    from django.http import QueryDict

    from marketplace.views import download_plugin

    fake_post = QueryDict(mutable=True)
    fake_post["git_url"] = git_url
    request._post = fake_post  # type: ignore[attr-defined]
    request.method = "POST"

    try:
        download_plugin(request)
    except Exception as e:
        return _server_error(str(e))

    folder = _get_folder_name_from_git_url(git_url)
    manifest = _load_local_manifest(folder)
    return _ok(
        {
            "folder_name": folder,
            "downloaded": bool(manifest),
            "manifest": manifest,
        },
        status=201 if manifest else 500,
    )
