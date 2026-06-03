# API Reference (Kernel)

Base URL local: `http://localhost:8080` (configurable vía `QUEAI_PORT`).

Las URLs están organizadas por la app Django que las sirve. La **fuente de verdad** de las rutas son los `urls.py` de cada app (`core/urls.py`, `module_manager/urls.py`, `marketplace/urls.py`, `system_monitor/urls.py`).

## Dos superficies de API

El kernel expone dos superficies distintas:

1. **UI web** (todo lo siguiente) — auth por sesión Django, devuelve HTML.
2. **API REST `/api/v1/`** — auth por bearer token (`QUEAI_API_TOKEN`), devuelve JSON. Pensada para scripts, CI y la CLI `queai`. Documentada al final.

## Generales (`core/`)
- `GET /` — Home del kernel (`home.html`).
- `GET /admin/` — Admin de Django (deshabilitable en producción).

## `module_manager/` — gestor del catálogo local

- `GET /manager/`
  - Sincroniza plugins en disco con BD y renderiza el catálogo. También ejecuta el reconciliador (borra plugins huérfanos y limpia sus recursos Docker).

- `POST /manager/install/`
  - Form data: `manifest_folder_name`
  - Acción: `docker compose up -d --build --force-recreate` sobre el módulo.

- `POST /manager/start/`
  - Form data: `manifest_folder_name`
  - Acción: `docker compose start`.

- `POST /manager/stop/`
  - Form data: `manifest_folder_name`
  - Acción: `docker compose stop`.

- `POST /manager/uninstall/`
  - Form data: `manifest_folder_name`
  - Acción: `docker compose down --rmi all --volumes --remove-orphans`. Conserva la carpeta del plugin y el registro en BD (sigue listado como disponible).

- `POST /manager/delete/`
  - Form data: `manifest_folder_name`
  - Acción: uninstall completo + `rmtree` de la carpeta + borrado del registro.

- `GET /manager/logo/<plugin_name>/<filename>`
  - Devuelve el logo desde `plugins/<plugin_name>/assets/<filename>`.

- `GET /manager/logs/<folder_name>/`
  - Respuesta JSON: últimas 150 líneas de `docker compose logs`.

- `GET /manager/get_env/<folder_name>/`
  - Si no existe `.env`, lo crea desde `.env.example` (o crea un placeholder vacío). Devuelve el contenido.

- `POST /manager/save_env/`
  - Form data: `folder_name`, `content`
  - Guarda el `.env` y aplica `docker compose up -d --force-recreate` para recrear el contenedor.

## `marketplace/` — catálogo remoto

- `GET /marketplace/`
  - Renderiza el catálogo remoto. Hace fetch del `register.json` con cache-busting y cruza contra el disco local para reportar `is_downloaded`, `local_version` e `is_update_available` por plugin.

- `POST /marketplace/download/`
  - Form data: `git_url`
  - Clona / actualiza el plugin desde Git en un contenedor `alpine/git` efímero con el UID/GID del host. Si el repo no contiene un `manifest.json` válido, se rechaza y se limpia.

## `system_monitor/` — observabilidad

- `GET /monitor/`
  - Renderiza el dashboard de monitoreo.

- `GET /monitor/stats/<folder_name>/`
  - Respuesta JSON con CPU, RAM, red e ID de cada contenedor del módulo. Fuente: `docker ps --filter label=com.docker.compose.project=<folder.lower()>` + `docker stats --no-stream`.

## API REST (`/api/v1/`)

Autenticación con header `Authorization: Bearer <QUEAI_API_TOKEN>` en cada request (excepto health y openapi.json). El token se define en `.env`; si está vacío y `DEBUG=True`, el kernel genera uno efímero por sesión y lo imprime en logs.

UI navegable en `GET /api/v1/docs` (Swagger UI, requiere navegar y luego pulsar **Authorize**). Schema crudo en `GET /api/v1/openapi.json`.

