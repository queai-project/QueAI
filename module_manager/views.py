import json
import os
import shutil
import subprocess

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.audit import record as audit_record

from .models import AvailableApp

RUNNING_CACHE_TTL = 5  # segundos
RUNNING_CACHE_PREFIX = "queai:running:"


def _invalidate_running_cache(folder_name: str | None = None):
    """Invalida el cache de estado running. Sin argumento invalida todo."""
    if folder_name is None:
        cache.clear()
    else:
        cache.delete(f"{RUNNING_CACHE_PREFIX}{folder_name}")


def _is_app_running_cached(folder_name: str) -> bool:
    """Lookup cacheado de `_is_app_running` por folder_name."""
    key = f"{RUNNING_CACHE_PREFIX}{folder_name}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    compose_path = get_compose_path(folder_name)
    state = _is_app_running(compose_path)
    cache.set(key, state, RUNNING_CACHE_TTL)
    return state


def _get_compose_command():
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    if shutil.which("docker"):
        return ["docker", "compose"]
    raise RuntimeError("No se encontró 'docker-compose' ni 'docker compose'.")


def get_compose_path(folder_name):
    return os.path.join(settings.PLUGINS_DIR, folder_name, "docker-compose.yml")


def get_manifest_path(folder_name):
    return os.path.join(settings.PLUGINS_DIR, folder_name, "manifest.json")


def get_plugin_path(folder_name):
    return os.path.join(settings.PLUGINS_DIR, folder_name)


def _load_manifest(folder_name):
    manifest_path = get_manifest_path(folder_name)
    if not os.path.isfile(manifest_path):
        return None
    try:
        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _is_app_running(compose_path):
    """Verifica si los contenedores asociados a un compose están activos."""
    if not os.path.exists(compose_path):
        return False

    try:
        compose_cmd = _get_compose_command()
        res = subprocess.run(
            compose_cmd + ["-f", compose_path, "top"],
            capture_output=True,
            text=True
        )
        return res.returncode == 0 and len(res.stdout.strip().split("\n")) > 1
    except Exception:
        return False

def _run_command(command):
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _docker_ids_by_label(resource_type, label):
    """
    Devuelve IDs de recursos Docker filtrados por label.
    resource_type: container | network | volume | image
    """
    resource_map = {
        "container": ["docker", "ps", "-aq", "--filter", f"label={label}"],
        "network": ["docker", "network", "ls", "-q", "--filter", f"label={label}"],
        "volume": ["docker", "volume", "ls", "-q", "--filter", f"label={label}"],
        "image": ["docker", "image", "ls", "-q", "--filter", f"label={label}"],
    }

    cmd = resource_map.get(resource_type)
    if not cmd:
        return []

    res = _run_command(cmd)
    if res.returncode != 0:
        return []

    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def _cleanup_missing_plugin_docker_artifacts(folder_name):
    """
    Limpia recursos Docker de un módulo aunque ya no exista su docker-compose.yml,
    apoyándose en el nombre de proyecto que Compose genera en labels.

    Esto intenta eliminar:
    - contenedores
    - redes
    - volúmenes
    - imágenes
    """
    project_candidates = _compose_project_candidates(folder_name)

    container_ids = set()
    network_ids = set()
    volume_ids = set()
    image_ids = set()

    for project_name in project_candidates:
        label = f"com.docker.compose.project={project_name}"

        for cid in _docker_ids_by_label("container", label):
            container_ids.add(cid)

        for nid in _docker_ids_by_label("network", label):
            network_ids.add(nid)

        for vid in _docker_ids_by_label("volume", label):
            volume_ids.add(vid)

        for iid in _docker_ids_by_label("image", label):
            image_ids.add(iid)

    # Extraer imágenes reales desde los contenedores encontrados
    image_ids.update(_docker_image_ids_from_containers(container_ids))

    # 1) Contenedores
    if container_ids:
        _run_command(["docker", "rm", "-f", *sorted(container_ids)])

    # 2) Redes
    if network_ids:
        _run_command(["docker", "network", "rm", *sorted(network_ids)])

    # 3) Volúmenes
    if volume_ids:
        _run_command(["docker", "volume", "rm", "-f", *sorted(volume_ids)])

    # 4) Imágenes
    if image_ids:
        _run_command(["docker", "rmi", "-f", *sorted(image_ids)])



