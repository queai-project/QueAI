
import subprocess
import json
from django.shortcuts import render
from django.http import JsonResponse
from module_manager.models import AvailableApp
def app_stats(request, folder_name):
    """Obtiene métricas de CPU y RAM de los contenedores de una app específica."""
    try:
        # 1. Buscamos los contenedores que pertenecen a este proyecto
        cmd_ids = [
            "docker", "ps", 
            "--filter", f"label=com.docker.compose.project={folder_name}", 
            "--format", "{{.ID}}"
        ]
        res_ids = subprocess.run(cmd_ids, capture_output=True, text=True)
        container_ids = res_ids.stdout.strip().split('\n')

        # Si no hay contenedores, devolvemos error silencioso para el JS
        if not container_ids or container_ids == ['']:
            return JsonResponse({"status": "error", "message": "No containers found"})

        # 2. Obtenemos las stats
        cmd_stats = [
            "docker", "stats", "--no-stream", 
            "--format", '{"id":"{{.ID}}","cpu":"{{.CPUPerc}}","mem":"{{.MemUsage}}","net":"{{.NetIO}}"}'
        ] + container_ids
        
        res_stats = subprocess.run(cmd_stats, capture_output=True, text=True)
        
        raw_lines = res_stats.stdout.strip().split('\n')
        # Limpiamos líneas vacías para evitar errores de JSON
        stats_data = [json.loads(line) for line in raw_lines if line.strip()]

        return JsonResponse({"status": "ok", "stats": stats_data})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

def stats_dashboard(request):
    """Renderiza la página de monitoreo pasando los datos limpios."""
    # Filtramos las apps instaladas
    apps = AvailableApp.objects.filter(is_installed=True)
    # Lista de nombres de carpetas para el JavaScript
    apps_folders = list(apps.values_list('folder_name', flat=True))
    
    return render(request, "system_monitor.html", {
        "apps": apps, 
        "apps_folders": apps_folders
    })