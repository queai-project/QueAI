# Modelo de seguridad — QueAI

Este documento describe la superficie de ataque del kernel, las
mitigaciones aplicadas en `v1.0` y las recomendaciones para distintos
entornos de despliegue.

Para reportar una vulnerabilidad, ver [`/SECURITY.md`](../SECURITY.md).

---

## 1. Superficie de ataque

### 1.1 Lo que el kernel expone

| Superficie | Defecto | Comentario |
|---|---|---|
| Hub web (`/`, `/manager/`, `/marketplace/`, `/monitor/`, `/account/`, `/audit/`, `/welcome/`) | sesión Django con login obligatorio | el único endpoint público sin auth es `/health` y `/login` |
| API REST (`/api/v1/*`) | bearer token `QUEAI_API_TOKEN` | `/api/v1/health` y `/api/v1/openapi.json` son públicos por diseño |
| Dashboard de Traefik (`:9090/dashboard/`) | basic-auth obligatoria | hash bcrypt en `QUEAI_TRAEFIK_DASHBOARD_AUTH` |
| UI de cada plugin (`/api/<name>/ui`) | sin auth en el kernel | el plugin decide si protege su propia UI |

### 1.2 Lo que el kernel consume

| Dependencia | Origen | Riesgo |
|---|---|---|
| `/var/run/docker.sock` | montado en el contenedor del kernel | equivalente a root sobre el host |
| Plugins en `plugins/<folder>/` | clonados desde Git via `marketplace` | código de terceros que se construye y ejecuta |
| Registry `register.json` | URL hardcoded en `marketplace/views.py` | si lo comprometen, pueden ofrecer plugins maliciosos |
| Imágenes Docker de plugins | descargadas desde el registry de cada plugin | confianza por procedencia del repo |

## 2. Mitigaciones en v1.0

### 2.1 Aplicadas

- **Auth obligatoria en sesión** (`@login_required` en todas las views
  operativas) y **bearer token** en la API.
- **`hmac.compare_digest`** para validar el token (resistente a timing
  attacks).
- **Cookies seguras** y headers anti-clickjacking / XSS cuando
  `DEBUG=False` (ver `core/settings.py`).
- **Subprocess con argv como lista**, nunca `shell=True`, en todas las
  llamadas a `docker compose` / `docker`.
- **CSRF** activo en la UI (las acciones via API requieren bearer
  token, no CSRF).
- **`.env` ignorado en git**; `db.sqlite3` nunca tracked.
- **Audit log** de cada acción mutante (UI / API / CLI / system).
- **Healthcheck con grace period** para evitar exponer ventanas de
  arranque como "down" en monitoreo externo.
- **`SECRET_KEY` requerido** explícitamente cuando `DEBUG=False` (el
  kernel se rehúsa a arrancar si falta).
- **Marketplace clona con `alpine/git` en sandbox** con UID/GID del
  host, no como root en el contenedor del kernel.

### 2.2 Conocidas y aceptadas

- **Docker socket = root**: el kernel tiene acceso completo al host
  via `/var/run/docker.sock`. Mitigación: documentar el riesgo, no
  exponer el kernel sin auth, no dar acceso a usuarios no confiables.
  Una alternativa futura es usar `docker-socket-proxy` con verbos
  restringidos.
- **Plugins ejecutan código arbitrario**: un plugin malicioso del
  registry oficial podría hacer daño. Mitigación: el registry está en
  un repo separado bajo control del proyecto y revisado al sumar
  nuevos plugins. Roadmap incluye firma criptográfica opcional.
- **SQLite local**: BD sin password ni TLS. Si compartes el host con
  otros usuarios sin namespacing, podrían leer `db.sqlite3`. Mitigar
  con permisos POSIX (`chmod 600`) — el instalador no lo hace
  automáticamente todavía.
- **Logs por defecto a stdout**: si capturas logs externos, ten en
  cuenta que pueden contener nombres de plugins, IDs de contenedores
  y errores con paths del host. No incluyen secretos del `.env`.

### 2.3 No implementadas todavía

- HTTPS / TLS terminator integrado (se documenta poner un reverse
  proxy delante; ver `docs/DEPLOYMENT.md`).
