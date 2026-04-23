import json
import os
import shutil
import subprocess

from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import AvailableApp


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
        with open(manifest_path, "r", encoding="utf-8") as f:
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


def get_apps(request):
    """
    Sincroniza disco con BD usando SOLO plugins válidos:
    - Deben tener manifest.json válido
    - Deben tener docker-compose.yml
    Las carpetas vacías o corruptas no aparecen en el hub.
    """
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

            if _is_app_running(compose_path):
                defaults["is_installed"] = True

            AvailableApp.objects.update_or_create(name=app_name, defaults=defaults)

        AvailableApp.objects.exclude(name__in=manifest_names).delete()

    apps = AvailableApp.objects.all().order_by("display_name")
    for app in apps:
        app.is_running = False
        if app.is_installed:
            app.is_running = _is_app_running(get_compose_path(app.folder_name))

    return render(request, "module_manager.html", {"apps": apps})


@require_POST
def install_app(request):
    folder = request.POST.get("manifest_folder_name")
    path = get_compose_path(folder)
    try:
        subprocess.run(
            ["docker-compose", "-f", path, "up", "-d", "--build", "--force-recreate"],
            check=True
        )
        AvailableApp.objects.filter(folder_name=folder).update(is_installed=True)
        messages.success(request, f"Módulo {folder} instalado y activado.")
    except Exception as e:
        messages.error(request, f"Error al instalar: {str(e)}")
    return redirect("get_apps")

@require_POST
def start_app(request):
    folder = request.POST.get("manifest_folder_name")
    path = get_compose_path(folder)
    try:
        compose_cmd = _get_compose_command()
        subprocess.run(compose_cmd + ["-f", path, "start"], check=True)
        messages.success(request, f"Módulo {folder} reanudado.")
    except Exception as e:
        messages.error(request, f"Error al iniciar: {str(e)}")
    return redirect("get_apps")


@require_POST
def stop_app(request):
    folder = request.POST.get("manifest_folder_name")
    path = get_compose_path(folder)
    try:
        compose_cmd = _get_compose_command()
        subprocess.run(compose_cmd + ["-f", path, "stop"], check=True)
        messages.info(request, f"Módulo {folder} detenido.")
    except Exception as e:
        messages.error(request, f"Error al detener: {str(e)}")
    return redirect("get_apps")


@require_POST
def uninstall_app(request):
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

        messages.warning(request, f"Módulo {folder} eliminado completamente del sistema.")
    except Exception as e:
        messages.error(request, f"Error al eliminar el módulo: {str(e)}")
    return redirect("get_apps")


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
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        return JsonResponse({"status": "ok", "content": content})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})


@require_POST
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
            messages.success(request, f"Configuración de {folder_name} actualizada y aplicada.")

        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})