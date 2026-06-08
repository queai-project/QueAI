# Technical architecture — QueAI

## Overview

QueAI consists of a **Django kernel** and an ecosystem of **Docker modules** connected by a shared network (`queai_network`), with **Traefik** as the HTTP entry point.

Main components:

- **Traefik**: routes traffic by prefix (`PathPrefix`) to the kernel and the modules. Listens on `:8473` of the host (configurable via `QUEAI_PORT`).
- **Django Kernel**: UI + catalog logic + Docker operations. Runs inside the `queai_kernel` container.
- **SQLite (`db.sqlite3`)**: local state of detected/installed modules. Not versioned.
- **Plugins**: independent services under `plugins/<module>/`, each with its own `docker-compose.yml`. **What they do internally is transparent to the kernel**: running a model on CPU, proxying an external API (OpenAI, Anthropic, ElevenLabs, etc.), chaining several steps in a pipeline — all valid as long as it respects the manifest contract and the `queai_network`.

## Network flow

```
[ browser ]
      │
      ▼   (host:8473)
┌───────────────┐
│    Traefik    │  ── PathPrefix(/) ───►  django-kernel (UI + control)
│ queai_network │  ── PathPrefix(/api/<plugin>) ───►  plugin container
└───────────────┘
```

1. The client hits `http://localhost:8473/`.
2. Traefik routes `PathPrefix(/)` → `kernel` service (`queai_kernel` container).
3. When a module is opened, Traefik routes `PathPrefix(/api/<module>)` → the plugin container.
4. Traefik's internal dashboard sits at `:9473` (also configurable, via `QUEAI_TRAEFIK_DASHBOARD_PORT`).

## Plugin model (what a plugin can be)

The kernel enforces a contract: a `manifest.json` declaring routes, a `docker-compose.yml` joining `queai_network`, and Traefik labels with `PathPrefix(/api/<name>)`. What happens inside the container is up to the author.

Valid patterns:

| Pattern | Example | Implications |
|---|---|---|
| Local CPU model | Tesseract OCR, faster-whisper STT, Piper TTS | The container loads the model into RAM; the host needs enough CPU/RAM |
| Local GPU model | Ollama with an LLM, a vision model | Requires `--gpus all` in the plugin's compose and NVIDIA Container Toolkit on the host |
| Thin proxy to an external API | Plugin that exposes `/transcribe` and internally calls the OpenAI Whisper API | The container uses almost no resources; needs outbound connectivity and a secret in its `.env` |
| Mixed pipeline | A "RAG" plugin that combines cloud embeddings with a local vector store | The plugin acts as its own internal orchestrator |
| OpenAI-compatible adapter | Plugin that offers `/v1/chat/completions` and decides local vs cloud per config | Lets the rest of the system see a single standard surface |

The kernel **does not distinguish** between these cases: to it, they're all containers with a URL under `/api/<name>`. The practical consequence is that swapping "CHAT local Ollama" for "CHAT proxy Anthropic" without affecting the rest of the modules is a plugin change, not a kernel change.

## Django apps (real mapping)

The kernel is split into three Django apps, each with a well-defined responsibility. **Source of truth for routes: `core/urls.py` and each app's `urls.py`.**

| App | Root path | Responsibility |
|---|---|---|
| `module_manager/` | `/manager/` | Local catalog, lifecycle (install/start/stop/uninstall/delete), `.env` editing, per-module logs. |
| `marketplace/` | `/marketplace/` | Remote catalog (registry), plugin download/update from Git. |
| `system_monitor/` | `/monitor/` | Dashboard for CPU/RAM/network of installed modules. |
| `core/` | `/` | Home and Django configuration (`settings`, `urls`). |

## Catalog flow

1. The `GET /manager/` view (`module_manager.views.get_apps`) scans `PLUGINS_DIR`.
2. For each valid folder (`manifest.json` + `docker-compose.yml`), metadata is synced into `AvailableApp` via `update_or_create`.
3. Per-plugin running state is evaluated with `docker compose -f <compose> top`.
4. Plugins that existed in the DB but are no longer on disk get `_cleanup_missing_plugin_docker_artifacts` (label-based sweep `com.docker.compose.project=<folder>` → removes containers, networks, volumes and orphan images), and their row is deleted.
5. The UI is rendered with the actions available for each state.

> `get_apps` is also the reconciler: it runs on every visit. It's synchronous and can get slow with many plugins; it has a 5 s locmem cache per worker (`_is_app_running_cached`) and a manual `POST /manager/refresh/` endpoint to invalidate it.

