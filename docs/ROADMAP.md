# Roadmap QueAI hacia v1.0 (lanzamiento Open Source)

> Documento de planificación. Vivo — actualizar conforme se avance.
> Última revisión: 2026-06-03 (Fase 0 + alineación + **Fase 1 completada**).

## Contexto

QueAI está en una etapa madura como kernel (descubrir, instalar, ejecutar, monitorear módulos), tiene 3 módulos funcionales (OCR, STT, TTS) en el registry, un RAG fuera de registry, una landing en [queai.dev](https://queai.dev) y un plugin template separado. Antes de abrirlo al público hay que cerrar la brecha entre lo que la landing promete y lo que el código realmente hace, endurecer el kernel y completar la gobernanza open source.

## Diagnóstico: brechas que bloquean el lanzamiento

### Brecha 1 — Landing vs realidad

| Landing dice | Realidad actual |
|---|---|
| `curl -fsSL https://get.queai.dev \| bash` | Dominio/instalador **no existe** todavía. |
| Dashboard en `localhost:8080` | `:8080` es **Traefik**. El hub está en `localhost/manager/`. |
| "5+ AI Modules" | Hay **3** en el registry (OCR, STT, TTS). |
| "Linux · macOS · Windows WSL2" | `install.sh` es **solo Debian/Ubuntu** (`apt-get`). |
| Demo: "Docker found ✓" | El instalador **purga** Docker existente sin avisar. |

### Brecha 2 — `install.sh` destructivo (queja activa de preusuarios)

1. `purge_old_docker` hace `apt-get remove --purge` de Docker/containerd/runc/buildx/compose-plugin **siempre** que detecta Docker — sin preguntar.
2. Borra `/var/lib/docker` y `/var/lib/containerd` → **arrasa imágenes, contenedores y volúmenes de otros proyectos** del usuario.
3. Borra `$HOME/QueAI` completo si existe, sin warning real.
4. Patrón `curl … | sudo bash` — anti-patrón de seguridad.
5. `sudo` global desde el inicio aunque Docker ya esté funcional.
6. Solo `apt-get` → no portable, contradice la landing.
7. No idempotente (correrlo dos veces rompe cosas).
8. No verifica grupo `docker` ni arquitectura (x86_64 vs arm64).

### Brecha 3 — Deuda técnica del kernel

- `SECRET_KEY='your-secret-key'`, `DEBUG=True`, `ALLOWED_HOSTS=['localhost']` por defecto en `core/settings.py`.
- **Sin autenticación**: cualquier persona con red al kernel puede `install/start/stop/uninstall/delete` módulos.
- **Sin HTTPS** por defecto; Traefik con `--api.insecure=true` y dashboard `:8080` expuesto sin auth.
- `runserver` (devserver Django) usado en producción.
- `db.sqlite3` **committeado al repo** con datos.
- Red Docker se llama `odoo_network` — herencia de otro proyecto, mal branding.
- `version: '3.8'` en compose (obsoleto en Compose v2).
- `djangorestframework` en `requirements.txt` sin usarse.
- **Cero tests reales** (los `tests.py` están vacíos).
- **Sin CI/CD**.
- Sin healthcheck del kernel en compose.
- Registry URL **hardcoded** en `marketplace/views.py`; no se puede usar registry propio sin tocar código.
- `get_apps` es síncrono: escanea disco + corre `docker compose top` por plugin en cada visita.
- Sin búsqueda/filtros/paginación en `/marketplace/` ni en `/manager/`.
- UI mezcla español/inglés sin i18n.
- Sin sistema de actualización del propio kernel (solo de plugins).

### Brecha 4 — Documentación interna desactualizada

`README.md`, `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md` referencian rutas `/store/` y una app Django `app_store/` que **no existen**. La refactorización a `module_manager` / `marketplace` / `system_monitor` no se reflejó en docs. Fuente de verdad real: `core/urls.py`.

### Brecha 5 — Gobernanza open source ausente

Faltan: `LICENSE` en root del kernel, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md`, issue templates, PR template, tags de release, imagen pre-built del kernel en GHCR, README hub en la org `queai-project`.

---

## Fases del roadmap

### Fase 0 — Cerrar la brecha con la landing ✅ COMPLETADA (2026-06-02)

- [x] **Reescribir `install.sh`** no destructivo: detecta Docker existente, soporta Linux (apt/dnf/yum/pacman) + macOS (brew), opciones `--dry-run`, `--unattended`, `--dir`, `--branch`. Sintaxis verificada y smoke test pasado. **Pendiente**: servirlo desde `get.queai.dev` (DNS + redirect).
- [x] **Alinear puertos**: kernel movido a `:8080` (vía Traefik), Traefik dashboard movido a `:9090`. Ambos configurables (`QUEAI_PORT`, `QUEAI_TRAEFIK_DASHBOARD_PORT`).
- [x] **Sincronizar docs**: `README.md`, `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md`, `docs/PLUGIN_DEVELOPMENT.md`, `docs/API_REFERENCE.md` con rutas reales (`/manager/`, `/marketplace/`, `/monitor/`) y puerto `:8080`.
- [x] **Red `odoo_network` → `queai_network`**: migrados kernel + plugins en `plugins/` (OCR, STT, TTS) + repo hermano `QueAI-RAG-LOCAL-MS/` + `QueAI_Plugin_Template/` (template + ejemplo). Quitado `external: true` en el kernel (ahora la crea Compose). ⚠️ Plugins de terceros publicados antes de v1.0 deberán migrar manualmente — documentado en `OPERATIONS.md`.
- [x] **`db.sqlite3`**: verificado que nunca estuvo trackeado en git. `.gitignore` ampliado con patrones estándar (`.venv/`, `htmlcov/`, `staticfiles/`, etc.) y `plugins/.gitkeep` añadido.
- [x] **`LICENSE` MIT** añadido al root del kernel.

**Cambios adicionales aplicados como parte de Fase 0** (no en el plan original):
- `docker-compose.yml` del kernel: quitado `version: '3.8'`, añadido `healthcheck` del kernel, contenedores renombrados a `queai_kernel` y `queai_traefik`, `restart: unless-stopped`.
- `.env.example` reescrito con `QUEAI_PORT`, `QUEAI_TRAEFIK_DASHBOARD_PORT`, `SECRET_KEY`, `ALLOWED_HOSTS` documentados.
- `core/settings.py`: `SECRET_KEY` default cambiado de `'your-secret-key'` a `'dev-insecure-change-me'`; `ALLOWED_HOSTS` parsea con trim de espacios y default `localhost,127.0.0.1`.

**Deuda residual de Fase 0** (no bloquea Fase 1, pero **sí bloquea publicación pública v1.0**):
- Configurar `get.queai.dev` para servir el `install.sh` (requiere acceso a DNS del dominio). Sin esto, el comando `curl -fsSL https://get.queai.dev | bash` que aparece en la landing **no funciona**. Alternativa: cambiar la landing al raw de GitHub mientras tanto.
- Crear el repo `queai-project/QueAI` (el código local apunta a esta URL, falta confirmar que existe en GitHub y migrar el push remoto).

### Alineación landing ↔ kernel ↔ template ✅ COMPLETADA (2026-06-02)

Trabajo adicional ejecutado después de Fase 0 para cerrar la brecha entre lo que la landing prometía y lo que existe:

- [x] **Landing reescrita** (`QueAI-LandingPage/index.html`):
  - Eliminados módulos que no existen (CHAT, RAG) de la grid principal; movidos a sección "Roadmap" con badge.
  - Eliminados badges "Cloud" de STT y TTS (los plugins reales son CPU local con Piper / faster-whisper).
  - Reemplazadas referencias a OpenAI / Anthropic / Deepgram / ElevenLabs / Coqui / Pinecone / ChromaDB / LlamaIndex por los stacks reales (Tesseract, faster-whisper, Piper).
  - Hero stats actualizados: "3 AI Modules" + "100% Local & Private" (antes "5+" y "2x Local & Cloud").
  - Arquitectura visual sin columna Cloud, refleja solo containers locales.
  - Use cases reescritos sin RAG / Chat LLM.
  - Principio "Hybrid by Design" reemplazado por "Docker-Native".
  - URLs GitHub corregidas a `queai-project/QueAI` (mayúsculas correctas) en lugar de `queai-project/queai`.
  - Meta tags SEO y `<title>` actualizados.
- [x] **Plugin template alineado** (`QueAI_Plugin_Template/`):
  - README.md: path absoluto hardcoded (`/home/juani/Documents/...`) reemplazado por `~/QueAI/plugins`.
  - Dockerfile del template y del ejemplo STT: Python 3.13.12 → 3.11-slim (alineado con kernel y plugins reales).
- [x] **Kernel apunta al repo correcto**: `install.sh`, `README.md`, `command.md`, `docs/OPERATIONS.md` ahora usan `github.com/queai-project/QueAI` en vez de `alejandrofonsecacuza/QueAI`.
- [x] **Soporte Windows documentado** (`docs/OPERATIONS.md` nueva sección):
  - WSL2 + Docker Desktop como vía oficial v1.0.
  - Recomendación de mantener el repo en `~/QueAI` dentro de WSL (no `/mnt/c/...`).
  - Limitaciones conocidas y plan post-v1.0 (`install.ps1` nativo).
  - Mención en `README.md`.

### Fase 1 — Endurecimiento técnico v1.0 ✅ COMPLETADA (2026-06-03)

- [x] **Auth Django** con sesiones: `@login_required` en todas las views de `module_manager`, `marketplace`, `system_monitor`. Vistas `/login/` y `/logout/` con `auth_views`. Template `core/templates/login.html` propio con estilo coherente.
- [x] **Management command `ensure_admin`**: crea superuser desde `QUEAI_ADMIN_USER` / `QUEAI_ADMIN_PASSWORD` en primer arranque. Idempotente. Soporta rotación de password con `QUEAI_ADMIN_ROTATE_PASSWORD=true`.
- [x] **Settings de producción**: `DEBUG=False` por defecto, `SECRET_KEY` obligatoria si no es modo dev (lanza error explícito en `__init__`), `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` parametrizables, cookies seguras y headers anti-XSS/clickjacking cuando `DEBUG=False`.
- [x] **gunicorn + whitenoise**: `entrypoint.sh` reescrito; `runserver` solo bajo `QUEAI_DEV=true`. `WhiteNoiseMiddleware` integrado, `STORAGES` con `CompressedManifestStaticFilesStorage` en prod, `collectstatic` en entrypoint.
- [x] **Endpoint `/health`** público (sin auth): reporta status, version, debug, plugins count. Healthcheck del compose actualizado para apuntar ahí.
- [x] **Traefik dashboard con basic-auth**: middleware `dashboard-auth` con `QUEAI_TRAEFIK_DASHBOARD_AUTH` (hash bcrypt vía htpasswd).
- [x] **`requirements.txt` limpio**: fuera `djangorestframework` y `dotenv`. Dentro `gunicorn`, `whitenoise`.
- [x] **Logging configurable**: handler `console`, formato `[time] LEVEL name: msg`, nivel desde `LOG_LEVEL`.
- [x] **Cache de `get_apps`**: helper `_is_app_running_cached` con TTL 5s. Invalidación en `install`/`start`/`stop`/`uninstall`/`delete`/`save_env_config`. Endpoint nuevo `POST /manager/refresh/` para forzar refresh manual.
- [x] **Tests mínimos** (11 tests pasando): `/health` sin auth, redirección a `/login` en rutas protegidas, render de login, `ensure_admin` con sus 4 escenarios, scan de plugins, `install`/`stop` mockean compose, `refresh` invalida cache.
- [x] **GitHub Actions**: `.github/workflows/ci.yml` (lint con ruff + tests en Python 3.11 y 3.12) y `.github/workflows/docker.yml` (build + push a `ghcr.io/queai-project/queai-kernel` en push a `main` o tag `v*`). Config de ruff en `pyproject.toml`.
- [x] App `core` añadida a `INSTALLED_APPS` (con `core/apps.py`) para que Django descubra el management command.

**Fuera de scope Fase 1** (movido a futuro):
- HTTPS / Let's Encrypt → post-v1.0 (decisión confirmada).
- `ruff format --check` en CI → opcional, expandiría scope a 22 archivos del código existente.

### Fase 2 — Completar el ecosistema prometido (3-4 semanas)

- [ ] **Módulo CHAT/LLM**: Ollama local + adaptadores OpenAI/Anthropic cloud. Es el más visible de la landing y hoy **no existe**.
- [ ] **Publicar RAG**: integrar `QueAI-RAG-LOCAL-MS` (carpeta hermana del repo) al registry oficial.
- [ ] Búsqueda y filtros en `/marketplace/` y `/manager/`.
- [ ] Categorías en el manifest (Local / Cloud / Hybrid).
- [ ] **Registry configurable**: `REGISTRY_URL` desde env, soporte de múltiples registries.
- [ ] Actualización del kernel desde la UI (pull de nueva imagen + rebuild).
- [ ] **i18n**: decidir idioma de UI (recomendado: inglés base + español como traducción).
- [ ] Onboarding: wizard de primer arranque (crear admin, sugerir módulos).

### Fase 3 — Gobernanza open source (1 semana, en paralelo)

- [ ] `CONTRIBUTING.md`
- [ ] `CODE_OF_CONDUCT.md` (Contributor Covenant)
- [ ] `SECURITY.md` (reporte de vulnerabilidades)
- [ ] `CHANGELOG.md` (formato Keep-a-Changelog)
- [ ] Issue templates: bug / feature / plugin proposal
- [ ] PR template
- [ ] Roadmap público en GitHub Projects (espejo de este archivo)
- [ ] README hub en la org `queai-project`
- [ ] Labels `good-first-issue` y `help-wanted`
- [ ] **Mover plugin template al kernel**: convertir `scripts/create_queai_plugin.py` (en `QueAI_Plugin_Template/`) en un comando `python manage.py create_plugin <NAME>`. Mantener el repo template solo como cookiecutter/template repo de GitHub.
- [ ] Tag `v1.0.0` cuando Fase 0 + 1 + 2 estén cerradas.

### Fase 4 — Crecimiento post-lanzamiento (continuo, no bloquea v1.0)

- [ ] Telemetría **opt-in** (count anónimo de instalaciones por módulo).
- [ ] Ratings/reviews en marketplace.
- [ ] CLI `queai` (install/start/stop/logs sin UI).
- [ ] Soporte GPU (NVIDIA Container Toolkit) detectado y auto-configurado.
- [ ] Backup/restore del estado completo (`plugins/` + DB + `.env`s).
- [ ] Más módulos: Vision, Embeddings, Diarization (referencias en otros repos hermanos del autor).

---

## Orden recomendado de ataque

1. **Semana 1** — Quick wins que cierran quejas activas: reescribir `install.sh` no-destructivo + arreglar docs del kernel + sacar `db.sqlite3` del repo.
2. **Quincena 2-3** — Fase 1 completa (endurecimiento).
3. **Mes 2** — Módulo CHAT/LLM + publicar RAG.
4. **Mes 2-3** — Resto de Fase 2 + Fase 3 en paralelo.
5. **Cuando todo lo anterior esté** — Tag `v1.0.0` y empuje público (Hacker News, r/selfhosted, awesome-selfhosted).

## Decisiones pendientes de confirmar con el equipo

- Puerto del kernel: ¿`:80` (actual) o `:8080` (alinear con landing)?
- Idioma de la UI: ¿español, inglés, o ambos con i18n?
- WSGI: ¿gunicorn (síncrono) o uvicorn (ASGI)?
- Auth: ¿solo password local, o JWT/SSO desde v1.0?
- ¿La landing migra a `localhost/manager/` o el kernel se mueve a `:8080`?
