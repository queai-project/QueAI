# Arquitectura Técnica - QueAI

## Visión general
QueAI se compone de un kernel Django y un ecosistema de módulos Docker conectados por una red compartida con Traefik como punto de entrada HTTP.

Componentes principales:

- **Traefik**: enruta tráfico por prefijos (`PathPrefix`) a kernel y módulos.
- **Django Kernel**: UI + lógica de catálogo + operaciones Docker.
- **SQLite**: estado de módulos detectados/instalados.
- **Plugins**: servicios independientes (típicamente FastAPI) en `plugins/<module>/`.

## Flujo de red
1. Cliente accede a `http://localhost/`.
2. Traefik dirige `PathPrefix('/')` al servicio `django-kernel`.
3. Cuando se abre un módulo, Traefik enruta `PathPrefix('/api/<module>')` al contenedor del plugin correspondiente.

## Flujo funcional del catálogo
1. Vista `GET /store/` escanea `plugins/`.
2. Para cada carpeta válida (`manifest.json` + `docker-compose.yml`), sincroniza metadatos en `AvailableApp`.
3. Evalúa estado de ejecución con `docker-compose -f <compose> top`.
4. Renderiza UI con acciones disponibles por estado.

## Modelo de datos principal
Tabla `AvailableApp`:

- `name`
- `folder_name`
- `display_name`
- `logo`
- `ui_entry_point`
- `configuration_entry_point`
- `documentation_entry_point`
- `version`
- `description`
- `author`
- `lic`
- `is_installed`

## Endpoints internos (kernel)
Base: `/store/`

- `GET /store/`: catálogo local y estado.
- `POST /store/install/`: `docker-compose up -d --build --force-recreate`.
- `POST /store/start/`: inicia módulo detenido.
- `POST /store/stop/`: detiene módulo.
- `POST /store/uninstall/`: `down --rmi all --volumes`.
- `GET /store/logs/<folder>/`: últimos logs.
- `GET /store/get_env/<folder>/`: carga/crea `.env`.
- `POST /store/save_env/`: guarda `.env` y aplica cambios.
- `GET /store/marketplace/`: catálogo remoto.
- `POST /store/download/`: clona plugin al directorio local.
- `GET /store/stats/<folder>/`: CPU/RAM/red de contenedores del módulo.
- `GET /store/dashboard/`: tablero de monitoreo.

## Estructura de carpetas relevante

```text
QueAI/
├── core/                    # Configuración Django
├── app_store/               # Lógica del hub de módulos
├── plugins/                 # Módulos instalables
├── docs/                    # Documentación
├── docker-compose.yml       # Traefik + Kernel
├── Dockerfile               # Imagen del Kernel
└── install.sh               # Instalación automática
```

## Decisiones actuales
- El kernel usa socket Docker del host (`/var/run/docker.sock`) para operar módulos.
- Los módulos no exponen puertos host; Traefik los publica por prefijo de ruta.
- El marketplace remoto usa un registro JSON centralizado.

## Riesgos operativos a considerar
- Exponer Docker socket al contenedor kernel implica alto privilegio operativo.
- `DEBUG=True` y `ALLOWED_HOSTS=["*"]` son adecuados para desarrollo, no para producción.
- La desinstalación elimina imágenes y volúmenes del módulo (`--rmi all --volumes`).
