# Arquitectura técnica — QueAI

## Visión general
QueAI se compone de un **kernel Django** y un ecosistema de **módulos Docker** conectados por una red compartida (`queai_network`) con **Traefik** como punto de entrada HTTP.

Componentes principales:

- **Traefik**: enruta tráfico por prefijos (`PathPrefix`) hacia el kernel y los módulos. Escucha en `:8080` del host (configurable vía `QUEAI_PORT`).
- **Django Kernel**: UI + lógica del catálogo + operaciones Docker. Se ejecuta dentro del contenedor `queai_kernel`.
- **SQLite (`db.sqlite3`)**: estado local de módulos detectados/instalados. No versionado.
- **Plugins**: servicios independientes en `plugins/<module>/`, cada uno con su propio `docker-compose.yml`. **Lo que hagan internamente es transparente para el kernel**: ejecutar un modelo en CPU, proxyar a una API externa (OpenAI, Anthropic, ElevenLabs, etc.), encadenar varios pasos en un pipeline — todo es válido mientras respete el contrato del manifest y la red `queai_network`.

## Flujo de red

```
[ navegador ]
      │
      ▼   (host:8080)
┌───────────────┐
│    Traefik    │  ── PathPrefix(/) ───►  django-kernel (UI + control)
│ queai_network │  ── PathPrefix(/api/<plugin>) ───►  contenedor del plugin
└───────────────┘
```

1. El cliente accede a `http://localhost:8080/`.
2. Traefik enruta `PathPrefix(/)` → servicio `kernel` (contenedor `queai_kernel`).
3. Al abrir un módulo, Traefik enruta `PathPrefix(/api/<modulo>)` → contenedor del plugin correspondiente.
4. El dashboard interno de Traefik queda en `:9090` (también configurable, con `QUEAI_TRAEFIK_DASHBOARD_PORT`).

## Modelo de plugins (qué puede ser un plugin)

El kernel impone un contrato: `manifest.json` declarando rutas, un
`docker-compose.yml` que se una a `queai_network`, y labels Traefik con
`PathPrefix(/api/<name>)`. Lo que ocurra dentro del contenedor es libre.

Patrones válidos:

| Patrón | Ejemplo | Implicaciones |
|---|---|---|
| Modelo local en CPU | Tesseract OCR, faster-whisper STT, Piper TTS | El contenedor carga el modelo en RAM; el host necesita CPU/RAM suficientes |
| Modelo local en GPU | Ollama con un LLM, modelo de visión | Requiere `--gpus all` en el compose del plugin y NVIDIA Container Toolkit en el host |
| Thin proxy a API externa | Plugin que expone `/transcribe` y por dentro llama a OpenAI Whisper API | El contenedor casi no consume recursos; necesita conectividad saliente y un secreto en su `.env` |
| Pipeline mixto | Plugin "RAG" que mezcla embeddings cloud con vector store local | El plugin hace de orquestador interno |
| Adaptador OpenAI-compat | Plugin que ofrece `/v1/chat/completions` y por dentro decide local vs cloud según config | Permite que el resto del sistema vea una única superficie estándar |

El kernel **no distingue** entre estos casos: para él todos son contenedores
con una URL bajo `/api/<name>`. La consecuencia práctica es que sustituir
"CHAT local Ollama" por "CHAT proxy Anthropic" sin afectar al resto de
módulos es un cambio de plugin, no del kernel.

## Apps Django (mapeo real)

El kernel está dividido en tres apps Django, cada una con su responsabilidad bien acotada. **Fuente de verdad de las rutas: `core/urls.py` y los `urls.py` de cada app.**

| App | Path raíz | Responsabilidad |
|---|---|---|
| `module_manager/` | `/manager/` | Catálogo local, ciclo de vida (install/start/stop/uninstall/delete), edición de `.env`, logs por módulo. |
| `marketplace/` | `/marketplace/` | Catálogo remoto (registry), descarga / actualización de plugins desde Git. |
| `system_monitor/` | `/monitor/` | Dashboard de CPU/RAM/red de los módulos instalados. |
| `core/` | `/` | Home y configuración Django (`settings`, `urls`). |

## Flujo funcional del catálogo
1. La vista `GET /manager/` (`module_manager.views.get_apps`) escanea `PLUGINS_DIR`.
2. Para cada carpeta válida (`manifest.json` + `docker-compose.yml`), sincroniza metadatos en `AvailableApp` mediante `update_or_create`.
3. Evalúa estado de ejecución por plugin con `docker compose -f <compose> top`.
4. Para los plugins que existían en BD pero ya no en disco, ejecuta `_cleanup_missing_plugin_docker_artifacts` (barrido por label `com.docker.compose.project=<folder>` → elimina contenedores, redes, volúmenes e imágenes huérfanas) y elimina la fila.
5. Renderiza UI con acciones disponibles por estado.

