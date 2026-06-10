# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

## [1.0.1] — 2026-06-10

First patch release after the public launch. Two themes:
follow-up on community feedback about installer idempotency, and
finishing the English translation pass that v1.0.0 left
half-done.

### Fixed

- **Installer is now truly idempotent on a host that already has
  QueAI deployed.** Re-running `curl | bash` used to abort at the
  port-check step with "port 8473 in use" — because the very
  QueAI deployment the user was upgrading was holding the port.
  The installer now detects its own `queai_kernel` /
  `queai_traefik` containers and skips the port check on
  reinstall, letting `docker compose up -d --build` do the
  refresh. Reported by a community reviewer right after the
  launch; fix matches their suggested implementation.

### Changed

- **`install.sh` translated to English end-to-end.** Every
  `[INFO]/[WARN]/[ERROR]` message, every step header, every
  prompt, every banner in the success summary. The control flow,
  function names, env vars, flag names and exit codes are
  unchanged.
- **Project documentation now fully in English.** The README
  already shipped in English in v1.0.0, but the rest was still
  in Spanish at launch. Translated in this release:
  - `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md` itself.
  - All issue templates (`bug_report`, `feature_request`,
    `plugin_proposal`, `config`) and the PR template.
  - Every page under `docs/` (PRODUCTVISION, ARCHITECTURE,
    OPERATIONS, PLUGIN_DEVELOPMENT, API_REFERENCE, SECURITY,
    DESIGN_TOKENS, index).
  - `CODE_OF_CONDUCT.md` is the official Contributor Covenant
    2.1 text, which is canonically published in English already,
    so it stays as-is.
- **README cleanup**: removed a duplicated "Arquitectura rápida"
  block (left over from a merge) and a dangling reference to a
  `docs/DEPLOYMENT.md` file that doesn't exist. Added a "Show
  your support" section with the GitHub stars shield.

### Notes for upgraders

- Existing installations: `curl -fsSL https://queai.dev/install.sh | bash`
  on a deployed host now upgrades the kernel code (`git reset
  --hard origin/main`) and rebuilds the container image without
  touching `.env`, `db.sqlite3`, installed plugins or admin
  credentials.
- Manual upgrade equivalent: `cd ~/QueAI && git pull &&
  docker compose up -d --build`.

---

## [1.0.0] — 2026-06-08

First stable Open Source release. The kernel moves from "stable rc
with docs/branding pending" to a publishable product: bilingual,
visually coherent with its official plugins, with an installer
that prompts for credentials and visual feedback during long
operations.

### Added

- **Bilingual ES/EN UI** via `gettext`: `LocaleMiddleware`,
  `ES · EN` switch in the navbar, embedded locale at
  `locale/{es,en}/` covering navbar, welcome, login, home, hub,
  marketplace, monitor, audit log, account, confirmation modals,
  Django flash messages and JS dynamic strings via `window.i18n`.
- **`AvailableApp.description_en`** + migration 0002: the plugin
  manifest can declare `description_en` and the Hub picks the
  version that matches the active language.
- **Visual feedback during long operations**: inline button
  spinner + persistent bottom-right overlay when running
  Download / Install / Stop / Resume / Update. No backend changes.
- **Interactive admin credentials prompt** in `install.sh`: asks
  for username + password with confirmation, length validation,
  and a blocklist of characters that break `.env`. In
  `--unattended` or without a TTY it generates a random urlsafe
  password and shows it once in the final banner.
