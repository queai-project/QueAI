# QueAI

**Modular AI orchestrator. Local, cloud, hybrid — your stack.**

QueAI is an open-source runtime for AI capabilities. Each capability is a
Docker container with its own UI and REST API. A module can run a model
locally on CPU, proxy a public API (OpenAI, Anthropic, ElevenLabs), or
chain several together — the kernel routes, monitors and audits everything
from one place.

> Stable version: **`v1.0.1`** — first Open Source release line.

## What it solves

| Problem | How QueAI handles it |
|---|---|
| Every AI capability ships its own server, its own `.env`, its own port | The kernel discovers, installs and orchestrates each module as a decoupled Docker container |
| Wiring 3 models = 3 different stacks | One dashboard (`/manager`), one REST API (`/api/v1`), one CLI (`queai`) |
| Mixing local models and cloud APIs needs manual glue | A plugin can be a local CPU model or a thin proxy to a public API — same contract either way |
| Start/stop/configure is DevOps work | All actions from the UI or the CLI; the kernel drives Docker underneath |
| Production-safe out of the box | Mandatory auth, audit log, real healthchecks, CLI backup/restore |

## Core components

- `traefik`: HTTP routing by prefix; exposes the hub on `:8473`.
- `django-kernel`: Django backend + hub UI.
- `plugins/*`: independent modules (typically FastAPI containers, but anything that speaks HTTP works).
- `db.sqlite3`: local catalog state (not versioned in the repo).
- `queai` CLI: Python client to automate from scripts or CI.
- Docker network `queai_network`: shared between the kernel and all plugins.

Flow: client → Traefik → Django (`/manager`, `/marketplace`, `/monitor`, `/api/v1`) → Docker operations → modules.

## Requirements

- Docker Engine and Docker Compose v2 (`docker compose`)
- Git
- Linux (Debian/Ubuntu, Fedora/RHEL, Arch), macOS, or **Windows via WSL2** (see [`docs/OPERATIONS.md`](./docs/OPERATIONS.md))

## Quick start

### One-line install

```bash
curl -fsSL https://queai.dev/install.sh | bash
```

The installer is **non-destructive**: it detects an existing Docker setup and reuses it instead of reinstalling. Options:

```bash
bash install.sh --dry-run         # show what it would do without changing anything
bash install.sh --unattended      # no prompts
bash install.sh --dir ~/QueAI     # custom install directory
bash install.sh --branch develop  # different branch
```

### Manual install

```bash
git clone https://github.com/queai-project/QueAI.git
cd QueAI
cp .env.example .env
docker compose up -d --build
```

## URLs

- Hub:               `http://localhost:8473/`
- Module catalog:    `http://localhost:8473/manager/`
- Marketplace:       `http://localhost:8473/marketplace/`
- Monitor dashboard: `http://localhost:8473/monitor/`
- Traefik dashboard: `http://localhost:9473/dashboard/` (internal)

> The hub port is configurable via `QUEAI_PORT` in `.env`.

## Build a plugin

Full guide in [`docs/PLUGIN_DEVELOPMENT.md`](./docs/PLUGIN_DEVELOPMENT.md). Covers the minimal layout, `manifest.json`, `docker-compose.yml`, Traefik integration, `.env.example`, and a publication checklist.

## Documentation

- [`docs/README.md`](./docs/README.md) — index
- [`docs/PRODUCTVISION.md`](./docs/PRODUCTVISION.md) — product vision
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — technical architecture
- [`docs/OPERATIONS.md`](./docs/OPERATIONS.md) — operations and deployment
- [`docs/API_REFERENCE.md`](./docs/API_REFERENCE.md) — kernel REST API
- [`docs/PLUGIN_DEVELOPMENT.md`](./docs/PLUGIN_DEVELOPMENT.md) — plugin author guide
- [`docs/DESIGN_TOKENS.md`](./docs/DESIGN_TOKENS.md) — visual design tokens
- [`docs/SECURITY.md`](./docs/SECURITY.md) — security policy

## Project status

| Latest release | `v1.0.1` |
|---|---|
| Tests | passing |
| Lint | `ruff check .` clean |
| CI | `ci.yml` (lint + tests on Python 3.11/3.12) |
| Bilingual UI | Spanish by default, English via the navbar switch |

The core is fit for self-hosting today: mandatory auth, gunicorn, env-based
configuration, audit log, CLI backup/restore.

## Show your support

If QueAI is useful to you, **a GitHub star helps me know it does** — and helps other people find the project.

[![Star this repo](https://img.shields.io/github/stars/queai-project/QueAI?style=social)](https://github.com/queai-project/QueAI/stargazers)

## License

MIT — see [`LICENSE`](./LICENSE).