> `get_apps` también es el reconciliador: corre en cada visita. Es síncrono y puede ser lento con muchos plugins; tiene un cache locmem de 5 s por worker (`_is_app_running_cached`) y un endpoint manual `POST /manager/refresh/` para invalidarlo.

## Modelo de datos principal
Tabla `AvailableApp` (`module_manager/models.py`):

- `name` (único, viene del manifest)
- `folder_name`
- `display_name`
- `logo`
- `ui_entry_point`
- `configuration_entry_point`
- `documentation_entry_point`
- `version`
- `description`
- `author`
- `lic`
- `is_installed`

## Endpoints internos del kernel

### `module_manager/` — gestor del catálogo local
- `GET  /manager/` — catálogo + estado.
- `POST /manager/install/` — `docker compose up -d --build --force-recreate`.
- `POST /manager/start/` — `docker compose start`.
- `POST /manager/stop/` — `docker compose stop`.
- `POST /manager/uninstall/` — `docker compose down --rmi all --volumes --remove-orphans` (conserva carpeta y registro).
- `POST /manager/delete/` — uninstall + `rmtree` del plugin + borrado del registro.
- `GET  /manager/logs/<folder>/` — últimas 150 líneas de logs.
- `GET  /manager/get_env/<folder>/` — carga/crea `.env` (clona desde `.env.example` en el primer acceso).
- `POST /manager/save_env/` — guarda `.env` y aplica cambios con `up -d --force-recreate`.
- `GET  /manager/logo/<plugin>/<file>` — sirve el logo del plugin desde `assets/`.

### `marketplace/` — catálogo remoto
- `GET  /marketplace/` — lista plugins desde el `register.json` remoto (URL hardcoded en `marketplace/views.py:REGISTRY_URL`; hacerlo configurable es Fase 2).
- `POST /marketplace/download/` — clona/actualiza plugin desde Git en un contenedor `alpine/git` efímero (ver "Marketplace clone contract" más abajo).

### `system_monitor/` — observabilidad
- `GET /monitor/` — dashboard.
- `GET /monitor/stats/<folder>/` — JSON con CPU/RAM/red por contenedor del módulo (`docker stats --no-stream` filtrado por label de compose).

## Marketplace: contrato de clonado

El kernel **no clona desde adentro del contenedor**, porque eso dejaría los plugins propiedad de `root` y fuera del filesystem del host. En su lugar, lanza un contenedor efímero:

```bash
docker run --rm --user $HOST_UID:$HOST_GID \
  -v $HOST_PROJECT_PATH/plugins:/data \
  alpine/git clone <git_url> /data/<folder>
```

Para que esto funcione, el `docker-compose.yml` del kernel pasa `HOST_PROJECT_PATH=${PWD}`, `HOST_UID=${UID}`, `HOST_GID=${GID}`. Si arrancas el kernel fuera de Docker Compose, exporta esas variables manualmente.

Un repo que clona pero no contiene `manifest.json` válido es **rechazado** y limpiado.

## Estructura de carpetas relevante

```text
QueAI/
├── core/                       # Configuración Django (settings, urls, asgi/wsgi)
├── module_manager/             # Catálogo + ciclo de vida de plugins
├── marketplace/                # Registry remoto + descarga
├── system_monitor/             # Dashboard CPU/RAM/red
├── plugins/                    # Módulos instalables (cada uno es un repo Git)
├── docs/                       # Documentación
├── docker-compose.yml          # Traefik + Kernel + red queai_network
├── Dockerfile                  # Imagen del Kernel
├── entrypoint.sh               # migrate + runserver
├── install.sh                  # Instalador no destructivo, multi-OS
├── .env.example                # Variables de entorno
└── LICENSE                     # MIT
```

## Decisiones actuales
- El kernel usa el socket Docker del host (`/var/run/docker.sock`) montado en `queai_kernel` para operar los módulos.
- Los módulos no exponen puertos del host; Traefik los publica por prefijo de ruta.
- El marketplace remoto usa un `register.json` JSON centralizado en GitHub.
- La red Docker compartida (`queai_network`) la crea el `docker-compose.yml` del kernel — los plugins se unen a ella declarándola como `external: true`.
- El puerto del hub es **`:8080`** por defecto, para alinear con la landing en queai.dev. Configurable.

## Riesgos operativos a considerar
- Exponer el socket Docker al contenedor del kernel implica alto privilegio.
- `DEBUG=True` y `ALLOWED_HOSTS` permisivos son apropiados para desarrollo, no para producción.
- Todas las vistas que mutan estado (`/manager/`, `/marketplace/`, `/monitor/`, `/account/`, `/audit/`) requieren login. Rutas públicas: `/`, `/health`, `/login/`. El admin se autocrea en el primer arranque desde `QUEAI_ADMIN_USER`/`QUEAI_ADMIN_PASSWORD`. La API REST usa bearer token (`QUEAI_API_TOKEN`).
- `delete_app` elimina imágenes, volúmenes y la carpeta completa del módulo (`--rmi all --volumes` + `rmtree`).