- Two-factor auth para el admin.
- API tokens por scope (hoy es un solo token con todo el acceso).
- Firma criptográfica de plugins.
- Rate limiting en el login.

## 3. Recomendaciones por entorno

### 3.1 Desarrollo local (laptop, "para probar")

- Sin restricciones especiales.
- `DEBUG=True` está OK si solo accedes desde `127.0.0.1`.
- Usa `QUEAI_ADMIN_USER` / `QUEAI_ADMIN_PASSWORD` con credenciales no
  reutilizadas.

### 3.2 Homelab / self-host en red privada

- **`DEBUG=False`** (obligatorio si la red es accesible por otros).
- **`SECRET_KEY`** generado con `secrets.token_urlsafe(50)`.
- **`QUEAI_API_TOKEN`** generado con `secrets.token_urlsafe(40)`.
- **`ALLOWED_HOSTS`** restringido a tu IP / dominio interno.
- Considera un **reverse proxy** (nginx, Caddy, Traefik) para TLS y
  para esconder el kernel de la red.
- **Backup periódico** con `queai backup`; guarda los archivos fuera
  del host.

### 3.3 Producción / accesible desde Internet

- Todo lo de Homelab más:
- **TLS obligatorio**, idealmente terminado en un reverse proxy
  externo con Let's Encrypt.
- **Cierra el dashboard de Traefik** (`:9090`) en el firewall del
  host; no lo expongas públicamente.
- **Logs centralizados** (Loki, Datadog, lo que uses).
- **Monitoring externo** del endpoint `/health` y de los healthchecks
  por plugin (`/api/v1/plugins/<id>/healthcheck`).
- **Audit log review** periódico — la tabla `AuditEvent` está pensada
  para que cualquier mutación quede trazada.
- **Rotación de tokens y password de admin** cada N meses; usa
  `QUEAI_ADMIN_ROTATE_PASSWORD=true` para rotar la del admin en el
  próximo arranque sin recrear el usuario.
- **Cerrá `/admin/` de Django** si no necesitás la admin UI nativa
  (puedes deshabilitarla en `core/urls.py`).

### 3.4 Aire-gapped (sin internet)

- El kernel funciona offline una vez instalado.
- El marketplace remoto deja de funcionar — usa instalación de
  plugins por carpeta directa (`plugins/<folder>/`) o desde un
  registry interno copiado.
- Recomendación adicional: deshabilita `/api/v1/marketplace/download`
  via un middleware o un reverse proxy con denylist, para evitar que
  un operador descargue plugins desde una URL externa por accidente.

## 4. Manejo de secretos

| Secreto | Dónde vive | Rotación |
|---|---|---|
| `SECRET_KEY` (Django) | `.env` del kernel | manual; rotar invalida sesiones activas |
| `QUEAI_API_TOKEN` | `.env` del kernel | manual; rotar invalida la CLI y scripts |
| `QUEAI_ADMIN_PASSWORD` | `.env` del kernel | usa `QUEAI_ADMIN_ROTATE_PASSWORD=true` para forzarla |
| `QUEAI_TRAEFIK_DASHBOARD_AUTH` | `.env` del kernel | regenera con `htpasswd -nbB user password` |
| Secretos de cada plugin | `.env` del plugin (en su carpeta) | edita desde la UI o desde `queai env <name> --edit` |

Buenas prácticas:

- **Nunca commits los `.env`** — están en `.gitignore` por defecto.
- **`queai backup`** los incluye en el tar; trata ese archivo como
  secreto al guardarlo.
- Si vas a usar la API desde scripts, exporta el token via env
  (`QUEAI_API_TOKEN=...`) en lugar de hardcodearlo en archivos.

## 5. Limitaciones conocidas

- **Sin auditoría firmada**: el audit log puede ser modificado por
  cualquiera con acceso de escritura a `db.sqlite3`.
- **Sin federación**: no hay forma de gestionar varios kernels desde
  una única consola. Es un kernel = un host.
- **Sin permisos granulares**: el admin tiene todo; no hay rol
  "read-only" o "solo logs".

Estas limitaciones están documentadas como decisiones explícitas en
[`PRODUCTVISION.md`](PRODUCTVISION.md) (sección "Fuera de alcance").
