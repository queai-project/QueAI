# API Reference (Kernel)

Base URL local: `http://localhost`

## Rutas generales
- `GET /` -> Home simple del kernel.
- `GET /admin/` -> Admin Django.

## Store
- `GET /store/`
  - Sincroniza plugins en disco con BD y renderiza catálogo.

- `POST /store/install/`
  - Form data: `manifest_folder_name`
  - Acción: instala y activa módulo.

- `POST /store/start/`
  - Form data: `manifest_folder_name`
  - Acción: inicia módulo detenido.

- `POST /store/stop/`
  - Form data: `manifest_folder_name`
  - Acción: detiene módulo.

- `POST /store/uninstall/`
  - Form data: `manifest_folder_name`
  - Acción: elimina contenedores/volúmenes/imágenes del módulo.

- `GET /store/logo/<plugin_name>/<filename>`
  - Devuelve logo desde `plugins/<plugin_name>/assets/`.

- `GET /store/logs/<folder_name>/`
  - Respuesta JSON: logs de compose (`tail=150`).

- `GET /store/get_env/<folder_name>/`
  - Si no existe `.env`, intenta crearlo desde `.env.example`.

- `POST /store/save_env/`
  - Form data: `folder_name`, `content`
  - Guarda `.env` y aplica `docker-compose up -d`.

- `GET /store/marketplace/`
  - Renderiza catálogo remoto de plugins.

- `POST /store/download/`
  - Form data: `git_url`
  - Clona repositorio del plugin en `plugins/`.

- `GET /store/stats/<folder_name>/`
  - Respuesta JSON con CPU, RAM, red e ID de contenedores del módulo.

- `GET /store/dashboard/`
  - Dashboard visual de monitoreo.

## Contrato esperado para plugins
Para interoperar correctamente, cada plugin debería exponer:

- `/<healthcheck>` (ej. `/health`) para estado básico.
- `/ui` para interfaz web embebida en iframe.
- Ruta base consistente con Traefik (`/api/<module_name>`).