## Core data model

`AvailableApp` table (`module_manager/models.py`):

- `name` (unique, from the manifest)
- `folder_name`
- `display_name`
- `logo`
- `ui_entry_point`
- `configuration_entry_point`
- `documentation_entry_point`
- `version`
- `description`
- `description_en` (optional EN translation)
- `author`
- `lic`
- `is_installed`

## Internal kernel endpoints

### `module_manager/` — local catalog manager

- `GET  /manager/` — catalog + state.
- `POST /manager/install/` — `docker compose up -d --build --force-recreate`.
- `POST /manager/start/` — `docker compose start`.
- `POST /manager/stop/` — `docker compose stop`.
- `POST /manager/uninstall/` — `docker compose down --rmi all --volumes --remove-orphans` (keeps folder and registry row).
- `POST /manager/delete/` — uninstall + `rmtree` of the plugin + registry row removal.
- `GET  /manager/logs/<folder>/` — last 150 log lines.
- `GET  /manager/get_env/<folder>/` — loads/creates `.env` (cloned from `.env.example` on first access).
- `POST /manager/save_env/` — saves `.env` and applies changes with `up -d --force-recreate`.
- `GET  /manager/logo/<plugin>/<file>` — serves the plugin's logo from `assets/`.

### `marketplace/` — remote catalog

- `GET  /marketplace/` — lists plugins from the remote `register.json` (URL in `marketplace/views.py:REGISTRY_URL`).
- `POST /marketplace/download/` — clones/updates a plugin from Git in an ephemeral `alpine/git` container (see "Marketplace clone contract" below).

### `system_monitor/` — observability

- `GET /monitor/` — dashboard.
- `GET /monitor/stats/<folder>/` — JSON with CPU/RAM/network per module container (`docker stats --no-stream` filtered by compose label).

## Marketplace: clone contract

The kernel **does not clone from inside the container**, because that would leave the plugins owned by `root` and outside the host's filesystem. Instead, it launches an ephemeral container:

```bash
docker run --rm --user $HOST_UID:$HOST_GID \
  -v $HOST_PROJECT_PATH/plugins:/data \
  alpine/git clone <git_url> /data/<folder>
```

For this to work, the kernel's `docker-compose.yml` passes `HOST_PROJECT_PATH=${PWD}`, `HOST_UID=${UID}`, `HOST_GID=${GID}`. If you run the kernel outside Docker Compose, export those variables manually.

A repo that clones but doesn't contain a valid `manifest.json` is **rejected** and cleaned up.

## Relevant folder layout

```text
QueAI/
├── core/                       # Django config (settings, urls, asgi/wsgi)
├── module_manager/             # Catalog + plugin lifecycle
├── marketplace/                # Remote registry + download
├── system_monitor/             # CPU/RAM/network dashboard
├── plugins/                    # Installable modules (each is its own Git repo)
├── docs/                       # Documentation
├── locale/                     # gettext translations (es, en)
├── docker-compose.yml          # Traefik + Kernel + queai_network
├── Dockerfile                  # Kernel image
├── entrypoint.sh               # migrate + gunicorn
├── install.sh                  # Non-destructive multi-OS installer
├── .env.example                # Environment variables
└── LICENSE                     # MIT
```

## Current decisions

- The kernel uses the host's Docker socket (`/var/run/docker.sock`) mounted into `queai_kernel` to operate the modules.
- Modules do not expose host ports; Traefik publishes them by path prefix.
- The remote marketplace uses a `register.json` centralized on GitHub.
- The shared Docker network (`queai_network`) is created by the kernel's `docker-compose.yml` — plugins join it by declaring it as `external: true`.
- The hub port is **`:8473`** by default, aligned with the landing page at queai.dev. Configurable.

## Operational considerations

- Exposing the Docker socket to the kernel container implies high privilege.
- `DEBUG=True` and permissive `ALLOWED_HOSTS` are fine for development, not for production.
- All state-mutating views (`/manager/`, `/marketplace/`, `/monitor/`, `/account/`, `/audit/`) require login. Public routes: `/`, `/health`, `/login/`. The admin is auto-created on first boot from `QUEAI_ADMIN_USER`/`QUEAI_ADMIN_PASSWORD`. The REST API uses a bearer token (`QUEAI_API_TOKEN`).
- `delete_app` removes images, volumes and the module's entire folder (`--rmi all --volumes` + `rmtree`).
