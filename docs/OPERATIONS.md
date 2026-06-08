# Operación y despliegue

## Requisitos
- Docker Engine y Docker Compose v2 (`docker compose`).
- Git.
- Linux (Debian/Ubuntu, Fedora/RHEL, Arch), macOS, o **Windows vía WSL2** (ver sección dedicada más abajo).

## Inicio rápido

### Opción A — instalador automático
```bash
curl -fsSL https://queai.dev/install.sh | bash
```

El instalador es **no destructivo**: detecta Docker existente y lo reutiliza. Opciones útiles:

```bash
bash install.sh --dry-run         # mostrar qué haría sin tocar nada
bash install.sh --unattended      # sin preguntas (usa defaults seguros)
bash install.sh --dir ~/QueAI     # directorio personalizado
bash install.sh --branch develop  # rama distinta
```

Variables de entorno reconocidas: `QUEAI_REPO_URL`, `QUEAI_BRANCH`, `QUEAI_DIR`.

### Opción B — manual
```bash
git clone https://github.com/queai-project/QueAI.git
cd QueAI
cp .env.example .env
# Edita .env: define SECRET_KEY (obligatorio si DEBUG=False),
# QUEAI_ADMIN_USER y QUEAI_ADMIN_PASSWORD, y la auth del dashboard de Traefik.
docker compose up -d --build
```

### Primer acceso

1. El kernel queda en `http://localhost:8080/`.
2. **Login obligatorio** en `/login/`. Las credenciales son las que definiste en `QUEAI_ADMIN_USER` / `QUEAI_ADMIN_PASSWORD` antes de arrancar.
3. Si no las definiste por env, crea el admin manualmente:
   ```bash
   docker compose run --rm django-kernel python manage.py createsuperuser
   ```
4. Para rotar la password del admin sin recrearlo, define `QUEAI_ADMIN_ROTATE_PASSWORD=true` en `.env` y reinicia.

### Variables de entorno principales

| Variable | Default | Notas |
|---|---|---|
| `QUEAI_PORT` | `8080` | Puerto del hub en el host |
| `QUEAI_TRAEFIK_DASHBOARD_PORT` | `9090` | Puerto del dashboard interno de Traefik |
| `QUEAI_TRAEFIK_DASHBOARD_AUTH` | `admin:queai` | Usuario:hashBcrypt — genera con `htpasswd -nbB admin <pwd>` |
| `DEBUG` | `False` | `True` en desarrollo. Si `False`, exige `SECRET_KEY`. |
| `SECRET_KEY` | (vacío) | Obligatorio en producción. Genera con `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Lista CSV |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:8080` | Lista CSV de orígenes para CSRF |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `QUEAI_DEV` | `false` | Si `true`, usa `runserver` con auto-reload en lugar de gunicorn |
| `QUEAI_GUNICORN_WORKERS` | `3` | Procesos de gunicorn |
| `QUEAI_GUNICORN_THREADS` | `2` | Threads por proceso |
| `QUEAI_ADMIN_USER` / `QUEAI_ADMIN_PASSWORD` | (vacío) | Si están definidos, se crea el superuser en el primer arranque |

## Windows vía WSL2

QueAI no tiene instalador nativo de Windows todavía (planificado para v1.1). En v1.0 la vía recomendada es **WSL2 + Docker Desktop**, que es lo que técnicamente promete la landing.

### Prerequisitos
1. **Windows 10/11 con WSL2 habilitado**. Desde PowerShell como administrador:
   ```powershell
   wsl --install
   ```
   Esto instala WSL2 + una distribución por defecto (Ubuntu).
2. **Docker Desktop para Windows** con el backend WSL2 activado:
   - Descargar de https://www.docker.com/products/docker-desktop/
   - En Settings → General → marcar **"Use the WSL 2 based engine"**.
   - En Settings → Resources → WSL Integration → activar la integración para tu distro.

### Instalación
Abre la terminal WSL (Ubuntu) y corre **el mismo instalador que en Linux**:

```bash
curl -fsSL https://queai.dev/install.sh | bash
```

Una vez levantado, el hub vive en `http://localhost:8080/` desde **el navegador de Windows**, no desde dentro de WSL — Docker Desktop expone los puertos del lado de Windows automáticamente.

### Recomendaciones importantes

