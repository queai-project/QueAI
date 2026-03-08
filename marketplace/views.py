import requests
import os
import subprocess
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
import platform

# Tu URL oficial de GitHub
REGISTRY_URL = "https://raw.githubusercontent.com/queai-project/QueAI-Registry/refs/heads/main/register.json"

def marketplace(request):
    """Muestra los plugins disponibles en la nube."""
    remote_plugins = []
    try:
        response = requests.get(REGISTRY_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Si el JSON es {"plugins": [...]}, extraemos la lista. Si es lista directa, la usamos.
            remote_plugins = data.get('plugins', []) if isinstance(data, dict) else data
    except Exception as e:
        messages.error(request, f"No se pudo conectar con el Marketplace: {e}")

    # Escaneamos carpetas locales para saber qué módulos ya han sido descargados
    downloaded_folders = []
    if os.path.exists(settings.PLUGINS_DIR):
        downloaded_folders = os.listdir(settings.PLUGINS_DIR)
    
    # Marcamos cada plugin remoto como 'ya_descargado' si su carpeta existe
    for plugin in remote_plugins:
        # Asumimos que la carpeta se llamará como el final de la git_url
        folder_name = plugin['git_url'].split('/')[-1].replace('.git', '')
        plugin['is_downloaded'] = folder_name in downloaded_folders

    return render(request, "marketplace.html", {"remote_plugins": remote_plugins})

@require_POST
def download_plugin(request):
    git_url = request.POST.get("git_url")
    folder_name = git_url.split('/')[-1].replace('.git', '')
    
    # 1. Ruta interna (la que Django ve para verificar si existe)
    target_path_internal = os.path.join(settings.PLUGINS_DIR, folder_name)

    if os.path.exists(target_path_internal):
        messages.warning(request, "El código de este módulo ya se encuentra en el sistema.")
        return redirect("marketplace")

    try:
        host_base_path = os.environ.get('HOST_PROJECT_PATH')
        user_id = os.environ.get('HOST_UID')
        group_id = os.environ.get('HOST_GID')
        
        host_plugins_path = f"{host_base_path}/plugins"

        # Comando base
        command = ["docker", "run", "--rm"]

        # SOLO añadimos el usuario si estamos en Linux (donde UID suele existir)
        # En Windows, omitimos esto para que Docker Desktop maneje los permisos
        if user_id and group_id and platform.system() != "Windows":
            command += ["--user", f"{user_id}:{group_id}"]

        # Añadimos el resto del comando
        command += [
            "-v", f"{host_plugins_path}:/data",
            "alpine/git",
            "clone", git_url, f"/data/{folder_name}"
        ]
        
        subprocess.run(command, check=True)
        messages.success(request, f"Módulo '{folder_name}' descargado con éxito.")
        
    except Exception as e:
        messages.error(request, f"Error al descargar: {str(e)}")
        print(f"DEBUG Error: {str(e)}")
        
    return redirect("get_apps")
