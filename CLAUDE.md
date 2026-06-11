# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

QueAI is a Django-based **kernel/hub** that manages independent AI modules ("plugins") as Docker projects. It auto-discovers plugins from `plugins/`, installs/starts/stops them via `docker compose`, exposes them through a shared Traefik router on a single host port, and reports CPU/RAM/network from `docker stats`. Persistence is a single SQLite file (`db.sqlite3`); the catalog table is `AvailableApp` in `module_manager/models.py`.

**Status:** publicly launched as Open Source on **2026-06-08** (LinkedIn post by Alejandro Fonseca Cuza + Juana Iris Pérez, ~5k impressions day 1). Latest tag: **`v1.0.3`**. Stable; receiving real-user bug reports.

**Repos involved (all under [`queai-project`](https://github.com/queai-project) org):**
- `QueAI` — this repo, the kernel.
- `QueAI-Registry` — `register.json` (plugin catalog).
- `queai-project.github.io` — landing page served at `queai.dev`. Also hosts `install.sh` (mirrored by hand from this repo).
- `QueAI-OCR-CPU-LOCAL-MS`, `QueAI-STT-CPU-LOCAL-MS`, `QueAI-TTS-CPU-LOCAL-MS` — the three official plugins.
- `QueAI-Plugin-Template` — starter template for new plugins.

## Running the system

Normal operation is fully containerized — the kernel runs as the `django-kernel` container and shells out to `docker compose` on the host via the mounted Docker socket.

```bash
docker compose up -d --build       # start kernel + Traefik
docker compose logs -f django-kernel
docker compose down
```

**Default port is `:8473`** (NOT `:8080`). Traefik dashboard at `:9473`. Both fixed deliberately so the landing/README/docs can advertise them unconditionally. Configurable via `QUEAI_PORT` / `QUEAI_TRAEFIK_DASHBOARD_PORT` if a user needs another port (manual install only — the `curl | bash` installer aborts on port collision with instructions instead of dynamically reassigning).

URLs:

- `http://localhost:8473/` — kernel home (`core.views.home_view`). Redirects to `/login/` if unauth, then to `/welcome/` once logged in (session-tracked dismiss).
- `http://localhost:8473/manager/` — installed/available plugin catalog (module_manager).
- `http://localhost:8473/marketplace/` — remote registry browser.
- `http://localhost:8473/monitor/` — system_monitor dashboard.
- `http://localhost:8473/account/` — user account (password change).
- `http://localhost:8473/audit/` — audit log table with filters/pagination.
- `http://localhost:8473/welcome/` — onboarding wizard.
- `http://localhost:8473/api/<plugin>/...` — plugin routes (each plugin attaches its own Traefik `PathPrefix` label).
- `http://localhost:9473/dashboard/` — Traefik dashboard (internal, basic-auth).
- `http://localhost:8473/api/v1/*` — REST API (bearer token).
- `http://localhost:8473/i18n/setlang/` — Django language-switch endpoint.

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
SECRET_KEY=test-only QUEAI_API_TOKEN=test-only-token DEBUG=True \
  python manage.py test
```

32 tests at v1.0.3. `subprocess.run` is mocked — no Docker required in CI. **The `test_backup_returns_tar_with_metadata` test can fail locally on a developer machine if a plugin's `.env` was created with root permissions by a previous container run** (`PermissionError`). CI doesn't see this. Not a real bug; backup hardening to skip unreadable files is a TODO.

## Architecture

Three Django apps mounted under `core/urls.py`, each owning one concern:

- **`module_manager/`** — the catalog and lifecycle controller. `get_apps` (the `/manager/` view) walks `PLUGINS_DIR`, requires both `manifest.json` and `docker-compose.yml` to consider a folder valid, and `update_or_create`s an `AvailableApp` row from the manifest. Folders that vanish from disk trigger `_cleanup_missing_plugin_docker_artifacts` — a label-based sweep (`com.docker.compose.project=<folder>`) that removes containers, networks, volumes, and images before deleting the DB row. Install/start/stop/uninstall/delete each shell out via `_get_compose_command()` which prefers `docker compose` (v2 plugin) and falls back to `docker-compose` (legacy v1) only if v2 is absent — but the installer refuses to run on v1-only hosts (v1 crashes against Docker daemons ≥ 25.x with `KeyError: 'ContainerConfig'`).
- **`marketplace/`** — fetches a remote `register.json` (URL hard-coded in `marketplace/views.py:REGISTRY_URL`, points at `queai-project/QueAI-Registry`) with cache-busting headers, compares versions per plugin via `_safe_version_tuple`, and on download spawns a one-shot `alpine/git` container to clone into `plugins/<folder>`. **It does not clone from inside the kernel container**; it runs `docker run --rm -v $HOST_PROJECT_PATH/plugins:/data alpine/git clone …`, which is why the kernel needs `HOST_PROJECT_PATH`, `HOST_UID`, `HOST_GID` (set by `docker-compose.yml` from `${PWD}` / `${UID}` / `${GID}`). A repo that clones successfully but lacks `manifest.json` is rejected.
- **`system_monitor/`** — `/monitor/` dashboard plus `app_stats(folder_name)` JSON endpoint. Stats are collected by `docker ps --filter label=com.docker.compose.project=<folder.lower()>` followed by `docker stats --no-stream` with a custom `{{.ID}}/{{.CPUPerc}}/{{.MemUsage}}/{{.NetIO}}` format. The lowercasing is load-bearing because Compose normalizes project names.

Everything talks to Docker through `/var/run/docker.sock`, mounted into the kernel container in `docker-compose.yml`. The kernel and all plugins share a Docker network named **`queai_network`** — created by the kernel's compose, joined by each plugin's compose as `external: true`. If you ever destroy it, plugins lose routing.

## Plugin contract

Each `plugins/<folder>/` must contain:

- `manifest.json` with at least `name` (unique, stable), `display_name`, `version`, `ui_entry_point`, `logo`. Optional: `configuration_entry_point`, `documentation_entry_point`, `healthcheck_entry_point`, `description`, **`description_en`** (English translation; the Hub uses it when the active UI language is `en`), `author`, `license`.
- `docker-compose.yml` that joins `queai_network` (declared `external: true`) and adds Traefik labels with `PathPrefix(\`/api/<name>\`)` and `loadbalancer.server.port=8000`. Don't declare `version:` — obsolete in Compose v2.
- `assets/<logo>` served by `module_manager.views.plugin_logo`.
- Optional `.env.example` — when the user opens config for a plugin, `get_env_config` clones it to `.env` on first read.

See `docs/PLUGIN_DEVELOPMENT.md` for the full template. `plugins/QueAI-OCR-CPU-LOCAL-MS/` is the canonical working reference.

The three official plugins (OCR / STT / TTS) embed a copy of the kernel's **design tokens** (palette, DM Sans / DM Mono typography, radius scale) so they look like one product family. The single source of truth is `docs/DESIGN_TOKENS.md`. When that file changes, the plugin index.html files in each plugin repo must be updated by hand — there is no runtime CSS sharing because plugins are independent containers.

## Bilingual UI (Spanish default, English switch)

Wired in v1.0.0. Stack: Django `gettext` + `LocaleMiddleware` + `i18n_patterns` not used (URLs stay language-agnostic).

- `settings.LANGUAGE_CODE = "es"`, `LANGUAGES = [("es", …), ("en", …)]`, `LOCALE_PATHS = [BASE_DIR / "locale"]`.
- `MIDDLEWARE` order: `LocaleMiddleware` between `SessionMiddleware` and `CommonMiddleware`.
- Switch in the navbar (`base.html`) posts to `/i18n/setlang/` and the language is stored in a cookie (`django_language`).
- Translations live in `locale/{es,en}/LC_MESSAGES/django.{po,mo}`. Both `.po` and compiled `.mo` are tracked in git.
- **Regenerating the locale** without `gettext-bin`: run `python3 scripts/build_locale.py`. The script keeps a hand-written ES→EN map in code, builds the `.po` from it via `polib`, and compiles the `.mo`. This is a workaround for hosts (mine included) that don't have `msgfmt`/`msguniq` available.
- **`{% blocktrans %}` with embedded `{% url %}` tags:** use `{% url 'name' as var %}` outside the block and reference `{{ var }}` inside, otherwise Django raises `'blocktrans' doesn't allow other block tags`.
- **Multi-line `{% blocktrans %}`:** always add `trimmed` — without it, the msgid carries the literal template indentation, never matches the `.po` and stays untranslated.
- **JS strings** dynamic in `module_manager/static/js/apps.js` consume `window.i18n` populated by `module_manager.html` with `{% trans … %}` calls before the `<script src="apps.js">` include. Apps.js has a `t(key, fallback)` helper.
- **Flash messages** from Python views use `gettext as _` from `django.utils.translation`. There's a subtle gotcha in `marketplace/views.py`: the code uses `_` as a throwaway variable for tuple unpacks (`folder, _, _ = …`), which shadows the imported `_`. Renamed those to `_unused1` / `_unused2` so gettext keeps working in the same function.

## Things to know that aren't obvious from the code

- **Source of truth for routes is always `core/urls.py` + each app's `urls.py`** (not docs, not landing).
- **Source of truth for the kernel version is the `VERSION` file at the repo root** (since v1.0.3). `core.settings._read_kernel_version()` reads it with env-var override priority: `os.getenv("VERSION")` → `VERSION` file → empty. Older releases (≤ v1.0.2) read it from `.env`, which broke on upgrade because the installer preserves user `.env`s; users on those releases had a frozen version string. The installer's `bootstrap_env` strips any legacy `VERSION=` line from existing `.env` files on upgrade (idempotent — only touches that line).
- **Compose project name = folder name, lowercased**, because Compose lowercases by default. `system_monitor.views.app_stats` and `_compose_project_candidates` rely on this for label filtering. If you ever rename a plugin folder, the orphan-cleanup sweep is your safety net.
- **Uninstall vs Delete differ deliberately.** `uninstall_app` runs `down --rmi all --volumes --remove-orphans` and flips `is_installed=False` but keeps the folder and DB row so the module stays listed as available. `delete_app` additionally `rmtree`s `plugins/<folder>` and removes the row.
- **`get_apps` is also the reconciler.** Hitting `/manager/` re-scans disk, upserts rows, and prunes orphans on every request — there's no background job. Slow if you have many plugins because it runs `docker compose top` per plugin. It's cached with `_is_app_running_cached` (5s TTL via Django's locmem cache, per worker). Mutating actions (install/start/stop/uninstall/delete/save_env) invalidate that folder's entry. `POST /manager/refresh/` clears the whole cache from the UI.
- **Settings are production-ready by default.** `DEBUG=False`, `SECRET_KEY` is **required** (kernel refuses to start if missing and not in DEBUG mode), `QUEAI_API_TOKEN` same rule. `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` from env. When `DEBUG=False`, cookies are secure/httponly and anti-XSS/clickjacking headers are on.
- **Auth is mandatory.** Every view in `module_manager`, `marketplace`, `system_monitor`, plus `/account/`, `/audit/`, `/welcome/` uses `@login_required`. Public routes: `/health`, `/login/`, `/logout/`. `home_view` (`/`) is also `@login_required`-equivalent: redirects unauth users to `/login/` and authenticated users to `/welcome/` if they haven't dismissed it. Bootstrap admin via `QUEAI_ADMIN_USER` + `QUEAI_ADMIN_PASSWORD` env vars (consumed by the `ensure_admin` management command on each boot — idempotent). The `install.sh` prompts interactively for these on first install or generates a random password in `--unattended` mode (shown in the final banner exactly once).
- **`install.sh` highlights** (see `install.sh` and `docs/OPERATIONS.md` for full detail):
  - **Refuses to run on docker-compose v1**-only hosts since v1.0.3 — v1 (last released 2021, EOL 2023) crashes against modern Docker daemons. The script aborts up front with a one-line install hint for v2 (`apt-get install docker-compose-plugin` etc.). It does NOT install v2 automatically or prompt.
  - **Auto-generates `SECRET_KEY` (50 bytes) and `QUEAI_API_TOKEN` (40 bytes)** on first install if missing. Idempotent — doesn't rotate existing values.
  - **`ensure_port_free` skips its own check** if the kernel's own containers (`queai_kernel` or `queai_traefik`) are already running, because otherwise re-running the installer on an existing deployment would abort with "port 8473 in use" (held by QueAI itself). This is the "true idempotency" feedback from a community reviewer.
  - **`clone_or_update_repo`** does `git fetch` + `checkout -B branch origin/branch` + `git reset --hard origin/branch` — it never tries to merge. The install directory is fully owned by the installer; local commits are not expected.
  - **Cache-bust + post-rebuild plugin behavior**: in `module_manager/static/js/apps.js`, `openApp(url)` appends `?_t=Date.now()` to the iframe src so a plugin rebuild is reflected immediately without browser refresh. The plugin iframe modal in `module_manager.html` is capped at `1200px` centered, not full-screen (it was the latter pre-v1.0.0; users complained that plugin contents centered at 980px looked weird flanked by empty bands).
- **Healthcheck endpoint** is at `/health` (public, no auth). The Docker healthcheck in `docker-compose.yml` hits it. Returns `{status, version, debug, plugins}`. Per-plugin healthcheck lives at `/api/v1/plugins/<folder>/healthcheck` and probes the manifest's `healthcheck_entry_point` via `core/healthcheck.py` (5s file-based cache; `mark_starting(folder)` sets a 60s grace window after install/start/save_env during which a fail is reported as `starting`, not `down`). The cache is **file-based, not locmem**, so the `starting` flag set by one gunicorn worker is visible to all others — critical bug we hit pre-v1.0.0.
- **Tests live in `core/tests.py` and `module_manager/tests.py`.** Run with `python manage.py test` (needs `SECRET_KEY` AND `QUEAI_API_TOKEN` in env to import settings). `subprocess.run` is mocked — no Docker required in CI.
- **CI in `.github/workflows/ci.yml`:** ruff lint + tests on Python 3.11/3.12. No container registry; the `install.sh` does a local build. The previously existing `sync-installer.yml` was removed — keeping `queai.dev/install.sh` in sync with the kernel's `install.sh` is now manual (copy the file across, commit both repos). It's not a frequent operation; the trade-off was deemed worth the simplicity.
- **REST API lives in `core/api/`** under `/api/v1/`. Same operations as the UI but JSON. Auth is bearer-token only (no Django sessions); the token is `QUEAI_API_TOKEN` from `.env`, auto-generated in DEBUG mode if missing. `@api_token_required` uses `hmac.compare_digest`. OpenAPI 3 schema is hand-built in `core/api/openapi.py` — no DRF, no drf-spectacular. Swagger UI at `/api/v1/docs` (loads JS from jsDelivr).
- **`cli/queai_cli`** is a separate pip package. Excluded from the kernel's ruff config because it has its own `requires-python = ">=3.10"`. Install with `pipx install ./cli`. Config at `~/.config/queai/config.toml` (chmod 0600), overridable via `QUEAI_ENDPOINT` and `QUEAI_API_TOKEN` env vars.
- **Three observability/safety modules** (`core/healthcheck.py`, `core/audit.py`, `core/backup.py`):
  - `audit_record(action, source)` decorator wraps every mutating view in `module_manager`/`marketplace`. Auto-purges when `AuditEvent.objects.count() > QUEAI_AUDIT_MAX_EVENTS` (default 5000), keeping `QUEAI_AUDIT_KEEP_AFTER_PURGE` (default 4000). The audit decorator reads `manifest_folder_name` from POST or `folder_name` from kwargs for the target.
  - `backup.build_backup()` produces a `tar.gz` with `db.sqlite3` + the kernel's `.env` + each plugin's `.env`. **Does not include `plugins/` source.** The endpoint that downloads it (`GET /api/v1/backup`) is API-only — backup was removed from the web UI deliberately because the tar contains secrets and shouldn't be a click away.
  - SSE log streaming at `GET /api/v1/plugins/<folder>/logs/stream` is gated by `threading.BoundedSemaphore(2)` — gunicorn sync workers would hang otherwise. Two concurrent log tails max per kernel.
- **Plugin identifier is normalised at the API layer**: every endpoint accepts either `folder_name` (e.g. `QueAI-OCR-CPU-LOCAL-MS`) or `name` slug (`ocr_local_cpu`). `_get_app_or_404` resolves both. Always operate on `app.folder_name` internally — never the raw URL parameter — because Docker paths/labels use the folder name.
- **`AvailableApp.description_en` field** (model migration `0002_availableapp_description_en`) was added in v1.0.0 for the bilingual Hub. `get_apps` reads `manifest.get("description_en", "")` and stores it on each row. The card template picks it when `get_current_language() == 'en'` and the field is non-empty; falls back to `description` (Spanish) otherwise. The three official plugin manifests carry `description_en`; the `QueAI-Registry/register.json` also has `description_en` on every entry plus `schema_version: 2`.
- **`requirements.txt` includes `djangorestframework` but DRF is not in `INSTALLED_APPS`** and nothing imports it — it's dead weight, not a hint that DRF is in use.
- **`.gitattributes`** forces LF line endings on `*.sh`, `*.bash`, `Dockerfile`, `docker-compose*`, `entrypoint`, `install.sh`, plus `.py`/`.yml`/`.toml`. Added in v1.0.2 after a user with `core.autocrlf=true` (Windows/WSL default) cloned the repo, got CRLF in `entrypoint.sh`, and Docker rejected the script with the misleading `exec /entrypoint.sh: no such file or directory` (the actual missing file was `/bin/sh\r`, not `entrypoint.sh`).
- **Static assets**: `static/welcome-emoji.png` (Kyubit waving with a "WELCOME" sign, used on the welcome wizard) and `static/sad-emoji.png` (Kyubit looking sad, used on empty states in Hub / Monitor / Marketplace). The mascot is "Kyubit" — keep it.

## Release process

1. Code on `main`. CI green (`ruff check .` + `manage.py test`).
2. Bump `VERSION` file (e.g. `1.0.3` → `1.0.4`).
3. Add a `## [X.Y.Z] — YYYY-MM-DD` section to `CHANGELOG.md` with `Added` / `Changed` / `Fixed` / `Removed` / `Security` subsections and a "Notes for upgraders" block when relevant. **Always include both upgrade paths** (`curl | bash` and manual `git pull + docker compose up -d --build`) — the manual path needs explicit instructions when `.env` migration is required.
4. Update the `[X.Y.Z]: …` link reference at the bottom of `CHANGELOG.md`.
5. Update README `Stable version` line and `Latest release` table cell.
6. `git commit -m "release: vX.Y.Z" && git tag -a vX.Y.Z -m "..." && git push origin main && git push origin vX.Y.Z`.
7. Copy `install.sh` to `~/Documents/Works/QueAI-LandingPage/`, commit, push (the landing serves `queai.dev/install.sh`).
8. Create the GitHub Release manually at `https://github.com/queai-project/QueAI/releases/new?tag=vX.Y.Z`. Mark "Set as the latest release". `gh` CLI is not installed on the maintainer's box.
9. If the release breaks something for existing users, be ready to **rollback with `git reset --hard <previous-tag> && git push --force origin main`** plus deleting the bad tag locally and remotely. The maintainer's preferred approach is force-push (preserves clean linear history) over `git revert`. This was used the day of the launch to roll back v1.0.3/v1.0.4/v1.0.5 attempts — the *current* v1.0.3 is a re-tagging after a more careful attempt, not the same commit content as the failed first try.

## Future work (post-v1.0.x)

**Idea proposed by Alejandro that we agreed is fundamentally strong:**

- Each plugin exposes an **MCP server** (Model Context Protocol, Anthropic, Nov-2024) at `/api/<name>/mcp`, declared in `manifest.json` as `mcp_entry_point`.
- The kernel grows an `agent` module (or it ships as a downloadable plugin) with an LLM backend interchangeable via `.env` (`AGENT_BACKEND=ollama|anthropic|openai`).
- The agent discovers MCP servers of installed plugins automatically and uses them as tools.

Phases tentatively scoped:

- **Phase A** (v1.1.0): plugins expose MCP, no kernel changes. Each official plugin grows one tool: `extract_text` (OCR), `transcribe_audio` (STT), `synthesize_speech` (TTS).
- **Phase B** (v1.2.0): agent as installable plugin with LLM dispatch + cost/latency display + tool selection router.
- **Phase C** (v1.3.0+): agent gets kernel-management tools (install plugin, get logs, etc.) with explicit user approval modals.

Open questions: tool selection scaling beyond ~20 plugins, approval-required mode for mutating tools, default LLM backend (probably Ollama local for the "stays local-first" message). Worth opening a public RFC issue (`docs/PROPOSALS/0001-mcp-agent.md`) before any code.

## Working preferences (maintainer)

These come from working with Alejandro through the launch and immediately after; they're not in any doc, so they go here:

- **Spanish in conversation. English in code/docs/git.** Project documentation is English-only as of v1.0.3 (README, docs/, CHANGELOG, governance files, install.sh messages). The UI is bilingual. CLAUDE.md and memory are English (this file). Conversation with Alejandro is Spanish.
- **Don't push changes without testing the upgrade path.** The day of the launch we tagged v1.0.1 → v1.0.5 in quick succession trying to fix things and made it worse. The lesson: simulate the upgrade locally before tagging, including the case where an existing `.env` is preserved. The `install.sh` has functions that can be smoke-tested with `bash` stubs (see how `ensure_compose` was tested in the v1.0.3 commit message).
- **Don't add interactive prompts to `curl | bash` paths.** One-liners must remain one-liners. If the script needs a decision the user must make, abort with a clear error and a single command they can run, never prompt mid-flow.
- **Don't install things on the user's host without explicit consent.** The v1.0.4/v1.0.5 attempt to auto-install `docker-compose-plugin` was rightly rejected. The script can recommend, but the install command belongs to the user.
- **Manual rollbacks are preferred over forward-fix when the maintainer is upset.** Force-push to the last good tag, document the rollback in a CHANGELOG entry of the next release. This happened mid-launch and the right move is to honour the request first, debug after.
- **The maintainer reads commit messages.** Write them like a colleague onboarding into the project tomorrow — context first, mechanics second, no PR-template noise.
