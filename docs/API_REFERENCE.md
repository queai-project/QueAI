# API Reference (Kernel)

Base URL local: `http://localhost:8080` (configurable vía `QUEAI_PORT`).

Las URLs están organizadas por la app Django que las sirve. La **fuente de verdad** de las rutas son los `urls.py` de cada app (`core/urls.py`, `module_manager/urls.py`, `marketplace/urls.py`, `system_monitor/urls.py`).

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

## Contrato esperado para plugins
Para interoperar correctamente, cada plugin debería exponer:

- `<base_path>/health` para healthcheck básico.
- `<base_path>/ui` para interfaz web embebible en iframe.
- Ruta base consistente con las labels de Traefik: `PathPrefix(/api/<module_name>)`.

Donde `<base_path>` = `/api/<module_name>` (definido en el `manifest.json` como `ui_entry_point`, `healthcheck_entry_point`, etc).