def _compose_down_full(compose_path):
    """
    Hace down completo del módulo, limpiando contenedores, imágenes,
    volúmenes y huérfanos relacionados con ese docker compose.
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
        check=True,
    )


def _delete_plugin_folder(folder_name):
    plugin_path = get_plugin_path(folder_name)
    if os.path.exists(plugin_path):
        shutil.rmtree(plugin_path, ignore_errors=False)


def plugin_logo(request, plugin_name, filename):
    """Sirve el logo del plugin limpiando rutas redundantes."""
    clean_name = filename.split("/")[-1]
    logo_path = os.path.join(settings.PLUGINS_DIR, plugin_name, "assets", clean_name)
    if os.path.exists(logo_path):
        return FileResponse(open(logo_path, "rb"), content_type="image/png")
    raise Http404("Logo no encontrado")


@login_required
def get_apps(request):
    """
    Sincroniza disco con BD usando SOLO plugins válidos:
    - Deben tener manifest.json válido
    - Deben tener docker-compose.yml
    Las carpetas vacías o corruptas no aparecen en el hub.

    Además, si un módulo existía en BD pero desapareció del directorio,
    se intentan limpiar sus recursos Docker asociados.
    """
    # Onboarding: si el catálogo está vacío y el usuario no descartó el wizard,
    # mandamos a /welcome/ para guiar el primer arranque.
    if not request.session.get("welcome_dismissed") and not AvailableApp.objects.exists():
        return redirect("welcome")

    plugins_dir = settings.PLUGINS_DIR

    if os.path.isdir(plugins_dir):
        manifest_names = set()

        for folder in os.listdir(plugins_dir):
            compose_path = get_compose_path(folder)
            manifest = _load_manifest(folder)

            if not os.path.isfile(compose_path):
                continue
            if not manifest:
                continue

            app_name = manifest.get("name")
            if not app_name:
                continue

            manifest_names.add(app_name)

            defaults = {
                "folder_name": folder,
                "display_name": manifest.get("display_name", app_name),
                "author": manifest.get("author", ""),
                "ui_entry_point": manifest.get("ui_entry_point", ""),
                "configuration_entry_point": manifest.get("configuration_entry_point", ""),
                "documentation_entry_point": manifest.get("documentation_entry_point", ""),
                "version": manifest.get("version", "1.0.0"),
                "description": manifest.get("description", ""),
                "logo": manifest.get("logo", "logo.png"),
                "lic": manifest.get("license", ""),
            }

            if _is_app_running_cached(folder):
                defaults["is_installed"] = True

            AvailableApp.objects.update_or_create(name=app_name, defaults=defaults)

        # Detectar módulos que estaban en BD pero ya no existen en disco
        missing_apps = list(AvailableApp.objects.exclude(name__in=manifest_names))

        for app in missing_apps:
            try:
                if app.folder_name:
                    _cleanup_missing_plugin_docker_artifacts(app.folder_name)
            except Exception as e:
                print(f"DEBUG cleanup missing plugin '{app.folder_name}': {e}")

        # Luego sí eliminamos los registros huérfanos de la BD
        AvailableApp.objects.exclude(name__in=manifest_names).delete()

    apps = AvailableApp.objects.all().order_by("display_name")
    for app in apps:
        app.is_running = False
        if app.is_installed:
            app.is_running = _is_app_running_cached(app.folder_name)

    return render(
        request,
        "module_manager.html",
        {
            "apps": apps,
            "queai_version": getattr(settings, "QUEAI_VERSION", ""),
        },
    )


def _compose_project_candidates(folder_name):
    """
    Genera posibles nombres de proyecto de Docker Compose a partir del nombre
    de la carpeta del plugin.
    """
    raw = (folder_name or "").strip()
    candidates = []

    for value in [
        raw,
        raw.lower(),
        raw.replace("_", "-").lower(),
    ]:
        if value and value not in candidates:
            candidates.append(value)

    return candidates


def _docker_image_ids_from_containers(container_ids):
    """
    Extrae los image IDs reales asociados a una lista de contenedores.
    """
    image_ids = set()

    for container_id in container_ids:
        res = _run_command(["docker", "inspect", "--format", "{{.Image}}", container_id])
        if res.returncode == 0:
            image_id = res.stdout.strip()
            if image_id:
                image_ids.add(image_id)

    return image_ids


@login_required
@require_POST
@audit_record("install", source="ui")
def install_app(request):
    folder = request.POST.get("manifest_folder_name")
    path = get_compose_path(folder)
    try:
        subprocess.run(
            ["docker-compose", "-f", path, "up", "-d", "--build", "--force-recreate"],
            check=True
        )
        AvailableApp.objects.filter(folder_name=folder).update(is_installed=True)
        _invalidate_running_cache(folder)
        messages.success(request, f"Módulo {folder} instalado y activado.")
    except Exception as e:
        messages.error(request, f"Error al instalar: {str(e)}")
    return redirect("get_apps")

@login_required
@require_POST
@audit_record("start", source="ui")
def start_app(request):
    folder = request.POST.get("manifest_folder_name")
    path = get_compose_path(folder)
    try:
        compose_cmd = _get_compose_command()
        subprocess.run(compose_cmd + ["-f", path, "start"], check=True)
        _invalidate_running_cache(folder)
        messages.success(request, f"Módulo {folder} reanudado.")
    except Exception as e:
        messages.error(request, f"Error al iniciar: {str(e)}")
    return redirect("get_apps")


@login_required
@require_POST
@audit_record("stop", source="ui")
def stop_app(request):
    folder = request.POST.get("manifest_folder_name")
    path = get_compose_path(folder)
    try:
        compose_cmd = _get_compose_command()
        subprocess.run(compose_cmd + ["-f", path, "stop"], check=True)
        _invalidate_running_cache(folder)
        messages.info(request, f"Módulo {folder} detenido.")
    except Exception as e:
        messages.error(request, f"Error al detener: {str(e)}")
    return redirect("get_apps")

@login_required
@require_POST
@audit_record("uninstall", source="ui")
def uninstall_app(request):
    """
    Desinstala el módulo pero NO borra su carpeta local.
    El módulo seguirá apareciendo en el Hub como disponible/sin instalar.
    """
    folder = request.POST.get("manifest_folder_name")
    path = get_compose_path(folder)

    try:
        if os.path.exists(path):
            _compose_down_full(path)

        AvailableApp.objects.filter(folder_name=folder).update(is_installed=False)
        _invalidate_running_cache(folder)
        messages.warning(request, f"Módulo {folder} desinstalado.")
    except Exception as e:
        messages.error(request, f"Error al desinstalar el módulo: {str(e)}")
    return redirect("get_apps")

@login_required
@require_POST
@audit_record("delete", source="ui")
def delete_app(request):
    """
    Borra completamente el módulo desde el Hub:
    - tumba el compose
    - elimina contenedores, imágenes, volúmenes y orphans del compose
    - elimina el registro de la BD
    - elimina la carpeta completa del plugin
    """
    folder = request.POST.get("manifest_folder_name")
    path = get_compose_path(folder)

    try:
        if os.path.exists(path):
            _compose_down_full(path)

        AvailableApp.objects.filter(folder_name=folder).delete()
        _delete_plugin_folder(folder)
        _invalidate_running_cache(folder)

        messages.warning(request, f"Módulo {folder} eliminado completamente del sistema.")
    except Exception as e:
        messages.error(request, f"Error al eliminar el módulo: {str(e)}")
    return redirect("get_apps")


@login_required
def app_detail(request, folder_name):
    """Página de detalle por plugin: tabs Overview / .env / Logs."""
    from django.http import Http404

    try:
        app = AvailableApp.objects.get(folder_name=folder_name)
    except AvailableApp.DoesNotExist as err:
        raise Http404("Plugin no encontrado") from err

    app.is_running = False
    if app.is_installed:
        app.is_running = _is_app_running_cached(folder_name)

    return render(
        request,
        "module_detail.html",
        {"app": app},
    )


@login_required
def app_logs_stream(request, folder_name):
    """Stream SSE de logs con auth de sesión (UI consume esto)."""
    from core.api.views import make_sse_response, stream_logs

    try:
        app = AvailableApp.objects.get(folder_name=folder_name)
    except AvailableApp.DoesNotExist:
        try:
            app = AvailableApp.objects.get(name=folder_name)
        except AvailableApp.DoesNotExist:
            return JsonResponse({"error": "not_found"}, status=404)

    try:
        tail = max(1, min(int(request.GET.get("tail", "50")), 500))
    except ValueError:
        tail = 50
    return make_sse_response(stream_logs(app.folder_name, tail=tail))


@login_required
def app_healthcheck(request, folder_name):
    """Healthcheck del plugin para consumo desde la UI (sesión Django)."""
    from core.api.views import _compute_healthcheck

    try:
        app = AvailableApp.objects.get(folder_name=folder_name)
    except AvailableApp.DoesNotExist:
        try:
            app = AvailableApp.objects.get(name=folder_name)
        except AvailableApp.DoesNotExist:
            return JsonResponse({"error": "not_found"}, status=404)

    return JsonResponse(_compute_healthcheck(app))


@login_required
def app_logs(request, folder_name):
    path = get_compose_path(folder_name)
    try:
        compose_cmd = _get_compose_command()
        res = subprocess.run(
            compose_cmd + ["-f", path, "logs", "--tail=150"],
            capture_output=True,
            text=True
        )
        return JsonResponse({"status": "ok", "logs": res.stdout + res.stderr})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})


@login_required
def get_env_config(request, folder_name):
    """Lee el .env, clonando el .env.example si es la primera vez."""
    plugin_path = os.path.join(settings.PLUGINS_DIR, folder_name)
    env_path = os.path.join(plugin_path, ".env")
    example_path = os.path.join(plugin_path, ".env.example")

    if not os.path.exists(env_path):
        try:
            if os.path.exists(example_path):
                shutil.copyfile(example_path, env_path)
            else:
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write("# Configuración del Módulo\n# Define tus variables aquí (KEY=VALUE)\n")
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Error de permisos al crear .env: {str(e)}"})

    try:
        with open(env_path, encoding="utf-8") as f:
            content = f.read()
        return JsonResponse({"status": "ok", "content": content})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})


@login_required
@require_POST
@audit_record("save_env", source="ui")
def save_env_config(request):
    """Guarda el .env y aplica cambios recreando el contenedor."""
    folder_name = request.POST.get("folder_name")
    content = request.POST.get("content")
    env_path = os.path.join(settings.PLUGINS_DIR, folder_name, ".env")
    path = get_compose_path(folder_name)

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)

        if os.path.exists(path):
            compose_cmd = _get_compose_command()
            subprocess.run(
                compose_cmd + ["-f", path, "up", "-d", "--force-recreate"],
                check=True
            )
            _invalidate_running_cache(folder_name)
            messages.success(request, f"Configuración de {folder_name} actualizada y aplicada.")

        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

@login_required
@require_POST
def refresh_catalog(request):
    """Invalida el cache de estado running para forzar un re-scan completo."""
    _invalidate_running_cache()
    return redirect("get_apps")
