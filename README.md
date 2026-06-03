# QueAI

QueAI es un kernel para gestionar módulos de IA desacoplados en un modelo tipo marketplace local: descubre módulos, los instala con Docker, permite configurarlos por `.env`, consultar logs y monitorear recursos desde una única UI.

> Estado: en preparación para lanzamiento v1.0 Open Source. El plan de salida vive en [`docs/ROADMAP.md`](./docs/ROADMAP.md).

## Características
- Descubrimiento automático de módulos en `plugins/`.
- Instalación, inicio, parada, desinstalación y borrado desde la web.
- Carga y edición de configuración `.env` por módulo, con recreación del contenedor al guardar.
- Logs por módulo en tiempo real (consulta bajo demanda).
- Dashboard de monitoreo de CPU, RAM y red.
- Marketplace remoto + descarga directa desde URL Git.

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
curl -fsSL https://raw.githubusercontent.com/queai-project/QueAI/main/install.sh | bash
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

## Licencia
MIT — ver [`LICENSE`](./LICENSE).

## Estado actual
Proyecto orientado a desarrollo/laboratorio. El endurecimiento para producción (auth, HTTPS, WSGI real, settings seguros) es parte de la Fase 1 del [`ROADMAP`](./docs/ROADMAP.md).
