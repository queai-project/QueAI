import os
import json
import subprocess
from django.shortcuts import render, redirect
from django.http import FileResponse, Http404, JsonResponse
from django.conf import settings
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import AvailableApp

# --- UTILIDADES ---
def get_compose_path(folder_name):
    return os.path.join(settings.PLUGINS_DIR, folder_name, 'docker-compose.yml')

# --- VISTAS ---

def plugin_logo(request, plugin_name, filename):
    """Sirve el logo del plugin limpiando rutas redundantes."""
    clean_name = filename.split('/')[-1] # Por si viene 'assets/logo.png'
    logo_path = os.path.join(settings.PLUGINS_DIR, plugin_name, 'assets', clean_name)
    print(f"{logo_path=}")
    if os.path.exists(logo_path):
        return FileResponse(open(logo_path, 'rb'), content_type="image/png")
    raise Http404("Logo no encontrado")

# --- UTILIDADES AUXILIARES ---
def _is_app_running(compose_path):
    """Verifica si los contenedores asociados a un compose están activos."""
    if not os.path.exists(compose_path):
        return False
    try:
        # Si 'top' devuelve salida (más allá de encabezados), hay procesos corriendo
        res = subprocess.run(
            ["docker-compose", "-f", compose_path, "top"], 
            capture_output=True, 
            text=True
        )
        return res.returncode == 0 and len(res.stdout.strip().split('\n')) > 1
    except Exception:
        return False

# --- VISTA GET_APPS OPTIMIZADA ---
def get_apps(request):
    """Sincroniza disco con BD y verifica estados en tiempo real."""
    plugins_dir = settings.PLUGINS_DIR
    
    # 1. Sincronización (Disco -> BD)
    if os.path.isdir(plugins_dir):
        manifest_names = set()
        
        for folder in os.listdir(plugins_dir):
            path = get_compose_path(folder)
            manifest_path = os.path.join(plugins_dir, folder, 'manifest.json')
            
            # Validaciones rápidas de existencia
            if not os.path.isfile(path):
                # print(f"Saltando {folder}: no existe docker-compose.yml") 
                continue 
            if not os.path.isfile(manifest_path):
                continue

            # Procesar Manifest
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    m = json.load(f)
                
                app_name = m.get('name')
                if not app_name: continue
                
                manifest_names.add(app_name)
                
                # Datos comunes para actualizar o crear
                defaults = {
                    'folder_name': folder,
                    'display_name': m.get('display_name', app_name),
                    'ui_entry_point': m.get('ui_entry_point', ''),
                    'documentation_entry_point': m.get('documentation_entry_point', ''),
                    'version': m.get('version', '1.0.0'),
                    'description': m.get('description', ''),
                    'logo': m.get('logo', 'logo.png'),
                }

                # Si detectamos que está corriendo, forzamos is_installed=True
                # Esto auto-detecta instalaciones manuales fuera de la UI
                if _is_app_running(path):
                    defaults['is_installed'] = True

                AvailableApp.objects.update_or_create(name=app_name, defaults=defaults)
                
            except (json.JSONDecodeError, OSError) as e:
                print(f"Error procesando plugin {folder}: {e}")

        # Limpieza: Eliminar de la BD registros que ya no existen en disco
        AvailableApp.objects.exclude(name__in=manifest_names).delete()

    # 2. Live Check (BD -> UI)
    # Solo verificamos el estado 'running' para visualización, sin escribir en BD
    apps = AvailableApp.objects.all().order_by('display_name')
    for app in apps:
        app.is_running = False
        # Solo gastamos recursos chequeando apps que creemos instaladas
        if app.is_installed:
            app.is_running = _is_app_running(get_compose_path(app.folder_name))

    return render(request, "apps.html", {"apps": apps})
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
        subprocess.run(["docker-compose", "-f", path, "start"], check=True)
        messages.success(request, f"Módulo {folder} reanudado.")
    except Exception as e:
        messages.error(request, f"Error al iniciar: {str(e)}")
    return redirect("get_apps")

@require_POST
def stop_app(request):
    folder = request.POST.get("manifest_folder_name")
    path = get_compose_path(folder)
    try:
        subprocess.run(["docker-compose", "-f", path, "stop"], check=True)
        messages.info(request, f"Módulo {folder} detenido.")
    except Exception as e:
        messages.error(request, f"Error al detener: {str(e)}")
    return redirect("get_apps")

@require_POST
def uninstall_app(request):
    folder = request.POST.get("manifest_folder_name")
    path = get_compose_path(folder)
    try:
        subprocess.run(
            ["docker-compose", "-f", path, "down", "--rmi", "all", "--volumes"], 
            check=True
        )
        AvailableApp.objects.filter(folder_name=folder).update(is_installed=False)
        messages.warning(request, f"Módulo {folder} desinstalado y limpiado.")
    except Exception as e:
        messages.error(request, f"Error al desinstalar: {str(e)}")
    return redirect("get_apps")

def app_logs(request, folder_name):
    path = get_compose_path(folder_name)
    try:
        res = subprocess.run(["docker-compose", "-f", path, "logs", "--tail=150"], capture_output=True, text=True)
        return JsonResponse({"status": "ok", "logs": res.stdout + res.stderr})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
    


# ... (tus imports y funciones anteriores se mantienen igual) ...


import shutil # Añade este import al inicio del archivo

def get_env_config(request, folder_name):
    """Lee el .env, clonando el .env.example si es la primera vez."""
    plugin_path = os.path.join(settings.PLUGINS_DIR, folder_name)
    env_path = os.path.join(plugin_path, '.env')
    example_path = os.path.join(plugin_path, '.env.example')
    
    # Lógica de inicialización inteligente
    if not os.path.exists(env_path):
        try:
            if os.path.exists(example_path):
                # Clonamos el ejemplo para que el usuario tenga una base
                shutil.copyfile(example_path, env_path)
                print(f"DEBUG: .env creado a partir de .env.example para {folder_name}")
            else:
                # Si no hay ejemplo, creamos uno con un comentario guía
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.write("# Configuración del Módulo\n# Define tus variables aquí (KEY=VALUE)\n")
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Error de permisos al crear .env: {str(e)}"})
            
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return JsonResponse({"status": "ok", "content": content})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

@require_POST
def save_env_config(request):
    """Guarda el .env y aplica cambios recreando el contenedor."""
    folder_name = request.POST.get("folder_name")
    content = request.POST.get("content")
    env_path = os.path.join(settings.PLUGINS_DIR, folder_name, '.env')
    path = get_compose_path(folder_name)

    try:
        # 1. Guardar el archivo físico
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 2. Si la app está instalada, aplicar cambios con Docker
        # Docker Compose detecta el cambio en .env y recrea el contenedor automáticamente
        if os.path.exists(path):
            subprocess.run(["docker-compose", "-f", path, "up", "-d"], check=True)
            messages.success(request, f"Configuración de {folder_name} actualizada y aplicada.")
        
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})