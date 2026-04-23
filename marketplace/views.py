import json
import os
import platform
import re
import shutil
import subprocess
import time
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from module_manager.models import AvailableApp

REGISTRY_URL = "https://raw.githubusercontent.com/queai-project/QueAI-Registry/refs/heads/main/register.json"


def _get_compose_command():
    """
    Devuelve el comando disponible para Docker Compose.
    Prioriza 'docker-compose' por compatibilidad con tu código actual.
    """
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    if shutil.which("docker"):
        return ["docker", "compose"]
    raise RuntimeError("No se encontró 'docker-compose' ni 'docker compose'.")


def _safe_version_tuple(version):
    """
    Convierte una versión en una tupla comparable.
    Ej: '1.1.4' -> (1, 1, 4)
    Ignora texto no numérico.
    """
    if not version:
        return (0,)
    parts = re.findall(r"\d+", str(version))
    if not parts:
        return (0,)
    return tuple(int(p) for p in parts)


def _is_remote_version_newer(local_version, remote_version):
    return _safe_version_tuple(remote_version) > _safe_version_tuple(local_version)


def _get_folder_name_from_git_url(git_url):
    return git_url.rstrip("/").split("/")[-1].replace(".git", "")


def _get_plugin_paths(folder_name):
    plugin_path = os.path.join(settings.PLUGINS_DIR, folder_name)
    manifest_path = os.path.join(plugin_path, "manifest.json")
    compose_path = os.path.join(plugin_path, "docker-compose.yml")
    return plugin_path, manifest_path, compose_path


def _load_local_manifest(folder_name):
    """
    Retorna el manifest local si existe y es válido.
    Si la carpeta existe pero no hay manifest, retorna None.
    """
    _, manifest_path, _ = _get_plugin_paths(folder_name)
    if not os.path.isfile(manifest_path):
        return None
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _fetch_registry_plugins():
    """
    Fuerza lectura fresca del registry en cada llamada.
    Se añade cache-busting por querystring y headers no-cache.
    """
    cache_buster = urlencode({"_ts": str(time.time_ns())})
    url = f"{REGISTRY_URL}?{cache_buster}"

    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    response = requests.get(url, headers=headers, timeout=8)
    response.raise_for_status()

    data = response.json()
    return data.get("plugins", []) if isinstance(data, dict) else data


