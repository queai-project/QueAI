# Operations and deployment

## Requirements

- Docker Engine and Docker Compose v2 (`docker compose`).
- Git.
- Linux (Debian/Ubuntu, Fedora/RHEL, Arch), macOS, or **Windows via WSL2** (see the dedicated section below).

## Quick start

### Option A — automatic installer

```bash
curl -fsSL https://queai.dev/install.sh | bash
```

The installer is **non-destructive**: it detects an existing Docker setup and reuses it. Useful options:

```bash
bash install.sh --dry-run         # show what it would do without changing anything
bash install.sh --unattended      # no prompts (uses safe defaults)
bash install.sh --dir ~/QueAI     # custom install directory
bash install.sh --branch develop  # different branch
```

Recognized environment variables: `QUEAI_REPO_URL`, `QUEAI_BRANCH`, `QUEAI_DIR`.

### Option B — manual

```bash
git clone https://github.com/queai-project/QueAI.git
cd QueAI
cp .env.example .env
# Edit .env: set SECRET_KEY (mandatory if DEBUG=False),
# QUEAI_ADMIN_USER and QUEAI_ADMIN_PASSWORD, and the Traefik dashboard auth.
docker compose up -d --build
```

### First access

1. The kernel lives at `http://localhost:8473/`.
2. **Login is mandatory** at `/login/`. Credentials are whatever you set in `QUEAI_ADMIN_USER` / `QUEAI_ADMIN_PASSWORD` before starting.
3. If you didn't set them via env, create the admin manually:
   ```bash
   docker compose run --rm django-kernel python manage.py createsuperuser
   ```
4. To rotate the admin password without recreating the user, set `QUEAI_ADMIN_ROTATE_PASSWORD=true` in `.env` and restart.

### Main environment variables

