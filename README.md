# QueAI

**Modular AI orchestrator. Local, cloud, hybrid — your stack.**

QueAI is an open-source runtime for AI capabilities. Each capability is a
Docker container with its own UI and REST API. A module can run a model
locally on CPU, proxy a public API (OpenAI, Anthropic, ElevenLabs), or
chain several together — the kernel routes, monitors and audits everything
from one place.

> Estado: preparación para lanzamiento `v1.0` Open Source. Plan completo en [`docs/ROADMAP.md`](./docs/ROADMAP.md). Último estado etiquetado: `v1.0.0-rc1`.

## Qué resuelve

| Problema | Cómo lo aborda QueAI |
|---|---|
| Cada capacidad de IA viene con su propio servidor, su `.env`, su puerto | El kernel descubre, instala y orquesta cada módulo como contenedor Docker desacoplado |
| Conectar 3 modelos = 3 stacks distintos | Un solo dashboard (`/manager`), un solo API REST (`/api/v1`), un solo CLI (`queai`) |
| Mezclar modelos locales y APIs cloud requiere pegamento manual | Un plugin puede ser CPU local o un thin proxy a una API pública, el contrato es el mismo |
| Probar arrancar/parar/configurar es trabajo de DevOps | Acciones desde la UI o la CLI; el kernel maneja Docker por debajo |
| Producción seguro fuera de la caja | Auth obligatoria, audit log, healthchecks reales, backup/restore desde CLI |

## Componentes principales
- `traefik`: ruteo HTTP por prefijos, expone el hub en `:8080`.
- `django-kernel`: backend Django + UI del hub.
- `plugins/*`: módulos independientes (típicamente FastAPI, pero cualquier contenedor sirve).
- `db.sqlite3`: estado del catálogo (no versionado en el repo).
- `queai` CLI: cliente Python para automatizar desde scripts o CI.
- Red Docker `queai_network`: compartida entre kernel y todos los plugins.

Flujo: cliente → Traefik → Django (`/manager`, `/marketplace`, `/monitor`, `/api/v1`) → operaciones Docker → módulos.

## Arquitectura rápida
- `traefik`: ruteo HTTP por prefijos, expone el hub en `:8080`.
- `django-kernel`: backend Django + UI del hub.
- `plugins/*`: módulos independientes (típicamente contenedores FastAPI).
- `db.sqlite3`: persistencia local del catálogo (no versionado en el repo).
- Red Docker `queai_network`: compartida entre el kernel y todos los plugins.

Flujo: cliente → Traefik → Django (`/manager`, `/marketplace`, `/monitor`) → operaciones Docker → módulos.

## Requisitos
- Docker Engine y Docker Compose v2 (`docker compose`)
- Git
- Linux (Debian/Ubuntu, Fedora/RHEL, Arch), macOS, o **Windows vía WSL2** (ver [`docs/OPERATIONS.md`](./docs/OPERATIONS.md#windows-vía-wsl2))

## Ejecutar el proyecto

### Instalación automática
```bash
curl -fsSL https://queai.dev/install.sh | bash
```

El instalador es **no destructivo**: detecta Docker existente y lo reutiliza en vez de reinstalarlo. Opciones:

```bash
bash install.sh --dry-run         # ver qué haría sin ejecutar nada
bash install.sh --unattended      # sin preguntas
bash install.sh --dir ~/QueAI     # directorio personalizado
bash install.sh --branch develop  # otra rama
```

### Instalación manual
```bash
git clone https://github.com/queai-project/QueAI.git
cd QueAI
cp .env.example .env
docker compose up -d --build
```

## URLs
- Hub:                `http://localhost:8080/`
- Catálogo de apps:   `http://localhost:8080/manager/`
- Marketplace:        `http://localhost:8080/marketplace/`
- Dashboard monitor:  `http://localhost:8080/monitor/`
- Dashboard Traefik:  `http://localhost:9090/dashboard/` (interno)

> El puerto del hub es configurable vía `QUEAI_PORT` en `.env`.

## Crear un plugin
La guía completa está en [`docs/PLUGIN_DEVELOPMENT.md`](./docs/PLUGIN_DEVELOPMENT.md). Incluye estructura mínima, `manifest.json`, `docker-compose.yml`, integración con Traefik, `.env.example` y checklist de publicación.

## Documentación
- [`docs/README.md`](./docs/README.md)
- [`docs/PRODUCTVISION.md`](./docs/PRODUCTVISION.md)
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)
- [`docs/OPERATIONS.md`](./docs/OPERATIONS.md)
- [`docs/API_REFERENCE.md`](./docs/API_REFERENCE.md)
- [`docs/PLUGIN_DEVELOPMENT.md`](./docs/PLUGIN_DEVELOPMENT.md)
- [`docs/ROADMAP.md`](./docs/ROADMAP.md) — plan hacia v1.0 / lanzamiento Open Source

## Estado del proyecto

| Etiqueta más reciente | `v1.0.0-rc1` (primer release candidate) |
|---|---|
| Tests | 29/29 pasando |
| Lint | `ruff check .` limpio |
| CI | `ci.yml` (lint + tests py3.11/3.12) y `sync-installer.yml` (espejo del instalador) |
| Pendiente antes de `v1.0` | gobernanza OSS (CONTRIBUTING/CODE_OF_CONDUCT/SECURITY/CHANGELOG/templates) y documentación profesional completa — ver [`docs/ROADMAP.md`](./docs/ROADMAP.md) |

El núcleo es apto para self-host hoy: auth obligatoria, gunicorn,
configuración por env, audit log, backup/restore vía CLI. HTTPS y
reverse proxy se cubren en `docs/DEPLOYMENT.md` (en preparación).

## Licencia

MIT — ver [`LICENSE`](./LICENSE).
