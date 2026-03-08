# Guía de Creación de Plugins

## Objetivo
Definir la estructura mínima para que un módulo sea detectado y operado por QueAI.

## Estructura mínima
Crea una carpeta en `plugins/<nombre_modulo>/` con:

```text
plugins/<nombre_modulo>/
├── app/
│   └── main.py
├── frontend_dist/
│   └── index.html
├── assets/
│   └── logo.png
├── manifest.json
├── docker-compose.yml
└── Dockerfile
```

Opcional recomendado:

- `.env.example`
- `.env`
- `requirements.txt`

## Manifest requerido
Archivo `manifest.json` (campos esperados por el kernel):

```json
{
  "name": "my_module",
  "display_name": "My Module",
  "ui_entry_point": "/api/my_module/ui",
  "configuration_entry_point": "/api/my_module/config",
  "documentation_entry_point": "/api/my_module/docs",
  "healthcheck_entry_point": "/api/my_module/health",
  "version": "1.0.0",
  "logo": "logo.png",
  "description": "Descripción corta del módulo",
  "author": "Your Team",
  "license": "MIT"
}
```

Reglas prácticas:

- `name` debe ser estable y único.
- `ui_entry_point` debe coincidir con el `root_path`/rutas del servicio.
- `logo` debe existir en `assets/`.

## Backend mínimo (FastAPI)
Ejemplo de `app/main.py`:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="My Module", root_path="/api/my_module")

@app.get("/health")
def health():
    return {"status": "healthy"}

app.mount("/ui", StaticFiles(directory="frontend_dist", html=True), name="ui")
```

## Dockerfile mínimo

```dockerfile
FROM python:3.11-slim

WORKDIR /code
RUN pip install --no-cache-dir fastapi uvicorn
COPY ./app /code/app
COPY ./frontend_dist /code/frontend_dist
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## docker-compose del plugin
Puntos críticos:

- Conectar a red externa `odoo_network`.
- Habilitar Traefik.
- Definir router con `PathPrefix('/api/<tu_modulo>')`.
- Definir puerto interno del servicio (`8000`).

Ejemplo:

```yaml
version: '3.8'

services:
  my_module:
    build: .
    container_name: my_module_service
    networks:
      - odoo_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.my_module.rule=PathPrefix(`/api/my_module`)"
      - "traefik.http.routers.my_module.entrypoints=web"
      - "traefik.http.services.my_module.loadbalancer.server.port=8000"

networks:
  odoo_network:
    external: true
```

## Variables de entorno
Si incluyes `.env.example`, el kernel puede usarlo como plantilla al abrir configuración del módulo por primera vez.

Buenas prácticas:

- Documentar cada variable en comentarios.
- Nunca commitear secretos reales.
- Validar defaults seguros en tiempo de arranque del módulo.

## Flujo de prueba
1. Crear estructura del módulo.
2. Levantar el kernel (`docker compose up -d --build`).
3. Entrar a `http://localhost/store/`.
4. Verificar que aparece en el catálogo.
5. Instalar módulo desde UI.
6. Abrir UI del módulo y endpoint `/health`.
7. Revisar logs y dashboard de monitoreo.

## Checklist de compatibilidad
Antes de publicar un plugin:

- `manifest.json` válido.
- `docker-compose.yml` presente y funcional.
- `Dockerfile` construye sin errores.
- Ruta `ui_entry_point` accesible.
- Ruta de healthcheck operativa.
- Logo renderiza correctamente.
- Variables de entorno documentadas.

## Publicación en marketplace (opcional)
Para distribuir un módulo, publica su repo Git y registra su `git_url` en el registro remoto usado por QueAI (`register.json`).
