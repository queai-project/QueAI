# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

QueAI is a Django-based **kernel/hub** that manages independent AI modules ("plugins") as Docker projects. It auto-discovers plugins from `plugins/`, installs/starts/stops them via `docker compose`, exposes them through a shared Traefik router on a single host port, and reports CPU/RAM/network from `docker stats`. Persistence is a single SQLite file (`db.sqlite3`); the catalog table is `AvailableApp` in `module_manager/models.py`.

## Running the system

Normal operation is fully containerized — the kernel itself runs as the `django-kernel` container and shells out to `docker`/`docker-compose` on the host via the mounted Docker socket.

```bash
docker compose up -d --build       # start kernel + Traefik
docker compose logs -f django-kernel
docker compose down
```

URLs (Traefik web on `:8080`, internal dashboard on `:9090` — both configurable via `QUEAI_PORT` / `QUEAI_TRAEFIK_DASHBOARD_PORT`):

- `http://localhost:8080/` — kernel home (`core.views.home_view`)
- `http://localhost:8080/manager/` — installed/available plugin catalog (module_manager)
- `http://localhost:8080/marketplace/` — remote registry browser
- `http://localhost:8080/monitor/` — system_monitor dashboard
- `http://localhost:8080/api/<plugin>/...` — plugin routes (each plugin attaches its own Traefik `PathPrefix` label)
- `http://localhost:9090/dashboard/` — Traefik dashboard (internal)

`entrypoint.sh` runs `migrate --noinput` → `collectstatic` → `ensure_admin` → `gunicorn core.wsgi:application` (3 workers × 2 threads, 120s timeout — all overridable with `QUEAI_GUNICORN_*`). For dev with hot reload, set `QUEAI_DEV=true` to fall back to `runserver`.

### Running Django outside Docker (rare)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Marketplace download will fail outside Docker unless `HOST_PROJECT_PATH`, `HOST_UID`, `HOST_GID` are exported — see "Marketplace clone contract" below.

### Tests

Standard Django test runner:

```bash
python manage.py test                            # all apps
python manage.py test module_manager             # one app
python manage.py test module_manager.tests.ClassName.test_method
```

The app `tests.py` files are currently empty stubs.

## Architecture

Three Django apps mounted under `core/urls.py`, each owning one concern:

- **`module_manager/`** — the catalog and lifecycle controller. `get_apps` (the `/manager/` view) walks `PLUGINS_DIR`, requires both `manifest.json` and `docker-compose.yml` to consider a folder valid, and `update_or_create`s an `AvailableApp` row from the manifest. Folders that vanish from disk trigger `_cleanup_missing_plugin_docker_artifacts` — a label-based sweep (`com.docker.compose.project=<folder>`) that removes containers, networks, volumes, and images before deleting the DB row. Install/start/stop/uninstall/delete each shell out via `_get_compose_command()` which prefers the `docker-compose` binary and falls back to `docker compose`.
- **`marketplace/`** — fetches a remote `register.json` (URL hard-coded in `marketplace/views.py:REGISTRY_URL`) with cache-busting headers, compares versions per plugin via `_safe_version_tuple`, and on download spawns a one-shot `alpine/git` container to clone into `plugins/<folder>`. **It does not clone from inside the kernel container**; it runs `docker run --rm -v $HOST_PROJECT_PATH/plugins:/data alpine/git clone …`, which is why the kernel needs `HOST_PROJECT_PATH`, `HOST_UID`, `HOST_GID` (set by `docker-compose.yml` from `${PWD}` / `${UID}` / `${GID}`). A repo that clones successfully but lacks `manifest.json` is rejected.
- **`system_monitor/`** — `/monitor/` dashboard plus `app_stats(folder_name)` JSON endpoint. Stats are collected by `docker ps --filter label=com.docker.compose.project=<folder.lower()>` followed by `docker stats --no-stream` with a custom `{{.ID}}/{{.CPUPerc}}/{{.MemUsage}}/{{.NetIO}}` format. The lowercasing is load-bearing because Compose normalizes project names.

Everything talks to Docker through `/var/run/docker.sock`, mounted into the kernel container in `docker-compose.yml`. The kernel and all plugins share a Docker network named **`queai_network`** — created by the kernel's compose, joined by each plugin's compose as `external: true`. If you ever destroy it, plugins lose routing.

## Plugin contract

Each `plugins/<folder>/` must contain:

- `manifest.json` with at least `name` (unique, stable), `display_name`, `version`, `ui_entry_point`, `logo`, plus optional `configuration_entry_point`, `documentation_entry_point`, `healthcheck_entry_point`, `description`, `author`, `license`.
- `docker-compose.yml` that joins `queai_network` (declared `external: true`) and adds Traefik labels with `PathPrefix(\`/api/<name>\`)` and `loadbalancer.server.port=8000`. Don't declare `version:` — obsolete in Compose v2.
- `assets/<logo>` served by `module_manager.views.plugin_logo`.
- Optional `.env.example` — when the user opens config for a plugin, `get_env_config` clones it to `.env` on first read.

See `docs/PLUGIN_DEVELOPMENT.md` for the full template. `plugins/QueAI-OCR-CPU-LOCAL-MS/` is a working reference.

## Things to know that aren't obvious from the code

- **Source of truth for routes is always `core/urls.py` + each app's `urls.py`** (not docs, not landing). Real prefixes are `/manager/`, `/marketplace/`, `/monitor/`. The earlier `/store/` prefix is gone; if you find a stale reference, fix it.
- **Compose project name = folder name, lowercased**, because Compose lowercases by default. `system_monitor.views.app_stats` and `_compose_project_candidates` rely on this for label filtering. If you ever rename a plugin folder, the orphan-cleanup sweep is your safety net.
- **Uninstall vs Delete differ deliberately.** `uninstall_app` runs `down --rmi all --volumes --remove-orphans` and flips `is_installed=False` but keeps the folder and DB row so the module stays listed as available. `delete_app` additionally `rmtree`s `plugins/<folder>` and removes the row.
- **`get_apps` is also the reconciler.** Hitting `/manager/` re-scans disk, upserts rows, and prunes orphans on every request — there's no background job. Slow if you have many plugins because it runs `docker compose top` per plugin.
- **Settings are production-ready by default.** `DEBUG=False`, `SECRET_KEY` is **required** (kernel refuses to start if missing and not in DEBUG mode), `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` from env. When `DEBUG=False`, cookies are secure/httponly and anti-XSS/clickjacking headers are on.
- **Auth is mandatory.** Every view in `module_manager`, `marketplace`, `system_monitor` uses `@login_required`. Public routes: `/`, `/health`, `/login/`, `/logout/`. Bootstrap admin via `QUEAI_ADMIN_USER` + `QUEAI_ADMIN_PASSWORD` env vars (consumed by the `ensure_admin` management command on each boot — idempotent).
- **`get_apps` is cached** with `_is_app_running_cached` (5s TTL via Django's locmem cache, per worker). Mutating actions (install/start/stop/uninstall/delete/save_env) invalidate that folder's entry. There's a manual `POST /manager/refresh/` to clear the whole cache from the UI.
- **Healthcheck endpoint** is at `/health` (public, no auth). The Docker healthcheck in `docker-compose.yml` hits it. Returns `{status, version, debug, plugins}`.
- **Tests live in `core/tests.py` and `module_manager/tests.py`.** Run with `python manage.py test` (needs `SECRET_KEY` in env). `subprocess.run` is mocked — no Docker required in CI.
- **CI in `.github/workflows/`:** `ci.yml` runs ruff lint + tests on Python 3.11/3.12; `docker.yml` builds and pushes the kernel image to `ghcr.io/queai-project/queai-kernel` on tags and main.
- **REST API lives in `core/api/`** under `/api/v1/`. Same operations as the UI but JSON. Auth is bearer-token only (no Django sessions); the token is `QUEAI_API_TOKEN` from `.env`, auto-generated in DEBUG mode. `@api_token_required` uses `hmac.compare_digest`. OpenAPI 3 schema is hand-built in `core/api/openapi.py` — no DRF, no drf-spectacular. Swagger UI at `/api/v1/docs` (loads from unpkg).
- **`cli/queai_cli`** is a separate pip package. Excluded from the kernel's ruff config because it has its own `requires-python = ">=3.10"`. Install with `pipx install ./cli`. Config at `~/.config/queai/config.toml` (chmod 0600), overridable via `QUEAI_ENDPOINT` and `QUEAI_API_TOKEN` env vars.
- **`requirements.txt` includes `djangorestframework` but DRF is not in `INSTALLED_APPS`** and nothing imports it — it's dead weight, not a hint that DRF is in use.
- **`favicon.ico` and `logo.png` at the repo root are tracked binaries** (logo.png is ~1.4 MB). Don't accidentally rewrite them.