def _compose_down_full(compose_path):
    """
    Hace down completo del módulo, limpiando imágenes, volúmenes y huérfanos.
    No lanza error si el compose no existe.
    """
    if not os.path.isfile(compose_path):
        return

    compose_cmd = _get_compose_command()
    subprocess.run(
        compose_cmd + [
            "-f",
            compose_path,
            "down",
            "--rmi",
            "all",
            "--volumes",
            "--remove-orphans",
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def _cleanup_existing_plugin_installation(folder_name):
    """
    Si existe un docker-compose del módulo, hace down total con limpieza.
    Luego marca el módulo como no instalado y elimina completamente la carpeta.
    """
    plugin_path, _, compose_path = _get_plugin_paths(folder_name)

    # Baja y limpia contenedores/imágenes/volúmenes/orphans
    _compose_down_full(compose_path)

    # Refleja que ya no está instalado mientras se reemplaza
    AvailableApp.objects.filter(folder_name=folder_name).update(is_installed=False)

    # Elimina completamente la carpeta local
    if os.path.exists(plugin_path):
        shutil.rmtree(plugin_path, ignore_errors=False)


def marketplace(request):
    """Muestra los plugins disponibles en la nube con estado real local."""
    remote_plugins = []

    try:
        remote_plugins = _fetch_registry_plugins()
    except Exception:
        messages.error(
            request,
            "No se pudo conectar con el Marketplace. Verifica tu conexión a internet."
        )
        remote_plugins = []

    for plugin in remote_plugins:
        git_url = plugin.get("git_url", "")
        folder_name = _get_folder_name_from_git_url(git_url)
        local_manifest = _load_local_manifest(folder_name)

        plugin["folder_name"] = folder_name
        plugin["is_downloaded"] = False
        plugin["is_update_available"] = False
        plugin["local_version"] = None

        # Solo cuenta como descargado si existe manifest.json válido
        if local_manifest:
            local_version = local_manifest.get("version", "0.0.0")
            remote_version = plugin.get("version", "0.0.0")

            plugin["is_downloaded"] = True
            plugin["local_version"] = local_version
            plugin["is_update_available"] = _is_remote_version_newer(
                local_version,
                remote_version,
            )

    response = render(request, "marketplace.html", {"remote_plugins": remote_plugins})

    # Evita cache del lado navegador/proxy para que la pantalla se refresque de verdad
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"

    return response


@require_POST
def download_plugin(request):
    """
    Descarga o actualiza un plugin desde Git.
    Reglas:
    - Si la carpeta existe pero no tiene manifest.json, NO se considera descargado.
      Se limpia y se vuelve a clonar.
    - Si el módulo ya existe con manifest:
        - si la versión remota es mayor, se actualiza
        - si no, se informa que ya está actualizado
    - Antes de descargar/actualizar:
        - docker compose down --rmi all --volumes --remove-orphans
        - se borra la carpeta local
    """
    git_url = (request.POST.get("git_url") or "").strip()
    if not git_url:
        messages.error(request, "No se recibió una URL de Git válida.")
        return redirect("marketplace")

    folder_name = _get_folder_name_from_git_url(git_url)
    plugin_path, _, _ = _get_plugin_paths(folder_name)
    local_manifest = _load_local_manifest(folder_name)

    remote_version = None
    try:
        remote_plugins = _fetch_registry_plugins()
        for plugin in remote_plugins:
            if plugin.get("git_url") == git_url:
                remote_version = plugin.get("version")
                break
    except Exception:
        # Si falla el registry, permitimos descarga manual igualmente
        remote_version = None

    try:
        # Caso 1: existe manifest local válido
        if local_manifest:
            local_version = local_manifest.get("version", "0.0.0")

            if remote_version and not _is_remote_version_newer(local_version, remote_version):
                messages.info(
                    request,
                    f"El módulo '{folder_name}' ya está descargado y actualizado (v{local_version})."
                )
                return redirect("marketplace")

            # Hay que actualizar: bajar y limpiar como una desinstalación fuerte
            _cleanup_existing_plugin_installation(folder_name)
            action_label = "actualizado"

        else:
            # Caso 2: carpeta vacía, corrupta o incompleta
            if os.path.exists(plugin_path):
                _cleanup_existing_plugin_installation(folder_name)
            action_label = "descargado"

        host_base_path = os.environ.get("HOST_PROJECT_PATH")
        user_id = os.environ.get("HOST_UID")
        group_id = os.environ.get("HOST_GID")

        if not host_base_path:
            raise RuntimeError(
                "No está definida la variable de entorno HOST_PROJECT_PATH."
            )

        host_plugins_path = f"{host_base_path}/plugins"

        command = ["docker", "run", "--rm"]

        if user_id and group_id and platform.system() != "Windows":
            command += ["--user", f"{user_id}:{group_id}"]

        command += [
            "-v",
            f"{host_plugins_path}:/data",
            "alpine/git",
            "clone",
            git_url,
            f"/data/{folder_name}",
        ]

        subprocess.run(command, check=True)

        new_manifest = _load_local_manifest(folder_name)
        if not new_manifest:
            raise RuntimeError(
                f"El repositorio '{folder_name}' fue clonado pero no contiene un manifest.json válido."
            )

        # Dejamos el registro en estado no instalado hasta que el usuario lo instale/reanude desde el Hub
        AvailableApp.objects.filter(folder_name=folder_name).update(is_installed=False)

        messages.success(request, f"Módulo '{folder_name}' {action_label} con éxito.")

    except Exception as e:
        messages.error(request, f"Error al descargar/actualizar: {str(e)}")
        print(f"DEBUG Error: {str(e)}")

    return redirect("marketplace")