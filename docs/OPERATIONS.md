# Operación y Despliegue

## Requisitos
- Docker Engine y Docker Compose plugin.
- Git.
- Linux recomendado para flujo completo de instalación automática.

## Inicio rápido
### Opción A: instalación automática

```bash
curl -sSL https://raw.githubusercontent.com/alejandrofonsecacuza/QueAI/main/install.sh | sudo bash
```

### Opción B: manual

```bash
git clone https://github.com/alejandrofonsecacuza/QueAI.git
cd QueAI
docker compose up -d --build
```

## URLs de trabajo
- Hub: `http://localhost/`
- Catálogo: `http://localhost/store/`
- Marketplace: `http://localhost/store/marketplace/`
- Monitoreo: `http://localhost/store/dashboard/`
- Traefik dashboard: `http://localhost:8080/`

## Operaciones frecuentes
### Levantar servicios

```bash
docker compose up -d
```

### Ver estado

```bash
docker compose ps
```

### Ver logs del kernel

```bash
docker compose logs -f django-kernel
```

### Detener todo

```bash
docker compose down
```

## Gestión de módulos
Desde `http://localhost/store/` puedes:

- Instalar módulo (build + up).
- Iniciar/Detener módulo.
- Desinstalar módulo y limpiar recursos.
- Editar `.env` y reaplicar configuración.
- Consultar logs del módulo.

## Marketplace
- El catálogo remoto se obtiene desde un `register.json` en GitHub.
- Al descargar un módulo, el kernel ejecuta un `git clone` dentro de un contenedor auxiliar hacia `plugins/`.

## Monitoreo
El dashboard consulta cada pocos segundos:

- CPU
- RAM
- Red
- ID de contenedor

Fuente de datos: `docker stats --no-stream` y `docker ps` filtrado por label compose.

## Respaldo y restauración
Elementos a respaldar:

- Carpeta `plugins/`
- `db.sqlite3`
- `.env` del proyecto
- `.env` de cada módulo

## Seguridad recomendada para producción
- Desactivar `DEBUG`.
- Restringir `ALLOWED_HOSTS`.
- Proteger dashboard de Traefik (no dejar API insegura expuesta).
- Revisar impacto de exponer `/var/run/docker.sock` en contenedor de aplicación.

## Solución de problemas
### El módulo no aparece en catálogo
- Verifica que existan `manifest.json` y `docker-compose.yml` en su carpeta.

### Error al instalar módulo
- Revisa logs del kernel y build del módulo.
- Confirma que la red externa `odoo_network` esté disponible.

### No se descarga módulo desde marketplace
- Confirma conectividad a internet del host.
- Verifica URL Git del módulo.
- Revisa variables de entorno `HOST_PROJECT_PATH`, `HOST_UID`, `HOST_GID` en `django-kernel`.