- **Mantén el repo dentro del filesystem de WSL** (`~/QueAI`), no en `/mnt/c/...`. El I/O de NTFS a través de 9P es entre 5x y 20x más lento, y el OCR/STT castigan disco fuerte. Si tienes el repo en `C:\` mueve a `~/`.
- Si Docker Desktop está cerrado, los contenedores se detienen. Configúralo para **arrancar con Windows** si quieres que QueAI sobreviva reinicios.
- El comando `code .` desde WSL abre VS Code con el remote correcto y mejor rendimiento que abrirlo en Windows apuntando a `\\wsl$\...`.

### Limitaciones conocidas en WSL2

- El modelo de UID/GID dentro de WSL es real, así que el marketplace (que clona con `--user $UID:$GID`) funciona bien.
- Acceso a hardware GPU vía CUDA-WSL existe pero los plugins actuales son CPU-only, así que no aplica para v1.0.
- Windows nativo (PowerShell, sin WSL) **no está soportado** todavía. Está planificado un `install.ps1` post-v1.0.

## URLs de trabajo
- Hub:               `http://localhost:8080/`
- Catálogo:          `http://localhost:8080/manager/`
- Marketplace:       `http://localhost:8080/marketplace/`
- Monitor:           `http://localhost:8080/monitor/`
- Traefik dashboard: `http://localhost:9090/dashboard/` (interno)

> El puerto del hub es configurable vía `QUEAI_PORT` en `.env`.

## Operaciones frecuentes

```bash
docker compose up -d                    # levantar todo
docker compose ps                       # ver estado
docker compose logs -f django-kernel    # logs del kernel
docker compose restart django-kernel    # reiniciar el kernel sin tocar plugins
docker compose down                     # detener todo (mantiene volúmenes)
```

## Gestión de módulos
Desde `http://localhost:8080/manager/` puedes:

- **Instalar** módulo: `docker compose up -d --build --force-recreate` sobre el módulo.
- **Iniciar / Detener** módulo.
- **Desinstalar**: `down --rmi all --volumes --remove-orphans`. Conserva la carpeta y el registro (sigue listado como disponible).
- **Eliminar**: igual que desinstalar + `rmtree` de la carpeta + borrado del registro.
- **Editar `.env`** y reaplicar configuración (recreate del contenedor).
- **Consultar logs** del módulo (últimas 150 líneas, bajo demanda).

## Marketplace
- El catálogo remoto se obtiene desde un `register.json` en GitHub (URL en `marketplace/views.py:REGISTRY_URL`).
- Al descargar un módulo, el kernel ejecuta `git clone` dentro de un contenedor auxiliar `alpine/git` con el UID/GID del host para que los archivos queden con permisos del usuario.

## Monitoreo
El dashboard `/monitor/` consulta cada pocos segundos:
- CPU
- RAM
- Red
- ID de contenedor

Fuente de datos: `docker stats --no-stream` + `docker ps` filtrado por label `com.docker.compose.project=<folder.lower()>`.

## Respaldo y restauración
Elementos a respaldar:

- Carpeta `plugins/` (los plugins son repos Git independientes; un `git status` por plugin te dice si hay cambios sin commit).
- `db.sqlite3` (estado del catálogo).
- `.env` del proyecto.
- `.env` de cada módulo.

## Seguridad recomendada para producción

Mínimo antes de exponer a una red no confiable:

- `DEBUG=False`.
- `SECRET_KEY` única (regenérala: `python -c "import secrets; print(secrets.token_urlsafe(50))"`).
- `ALLOWED_HOSTS` restrictivo (no `*`).
- Auth básica delante del kernel (no incluida aún).
- HTTPS / TLS (no incluido aún).
- Cerrar o proteger el dashboard de Traefik (`:9090`).
- Revisar impacto de exponer `/var/run/docker.sock` al contenedor del kernel — implica privilegios de root en el host.

## Solución de problemas

### El módulo no aparece en el catálogo
- Verifica que existan `manifest.json` y `docker-compose.yml` en su carpeta.
- El `manifest.json` debe ser JSON válido y contener el campo `name`.

### Error al instalar módulo
- Revisa logs del kernel: `docker compose logs -f django-kernel`.
- Revisa el build del módulo: `cd plugins/<modulo> && docker compose up --build` (manualmente).
- Confirma que la red `queai_network` existe: `docker network ls | grep queai`.

### No se descarga módulo desde marketplace
- Confirma conectividad a internet del host.
- Verifica que la URL Git del módulo sea pública.
- Verifica que `HOST_PROJECT_PATH`, `HOST_UID`, `HOST_GID` estén definidas en el entorno del kernel. Si arrancaste con `docker compose up`, el compose ya las pasa desde `${PWD}` / `${UID}` / `${GID}`.

### El puerto 8080 está ocupado
Define otro puerto en `.env`:

```bash
QUEAI_PORT=9000
```

y recrea: `docker compose up -d --force-recreate`.

### Plugins antiguos no se conectan al kernel (red `odoo_network`)
A partir de v1.0 la red compartida se llama **`queai_network`** (antes `odoo_network`). Plugins desarrollados antes deben actualizar la sección `networks:` de su `docker-compose.yml`. Los plugins oficiales (OCR, STT, TTS, RAG) ya están migrados.
