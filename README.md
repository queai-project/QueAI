# QueAI

QueAI es un kernel para gestionar módulos de IA desacoplados en un modelo tipo marketplace local: descubre módulos, los instala con Docker, permite configurarlos por `.env`, consultar logs y monitorear recursos desde una única UI.

## Características
- Descubrimiento automático de módulos en `plugins/`.
- Instalación, inicio, parada y desinstalación desde la web.
- Carga y edición de configuración `.env` por módulo.
- Logs por módulo en tiempo real (consulta bajo demanda).
- Dashboard de monitoreo de CPU, RAM y red.
- Marketplace remoto + descarga directa desde URL Git.

## Arquitectura rápida
- `traefik`: ruteo HTTP por prefijos.
- `django-kernel`: backend y UI del hub.
- `plugins/*`: módulos independientes (normalmente contenedores FastAPI).
- `db.sqlite3`: persistencia local del catálogo.

Flujo: cliente -> Traefik -> Django (`/store/*`) -> operaciones Docker -> módulos.

## Requisitos
- Docker Engine
- Docker Compose plugin (`docker compose`)
- Git

## Ejecutar el proyecto
### Instalación automática
```bash
curl -sSL https://raw.githubusercontent.com/alejandrofonsecacuza/QueAI/main/install.sh | sudo bash
```

### Instalación manual
```bash
git clone https://github.com/alejandrofonsecacuza/QueAI.git
cd QueAI
docker compose up -d --build
```

## URLs
- Hub: `http://localhost/`
- Catálogo de apps: `http://localhost/store/`
- Marketplace: `http://localhost/store/marketplace/`
- Dashboard de monitoreo: `http://localhost/store/dashboard/`
- Dashboard Traefik: `http://localhost:8080/`

## Crear un plugin
La guía completa está en:

- [`docs/PLUGIN_DEVELOPMENT.md`](./docs/PLUGIN_DEVELOPMENT.md)

Incluye estructura mínima, `manifest.json`, `docker-compose.yml`, integración con Traefik, `.env.example` y checklist de publicación.

## Documentación
- [`docs/README.md`](./docs/README.md)
- [`docs/PRODUCTVISION.md`](./docs/PRODUCTVISION.md)
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)
- [`docs/OPERATIONS.md`](./docs/OPERATIONS.md)
- [`docs/API_REFERENCE.md`](./docs/API_REFERENCE.md)

## Estado actual
Proyecto orientado a desarrollo/laboratorio. Antes de usar en producción, revisar endurecimiento de seguridad, controles de acceso y políticas de despliegue.
