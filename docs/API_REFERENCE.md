# API Reference (Kernel)

Local base URL: `http://localhost:8473` (configurable via `QUEAI_PORT`).

URLs are organized by the Django app that serves them. The **source of truth** for routes is each app's `urls.py` (`core/urls.py`, `module_manager/urls.py`, `marketplace/urls.py`, `system_monitor/urls.py`).

## Two API surfaces

The kernel exposes two distinct surfaces:

1. **Web UI** (everything below) — Django session auth, returns HTML.
2. **REST API `/api/v1/`** — bearer token auth (`QUEAI_API_TOKEN`), returns JSON. Designed for scripts, CI and the `queai` CLI. Documented at the end.

## General (`core/`)

- `GET /` — Kernel home (`home.html`).
- `GET /admin/` — Django admin (can be disabled in production).

## `module_manager/` — local catalog manager

- `GET /manager/`
  - Syncs on-disk plugins with the DB and renders the catalog. Also runs the reconciler (removes orphaned plugins and cleans up their Docker resources).

- `POST /manager/install/`
  - Form data: `manifest_folder_name`
  - Action: `docker compose up -d --build --force-recreate` on the module.

- `POST /manager/start/`
  - Form data: `manifest_folder_name`
  - Action: `docker compose start`.

- `POST /manager/stop/`
  - Form data: `manifest_folder_name`
  - Action: `docker compose stop`.

- `POST /manager/uninstall/`
  - Form data: `manifest_folder_name`
  - Action: `docker compose down --rmi all --volumes --remove-orphans`. Keeps the plugin folder and the DB row (still listed as available).

- `POST /manager/delete/`
  - Form data: `manifest_folder_name`
  - Action: full uninstall + `rmtree` of the folder + DB row removal.

- `GET /manager/logo/<plugin_name>/<filename>`
  - Returns the logo from `plugins/<plugin_name>/assets/<filename>`.

- `GET /manager/logs/<folder_name>/`
  - JSON response: last 150 lines of `docker compose logs`.

- `GET /manager/get_env/<folder_name>/`
  - If `.env` doesn't exist, it's created from `.env.example` (or an empty placeholder). Returns the content.

- `POST /manager/save_env/`
  - Form data: `folder_name`, `content`
  - Saves the `.env` and applies `docker compose up -d --force-recreate` to recreate the container.

## `marketplace/` — remote catalog

- `GET /marketplace/`
  - Renders the remote catalog. Fetches `register.json` with cache-busting and cross-references against local disk to report `is_downloaded`, `local_version` and `is_update_available` per plugin.

- `POST /marketplace/download/`
  - Form data: `git_url`
  - Clones/updates the plugin from Git in an ephemeral `alpine/git` container using the host's UID/GID. If the repo doesn't contain a valid `manifest.json`, it's rejected and cleaned up.

## `system_monitor/` — observability

- `GET /monitor/`
  - Renders the monitoring dashboard.

- `GET /monitor/stats/<folder_name>/`
  - JSON response with CPU, RAM, network and ID for each module container. Source: `docker ps --filter label=com.docker.compose.project=<folder.lower()>` + `docker stats --no-stream`.

## REST API (`/api/v1/`)

Authentication: `Authorization: Bearer <QUEAI_API_TOKEN>` header on every request (except `health` and `openapi.json`). The token is set in `.env`; if empty and `DEBUG=True`, the kernel generates an ephemeral one per session and logs it.

Browsable UI at `GET /api/v1/docs` (Swagger UI; press **Authorize** after loading). Raw schema at `GET /api/v1/openapi.json`.

### Meta

- `GET /api/v1/health` — public. JSON with `status`, `version`, `plugins`.
- `GET /api/v1/openapi.json` — OpenAPI 3 schema.
- `GET /api/v1/docs` — Swagger UI.

### Catalog and lifecycle

- `GET  /api/v1/plugins/` — lists all plugins with their state.
- `GET  /api/v1/plugins/<folder>/` — detail.
- `POST /api/v1/plugins/<folder>/install` — `docker compose up --build`. Status 202.
- `POST /api/v1/plugins/<folder>/start` — starts the container.
- `POST /api/v1/plugins/<folder>/stop` — stops it.
- `POST /api/v1/plugins/<folder>/uninstall` — down with `--rmi all --volumes` (keeps the folder).
- `POST /api/v1/plugins/<folder>/delete` — uninstall + delete the plugin folder.

### Logs and metrics

- `GET /api/v1/plugins/<folder>/logs?tail=N` — last N lines (default 150, max 2000).
- `GET /api/v1/plugins/<folder>/stats` — CPU/RAM/network per container.

### Configuration

- `GET /api/v1/plugins/<folder>/env` — reads the `.env` (creates it from `.env.example` if missing).
- `PUT /api/v1/plugins/<folder>/env` — JSON body `{ "content": "KEY=VAL\n...", "apply": true }`. If `apply=true`, the container is recreated.

### Marketplace

- `GET  /api/v1/marketplace/` — remote registry list cross-referenced with local state.
- `POST /api/v1/marketplace/download` — JSON body `{ "git_url": "https://..." }`. Status 201 if the clone succeeds and the manifest is valid.

### Observability

- `GET /api/v1/plugins/<folder>/healthcheck` — hits the manifest's `healthcheck_entry_point` and returns `{healthy, latency_ms, status_code, error}`. 5 s cache. `healthy=null` if the plugin doesn't declare the endpoint.
- `GET /api/v1/plugins/<folder>/logs/stream?tail=50` — Server-Sent Events with `docker compose logs -f`. **Max 2 concurrent streams** in the kernel. Lines as `data: <line>\n\n`.
- `GET /api/v1/audit/?action=...&target=...&source=...&limit=100` — kernel action history.

### Backup / restore

- `GET /api/v1/backup` — downloads a `tar.gz` with `db.sqlite3` + the kernel's `.env` + each plugin's `.env`. **Does not** include `plugins/` or runtime data.
- `POST /api/v1/restore` (multipart, `backup` field) — extracts the tar into `restore-staging/`. Doesn't apply anything.
- `POST /api/v1/restore/apply` — moves the staging into the live system. Saves `db.sqlite3.pre-restore` and `.env.pre-restore` in case you need to roll back. **Requires a kernel restart** afterwards because Django keeps the DB handle open.

### Error codes

| Status | error | Meaning |
|--------|-------|---------|
| 400    | `bad_request`  | Invalid body or query. |
| 401    | `unauthorized` | Missing Authorization header. |
| 403    | `forbidden`    | Invalid token. |
| 404    | `not_found`    | Plugin doesn't exist. |
| 500    | `internal`     | Subprocess failed or other server error. |
| 503    | `degraded`     | (`/health` when the DB doesn't respond). |

### Client CLI

See [`cli/README.md`](../cli/README.md) — `queai login`, `queai list`, `queai install`, etc.

## Expected contract for plugins

To interoperate correctly, each plugin should expose:

- `<base_path>/health` for the basic healthcheck.
- `<base_path>/ui` for an iframe-embeddable web interface.
- A base path consistent with the Traefik labels: `PathPrefix(/api/<module_name>)`.

Where `<base_path>` = `/api/<module_name>` (defined in `manifest.json` as `ui_entry_point`, `healthcheck_entry_point`, etc.).