### Meta
- `GET /api/v1/health` — público. JSON con `status`, `version`, `plugins`.
- `GET /api/v1/openapi.json` — schema OpenAPI 3.
- `GET /api/v1/docs` — Swagger UI.

### Catálogo y ciclo de vida
- `GET  /api/v1/plugins/` — lista todos los plugins con su estado.
- `GET  /api/v1/plugins/<folder>/` — detalle.
- `POST /api/v1/plugins/<folder>/install` — `docker compose up --build`. Status 202.
- `POST /api/v1/plugins/<folder>/start` — inicia el contenedor.
- `POST /api/v1/plugins/<folder>/stop` — detiene.
- `POST /api/v1/plugins/<folder>/uninstall` — down con `--rmi all --volumes` (conserva carpeta).
- `POST /api/v1/plugins/<folder>/delete` — uninstall + borrado de la carpeta del plugin.

### Logs y métricas
- `GET /api/v1/plugins/<folder>/logs?tail=N` — últimas N líneas (default 150, máx 2000).
- `GET /api/v1/plugins/<folder>/stats` — CPU/RAM/red por contenedor.

### Configuración
- `GET /api/v1/plugins/<folder>/env` — lee el `.env` (lo crea desde `.env.example` si no existe).
- `PUT /api/v1/plugins/<folder>/env` — body JSON `{ "content": "KEY=VAL\n...", "apply": true }`. Si `apply=true`, recrea el contenedor.

### Marketplace
- `GET  /api/v1/marketplace/` — lista del registry remoto cruzada con estado local.
- `POST /api/v1/marketplace/download` — body JSON `{ "git_url": "https://..." }`. Status 201 si el clone es exitoso y el manifest válido.

### Observabilidad (Bloque D)
- `GET /api/v1/plugins/<folder>/healthcheck` — pega al `healthcheck_entry_point` del manifest y devuelve `{healthy, latency_ms, status_code, error}`. Cache 5s. `healthy=null` si el plugin no declara el endpoint.
- `GET /api/v1/plugins/<folder>/logs/stream?tail=50` — Server-Sent Events con `docker compose logs -f`. **Máx 2 streams simultáneos** en el kernel. Líneas como `data: <line>\n\n`.
- `GET /api/v1/audit/?action=...&target=...&source=...&limit=100` — historial de acciones del kernel (sin auth necesaria entre source).

### Backup / restore
- `GET /api/v1/backup` — descarga `tar.gz` con `db.sqlite3` + `.env` del kernel + `.env` de cada plugin. **No** incluye `plugins/` ni runtimes.
- `POST /api/v1/restore` (multipart, campo `backup`) — extrae el tar a `restore-staging/`. No aplica nada.
- `POST /api/v1/restore/apply` — mueve el staging al sistema en vivo. Guarda `db.sqlite3.pre-restore` y `.env.pre-restore` por si tienes que revertir. **Requiere reiniciar el kernel** después porque Django mantiene el handle de la BD abierto.

### Códigos de error

| Status | error                  | Significado |
|--------|------------------------|-------------|
| 400    | `bad_request`          | Body o query inválidos. |
| 401    | `unauthorized`         | Falta header Authorization. |
| 403    | `forbidden`            | Token inválido. |
| 404    | `not_found`            | Plugin no existe. |
| 500    | `internal`             | Subprocess falló u otro error servidor. |
| 503    | `degraded`             | (`/health` cuando la DB no responde). |

### CLI cliente

Ver [`cli/README.md`](../cli/README.md) — `queai login`, `queai list`, `queai install`, etc.

## Contrato esperado para plugins
Para interoperar correctamente, cada plugin debería exponer:

- `<base_path>/health` para healthcheck básico.
- `<base_path>/ui` para interfaz web embebible en iframe.
- Ruta base consistente con las labels de Traefik: `PathPrefix(/api/<module_name>)`.

Donde `<base_path>` = `/api/<module_name>` (definido en el `manifest.json` como `ui_entry_point`, `healthcheck_entry_point`, etc).