| Variable | Default | Notes |
|---|---|---|
| `QUEAI_PORT` | `8473` | Hub port on the host |
| `QUEAI_TRAEFIK_DASHBOARD_PORT` | `9473` | Internal Traefik dashboard port |
| `QUEAI_TRAEFIK_DASHBOARD_AUTH` | `admin:queai` | user:bcryptHash — generate with `htpasswd -nbB admin <pwd>` |
| `DEBUG` | `False` | `True` in dev. If `False`, `SECRET_KEY` is required. |
| `SECRET_KEY` | (empty) | Mandatory in production. Generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | CSV list |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:8473` | CSV list of trusted CSRF origins |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `QUEAI_DEV` | `false` | If `true`, uses `runserver` with auto-reload instead of gunicorn |
| `QUEAI_GUNICORN_WORKERS` | `3` | Gunicorn processes |
| `QUEAI_GUNICORN_THREADS` | `2` | Threads per process |
| `QUEAI_ADMIN_USER` / `QUEAI_ADMIN_PASSWORD` | (empty) | If set, the superuser is created on first boot |
| `QUEAI_API_TOKEN` | (empty) | Bearer token for `/api/v1/*`. Mandatory in production. |

## Windows via WSL2

QueAI doesn't have a native Windows installer yet (planned for v1.1). The recommended path on v1.0 is **WSL2 + Docker Desktop**, which is exactly what the landing page promises.

### Prerequisites

1. **Windows 10/11 with WSL2 enabled**. From an elevated PowerShell:
   ```powershell
   wsl --install
   ```
   This installs WSL2 + a default distro (Ubuntu).
2. **Docker Desktop for Windows** with the WSL2 backend enabled:
   - Download from https://www.docker.com/products/docker-desktop/
   - In Settings → General → check **"Use the WSL 2 based engine"**.
   - In Settings → Resources → WSL Integration → enable integration with your distro.

### Installation

Open the WSL terminal (Ubuntu) and run **the same installer used on Linux**:

```bash
curl -fsSL https://queai.dev/install.sh | bash
```

Once it's up, the hub lives at `http://localhost:8473/` **from the Windows browser**, not from inside WSL — Docker Desktop forwards the ports to the Windows side automatically.

### Important recommendations

- **Keep the repo inside the WSL filesystem** (`~/QueAI`), not at `/mnt/c/...`. NTFS I/O through 9P is 5x–20x slower, and OCR/STT hit the disk hard. If the repo is on `C:\`, move it to `~/`.
- If Docker Desktop is closed, the containers stop. Set it to **start with Windows** if you want QueAI to survive reboots.
- Running `code .` from WSL opens VS Code with the correct remote and noticeably better performance than opening it on Windows against `\\wsl$\...`.

### Known WSL2 limitations

- The UID/GID model inside WSL is real, so the marketplace (which clones with `--user $UID:$GID`) works fine.
- GPU access via CUDA-WSL exists but the current plugins are CPU-only, so it doesn't apply to v1.0.
- Native Windows (PowerShell, without WSL) **is not supported** yet. An `install.ps1` is planned for post-v1.0.

## Working URLs

- Hub:               `http://localhost:8473/`
- Catalog:           `http://localhost:8473/manager/`
- Marketplace:       `http://localhost:8473/marketplace/`
- Monitor:           `http://localhost:8473/monitor/`
- Traefik dashboard: `http://localhost:9473/dashboard/` (internal)

> The hub port is configurable via `QUEAI_PORT` in `.env`.

## Common operations

```bash
docker compose up -d                    # bring everything up
docker compose ps                       # show status
docker compose logs -f django-kernel    # tail kernel logs
docker compose restart django-kernel    # restart the kernel without touching plugins
docker compose down                     # stop everything (volumes kept)
```

## Module management

From `http://localhost:8473/manager/` you can:

- **Install** a module: `docker compose up -d --build --force-recreate` on the module.
- **Start / Stop** a module.
- **Uninstall**: `down --rmi all --volumes --remove-orphans`. Keeps the folder and the registry row (still listed as available).
- **Delete**: same as uninstall + `rmtree` of the folder + registry row removal.
- **Edit `.env`** and reapply configuration (container recreate).
- **Read logs** for the module (last 150 lines, on demand).

## Marketplace

- The remote catalog is fetched from a `register.json` on GitHub (URL in `marketplace/views.py:REGISTRY_URL`).
- When downloading a module, the kernel runs `git clone` inside an auxiliary `alpine/git` container with the host's UID/GID, so files end up with the user's permissions.

## Monitoring

The `/monitor/` dashboard polls every few seconds:

- CPU
- RAM
- Network
- Container ID

Data source: `docker stats --no-stream` + `docker ps` filtered by label `com.docker.compose.project=<folder.lower()>`.

## Backup and restore

What to back up:

- The `plugins/` folder (plugins are independent Git repos; `git status` per plugin tells you whether there are uncommitted changes).
- `db.sqlite3` (catalog state).
- The kernel's `.env`.
- Each module's `.env`.

The `queai` CLI provides `queai backup` / `queai restore` for the light path (db + envs).

## Production security recommendations

Minimum before exposing to an untrusted network:

- `DEBUG=False`.
- A unique `SECRET_KEY` (regenerate it: `python -c "import secrets; print(secrets.token_urlsafe(50))"`).
- Strict `ALLOWED_HOSTS` (no `*`).
- HTTPS / TLS in front of the kernel (not bundled).
- Close or protect the Traefik dashboard (`:9473`).
- Be mindful of exposing `/var/run/docker.sock` to the kernel container — it implies root-equivalent privileges on the host.

## Troubleshooting

### A module doesn't show up in the catalog

- Make sure both `manifest.json` and `docker-compose.yml` exist in its folder.
- The `manifest.json` must be valid JSON and contain a `name` field.

### Install fails

- Tail the kernel logs: `docker compose logs -f django-kernel`.
- Try the module's build manually: `cd plugins/<module> && docker compose up --build`.
- Confirm the `queai_network` network exists: `docker network ls | grep queai`.

### Marketplace download doesn't work

- Confirm the host has internet connectivity.
- Verify that the module's Git URL is public.
- Verify `HOST_PROJECT_PATH`, `HOST_UID`, `HOST_GID` are set in the kernel's environment. If you started via `docker compose up`, the compose passes them from `${PWD}` / `${UID}` / `${GID}` already.

### Port 8473 is busy

Define a different port in `.env`:

```bash
QUEAI_PORT=9000
```

then recreate: `docker compose up -d --force-recreate`. Remember to update `CSRF_TRUSTED_ORIGINS` to match.

### Legacy plugins can't reach the kernel (network `odoo_network`)

From v1.0 onwards, the shared network is **`queai_network`** (previously `odoo_network`). Plugins built before that must update the `networks:` section of their `docker-compose.yml`. The official plugins (OCR, STT, TTS, RAG) are already migrated.