- **Auto-generation of `SECRET_KEY` and `QUEAI_API_TOKEN`** on
  first boot (idempotent: won't rotate already-set values).
- **Port-in-use detection** in `install.sh` (with a fallback to
  manual install instructions) — the kernel port is fixed (see
  Changed).
- **`docs/DESIGN_TOKENS.md`** as the single source of truth for
  look & feel (palette, DM Sans/DM Mono typography, radius,
  principles). The 3 official plugins embed a copy of these
  tokens.
- **Reworked onboarding**: `/` → `/login/` → `/welcome/` on every
  first login; the welcome is skipped automatically if it was
  dismissed in the session. `?force=1` forces it.
- **Issue templates** (`bug_report`, `feature_request`,
  `plugin_proposal`), PR template and CODE_OF_CONDUCT (Contributor
  Covenant 2.1).
- **Plugin tooling**: `scripts/build_locale.py` to regenerate the
  locale without `gettext-bin` installed.

### Changed

- **Fixed kernel port: `:8473`** (Traefik dashboard `:9473`). The
  landing page, README and docs advertise the port unconditionally;
  the installer aborts with clear instructions if it's busy.
- **Unified look & feel across kernel and plugins**: flat palette
  `#141414` / `#1c1c1c` / `#262626`, no gradients, no
  glassmorphism, `14px` radius for cards / `9px` for buttons,
  DM Sans + DM Mono typography, language switch in the navbar.
- **Plugin iframe in the Hub**: capped at `1200px` and centered
  instead of full screen. Automatic cache-bust with
  `?_t=Date.now()` so a plugin rebuild is reflected immediately.
- **Login redirect** now lands on `/welcome/` (was `/manager/`).
- **`AvailableApp.description`** now also supports
  `description_en` in the `manifest.json`.
- **"Add to Hub" button in the Marketplace** renamed to
  **"Download"** (better reflects what it does: `git clone` to the
  filesystem; install is a separate second step).
- **Installer final banner** collapses the 4 kernel deep-links
  into a single `http://localhost:8473/` URL; the user discovers
  Hub/Marketplace/Monitor through the UI after the first login.

### Fixed

- **Plugins' Swagger `/docs`** is always served (was gated by
  `is_dev` and the STT compose forced production → 404).
- **Plugins downloaded with correct permissions** (`HOST_UID`/`GID`
  passed to the `alpine/git` container).
- **CSRF / login no longer break** when changing `QUEAI_PORT` from
  `install.sh`: the `.env` update keeps `CSRF_TRUSTED_ORIGINS`
  consistent.
- **Multi-line `{% blocktrans %}`** (home, welcome) now uses
  `trimmed` so the normalized msgid is what actually gets
  translated.

### Removed

- Internal planning notes (`docs/ROADMAP.md`).
- `sync-installer.yml` workflow (the installer is copied by hand
  to the landing-page repo).

---

## [1.0.0-rc1] — 2026-06-03

First release candidate. The kernel core is complete and stable,
with auth, observability, REST API + CLI, real healthcheck,
backup/restore. Pending for the final v1.0: full OSS governance,
professional docs and branding.

### Added

- **Mandatory Django auth** on `/manager/`, `/marketplace/`,
  `/monitor/`, `/account/`, `/audit/`. Login at `/login/`, logout
  at `/logout/`.
- **`ensure_admin` management command** for superuser
  auto-creation from `QUEAI_ADMIN_USER` / `QUEAI_ADMIN_PASSWORD`
  with optional rotation.
- **Public `/health`** endpoint.
- **REST API `/api/v1/*`** with bearer token (`QUEAI_API_TOKEN`),
  Swagger UI at `/api/v1/docs`, OpenAPI 3 at
  `/api/v1/openapi.json`.
- **`queai` CLI** installable with `pipx install ./cli`: commands
  `health`, `list`, `show`, `install`, `start`, `stop`,
  `uninstall`, `delete`, `logs [-f]`, `stats`, `env [--edit]`,
  `marketplace`, `download`, `audit`, `backup`,
  `restore [--apply]`.
- **Per-plugin healthcheck** invoking the manifest's
  `healthcheck_entry_point`, with a 5 s cache and a `starting`
  state during the grace period after
  `install` / `start` / `save_env`.
