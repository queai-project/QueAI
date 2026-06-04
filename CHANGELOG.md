# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versionado: [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- *(en preparación: gobernanza OSS completa, nueva documentación
  profesional, branding consolidado — ver `docs/ROADMAP.md`)*

---

## [1.0.0-rc1] — 2026-06-03

Primer *release candidate*. El núcleo del kernel está completo,
estable, con auth, observabilidad, API REST + CLI, healthcheck real,
backup/restore. Pendiente para v1.0 final: gobernanza OSS completa,
docs profesionales y branding.

### Added
- **Auth Django obligatorio** en `/manager/`, `/marketplace/`,
  `/monitor/`, `/account/`, `/audit/`. Login en `/login/`, logout
  en `/logout/`.
- **Management command `ensure_admin`** para autocreación del
  superuser desde `QUEAI_ADMIN_USER` / `QUEAI_ADMIN_PASSWORD` con
  rotación opcional.
- **Endpoint `/health`** público.
- **API REST `/api/v1/*`** con bearer token (`QUEAI_API_TOKEN`),
  Swagger UI en `/api/v1/docs`, OpenAPI 3 en `/api/v1/openapi.json`.
- **CLI `queai`** instalable con `pipx install ./cli`: comandos
  `health`, `list`, `show`, `install`, `start`, `stop`, `uninstall`,
  `delete`, `logs [-f]`, `stats`, `env [--edit]`, `marketplace`,
  `download`, `audit`, `backup`, `restore [--apply]`.
- **Healthcheck por plugin** que invoca `healthcheck_entry_point`
  del manifest, con cache de 5s y estado `starting` durante el
  grace period tras `install` / `start` / `save_env`.
- **Audit log** con modelo `AuditEvent` y auto-purga configurable
  (`QUEAI_AUDIT_MAX_EVENTS` / `QUEAI_AUDIT_KEEP_AFTER_PURGE`).
- **Logs en vivo (SSE)** por plugin con límite de 2 streams
  simultáneos.
- **Backup / restore *light*** (db.sqlite3 + .env del kernel + .env
  de cada plugin) accesible solo desde CLI / API.
- **Vista `/manager/app/<folder>/`** con tabs `.env`, Logs, Avanzado.
- **Wizard de primer arranque** `/welcome/`.
- **Página `/account/`** con cambio de password.
- **Instalador no-destructivo** multi-distro Linux (apt/dnf/yum/pacman)
  + macOS (brew). Servido desde `https://queai.dev/install.sh`.
- **CI con GitHub Actions** (`ci.yml`: lint con `ruff` + tests en
  Python 3.11/3.12).
- **Workflow espejo** (`sync-installer.yml`) que mantiene
  `queai.dev/install.sh` sincronizado con `install.sh` del kernel.
- **3 plugins oficiales** publicados como repos independientes:
  OCR (Tesseract), STT (faster-whisper), TTS (Piper).
- **Plantilla de plugin** en repo separado `queai-project/QueAI-Plugin-Template`.
- **Documentación** inicial:
  `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md`,
  `docs/PLUGIN_DEVELOPMENT.md`, `docs/API_REFERENCE.md`,
  `docs/PRODUCTVISION.md`, `docs/ROADMAP.md`, `CLAUDE.md`.

### Changed
- **Puerto del kernel**: `:80` → `:8080`; Traefik dashboard a `:9090`.
- **Red Docker compartida**: `odoo_network` → `queai_network`.
- **`runserver` → `gunicorn`** (3 workers x 2 threads). Modo dev
  detrás de `QUEAI_DEV=true`.
- **`requirements.txt`** limpiado: fuera `djangorestframework` y
  `dotenv` (no usados). Dentro `gunicorn` y `whitenoise`.
- **Templates** consolidados con `core/templates/base.html` + context
  processor (versión visible en todas las pantallas) y rediseño
  minimalista en hub, marketplace, monitor y detalle.
- **Documentación interna** reescrita: rutas reales
  (`/manager/`, `/marketplace/`, `/monitor/`) en lugar del histórico
  `/store/`.
- **Positioning**: de "local-first" a "modular AI orchestrator —
  local, cloud o hybrid". Refleja que un plugin puede ser modelo
  local **o** thin proxy a una API pública.

### Fixed
- Plugin identifier: la API y la CLI ahora aceptan tanto el slug
  corto (`ocr_local_cpu`) como el folder completo
  (`QueAI-OCR-CPU-LOCAL-MS`) y normalizan internamente al folder
  real antes de invocar Docker.
- Traefik fijado a `v2.11` por incompatibilidad de negociación de
  API entre Traefik v3 y daemons Docker más viejos.
- Backup/restore eliminados de la UI web (quedan solo en CLI/API)
  por decisión de UX — operación delicada, no debe estar a un
  click de distancia.

### Removed
- Workflow `docker.yml` (publicaba la imagen a GHCR). Decidido que
  para v1.0 el `install.sh` local-build es suficiente.
- Marquee decorativo, cards "Use Cases" y "Principles" y "Big CTA"
  de la landing.

### Security
- `DEBUG=False` por defecto.
- `SECRET_KEY` requerido en producción (el kernel se rehúsa a
  arrancar sin él cuando `DEBUG=False`).
- `QUEAI_API_TOKEN` requerido en producción con la misma regla.
- Cookies seguras + headers anti-XSS / clickjacking cuando
  `DEBUG=False`.
- Token de API validado con `hmac.compare_digest` (timing-safe).
- Dashboard de Traefik protegido por basic-auth.

---

[Unreleased]: https://github.com/queai-project/QueAI/compare/v1.0.0-rc1...HEAD
[1.0.0-rc1]: https://github.com/queai-project/QueAI/releases/tag/v1.0.0-rc1