- **Audit log** with `AuditEvent` model and configurable
  auto-purge (`QUEAI_AUDIT_MAX_EVENTS` /
  `QUEAI_AUDIT_KEEP_AFTER_PURGE`).
- **Live logs (SSE)** per plugin with a cap of 2 simultaneous
  streams.
- **Light backup / restore** (db.sqlite3 + the kernel's `.env` +
  each plugin's `.env`) accessible only from CLI / API.
- **`/manager/app/<folder>/`** view with `.env`, Logs, Advanced
  tabs.
- **First-boot wizard** at `/welcome/`.
- **`/account/` page** with password change.
- **Non-destructive installer** for multi-distro Linux
  (apt/dnf/yum/pacman) + macOS (brew). Served from
  `https://queai.dev/install.sh`.
- **CI with GitHub Actions** (`ci.yml`: lint with `ruff` + tests
  on Python 3.11/3.12).
- **Mirror workflow** (`sync-installer.yml`) keeping
  `queai.dev/install.sh` in sync with the kernel's `install.sh`.
- **3 official plugins** published as independent repos: OCR
  (Tesseract), STT (faster-whisper), TTS (Piper).
- **Plugin template** in a separate
  `queai-project/QueAI-Plugin-Template` repo.
- **Initial documentation**: `docs/ARCHITECTURE.md`,
  `docs/OPERATIONS.md`, `docs/PLUGIN_DEVELOPMENT.md`,
  `docs/API_REFERENCE.md`, `docs/PRODUCTVISION.md`, `CLAUDE.md`.

### Changed

- **Kernel port**: `:80` → `:8080`; Traefik dashboard at `:9090`.
- **Shared Docker network**: `odoo_network` → `queai_network`.
- **`runserver` → `gunicorn`** (3 workers × 2 threads). Dev mode
  behind `QUEAI_DEV=true`.
- **`requirements.txt`** trimmed: out `djangorestframework` and
  `dotenv` (unused). In `gunicorn` and `whitenoise`.
- **Templates** consolidated under `core/templates/base.html` +
  a context processor (the version is visible on every screen)
  and a minimalist redesign across hub, marketplace, monitor and
  detail.
- **Internal documentation** rewritten: real routes
  (`/manager/`, `/marketplace/`, `/monitor/`) instead of the old
  `/store/`.
- **Positioning**: from "local-first" to "modular AI orchestrator
  — local, cloud or hybrid". Reflects the fact that a plugin can
  be a local model **or** a thin proxy to a public API.

### Fixed

- Plugin identifier: the API and the CLI now accept both the
  short slug (`ocr_local_cpu`) and the full folder
  (`QueAI-OCR-CPU-LOCAL-MS`) and normalize internally to the
  real folder before calling Docker.
- Traefik pinned to `v2.11` because of an API-negotiation
  incompatibility between Traefik v3 and older Docker daemons.
- Backup/restore removed from the web UI (CLI/API only) by UX
  decision — sensitive operation, shouldn't be one click away.

### Removed

- `docker.yml` workflow (which used to publish the image to
  GHCR). Decided that for v1.0 the local-build `install.sh` is
  enough.
- The decorative marquee, the "Use Cases" / "Principles" cards
  and the "Big CTA" of the landing page.

### Security

- `DEBUG=False` by default.
- `SECRET_KEY` required in production (the kernel refuses to
  start without it when `DEBUG=False`).
- `QUEAI_API_TOKEN` required in production with the same rule.
- Secure cookies + anti-XSS / clickjacking headers when
  `DEBUG=False`.
- API token validated with `hmac.compare_digest` (timing-safe).
- Traefik dashboard protected with basic auth.

---

[1.0.1]: https://github.com/queai-project/QueAI/releases/tag/v1.0.1
[1.0.0]: https://github.com/queai-project/QueAI/releases/tag/v1.0.0
[1.0.0-rc1]: https://github.com/queai-project/QueAI/releases/tag/v1.0.0-rc1
