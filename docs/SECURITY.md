# Security model — QueAI

This document describes the kernel's attack surface, the mitigations applied in `v1.0`, and recommendations for different deployment environments.

To report a vulnerability, see [`/SECURITY.md`](../SECURITY.md).

---

## 1. Attack surface

### 1.1 What the kernel exposes

| Surface | Default | Comment |
|---|---|---|
| Web hub (`/`, `/manager/`, `/marketplace/`, `/monitor/`, `/account/`, `/audit/`, `/welcome/`) | Django session, login required | the only public endpoints without auth are `/health` and `/login` |
| REST API (`/api/v1/*`) | bearer token `QUEAI_API_TOKEN` | `/api/v1/health` and `/api/v1/openapi.json` are public by design |
| Traefik dashboard (`:9473/dashboard/`) | mandatory basic-auth | bcrypt hash in `QUEAI_TRAEFIK_DASHBOARD_AUTH` |
| Each plugin's UI (`/api/<name>/ui`) | no auth at the kernel level | the plugin decides whether to protect its own UI |

### 1.2 What the kernel consumes

| Dependency | Origin | Risk |
|---|---|---|
| `/var/run/docker.sock` | mounted in the kernel container | root-equivalent on the host |
| Plugins in `plugins/<folder>/` | cloned from Git via `marketplace` | third-party code that gets built and run |
| Registry `register.json` | URL in `marketplace/views.py` | if compromised, can serve malicious plugins |
| Plugin Docker images | downloaded from each plugin's registry | trust by repo provenance |

## 2. Mitigations in v1.0

### 2.1 Applied

- **Mandatory session auth** (`@login_required` on every operational view) and **bearer token** on the API.
- **`hmac.compare_digest`** to validate the token (timing-attack resistant).
- **Secure cookies** and anti-clickjacking / XSS headers when `DEBUG=False` (see `core/settings.py`).
- **Subprocess with argv as a list**, never `shell=True`, in every `docker compose` / `docker` call.
- **CSRF** active on the UI (actions through the API use the bearer token, no CSRF).
- **`.env` ignored in git**; `db.sqlite3` never tracked.
- **Audit log** for every mutating action (UI / API / CLI / system).
- **Healthcheck with grace period** to avoid exposing startup windows as "down" in external monitoring.
- **`SECRET_KEY` explicitly required** when `DEBUG=False` (the kernel refuses to start if missing).
- **Marketplace clones with sandboxed `alpine/git`** using the host's UID/GID, not as root in the kernel container.
- **`SECRET_KEY` and `QUEAI_API_TOKEN` auto-generated on first install** with strong random values (idempotent — won't rotate existing values).

### 2.2 Known and accepted

- **Docker socket = root**: the kernel has full host access via `/var/run/docker.sock`. Mitigation: document the risk, don't expose the kernel without auth, don't give access to untrusted users. A future alternative is `docker-socket-proxy` with restricted verbs.
- **Plugins run arbitrary code**: a malicious plugin from the official registry could do harm. Mitigation: the registry is in a separate, project-controlled repo reviewed when adding new plugins. The roadmap includes optional cryptographic signing.
- **Local SQLite**: a DB without password or TLS. If you share the host with untrusted users without namespacing, they could read `db.sqlite3`. Mitigate with POSIX permissions (`chmod 600`) — the installer doesn't do this automatically yet.
- **Default logs to stdout**: if you capture logs externally, note that they may contain plugin names, container IDs and errors with host paths. They do not include `.env` secrets.

### 2.3 Not implemented yet

- Built-in HTTPS / TLS terminator (the recommendation is a reverse proxy in front).
- Two-factor auth for the admin.
- Scoped API tokens (today there's a single token with full access).
- Cryptographic plugin signing.
- Login rate limiting.

## 3. Recommendations per environment

### 3.1 Local development (laptop, "just to try it")

- No special restrictions.
- `DEBUG=True` is fine if you only access from `127.0.0.1`.
- Use `QUEAI_ADMIN_USER` / `QUEAI_ADMIN_PASSWORD` with non-reused credentials.

### 3.2 Homelab / self-host on a private network

- **`DEBUG=False`** (mandatory if the network is accessible to others).
- **`SECRET_KEY`** generated with `secrets.token_urlsafe(50)`.
- **`QUEAI_API_TOKEN`** generated with `secrets.token_urlsafe(40)`.
- **`ALLOWED_HOSTS`** restricted to your IP / internal domain.
- Consider a **reverse proxy** (nginx, Caddy, Traefik) for TLS and to hide the kernel from the network.
- **Periodic backups** with `queai backup`; store the files off the host.

### 3.3 Production / Internet-accessible

- Everything from Homelab, plus:
- **Mandatory TLS**, ideally terminated by an external reverse proxy with Let's Encrypt.
- **Close the Traefik dashboard** (`:9473`) at the host firewall; don't expose it publicly.
- **Centralized logs** (Loki, Datadog, whatever you use).
- **External monitoring** of `/health` and per-plugin healthchecks (`/api/v1/plugins/<id>/healthcheck`).
- **Periodic audit log review** — the `AuditEvent` table is designed to leave a trace for every mutation.
- **Token and admin password rotation** every N months; use `QUEAI_ADMIN_ROTATE_PASSWORD=true` to rotate the admin's password on the next boot without recreating the user.
- **Close Django's `/admin/`** if you don't need the native admin UI (it can be disabled in `core/urls.py`).

### 3.4 Air-gapped (no internet)

- The kernel works offline once installed.
- The remote marketplace stops working — install plugins by direct folder placement (`plugins/<folder>/`) or from an internal mirror of the registry.
- Extra recommendation: disable `/api/v1/marketplace/download` via a middleware or a reverse-proxy denylist, to prevent an operator from downloading plugins from an external URL by accident.

## 4. Secret handling

| Secret | Lives in | Rotation |
|---|---|---|
| `SECRET_KEY` (Django) | kernel's `.env` | manual; rotating invalidates active sessions |
| `QUEAI_API_TOKEN` | kernel's `.env` | manual; rotating invalidates the CLI and scripts |
| `QUEAI_ADMIN_PASSWORD` | kernel's `.env` | set `QUEAI_ADMIN_ROTATE_PASSWORD=true` to force it |
| `QUEAI_TRAEFIK_DASHBOARD_AUTH` | kernel's `.env` | regenerate with `htpasswd -nbB user password` |
| Per-plugin secrets | the plugin's own `.env` (inside its folder) | edit from the UI or `queai env <name> --edit` |

Good practice:

- **Never commit `.env` files** — they're in `.gitignore` by default.
- **`queai backup`** includes them in the tar; treat that file as a secret when storing it.
- If you're calling the API from scripts, export the token via env (`QUEAI_API_TOKEN=...`) instead of hardcoding it in files.

## 5. Known limitations

- **No signed auditing**: anyone with write access to `db.sqlite3` can modify the audit log.
- **No federation**: there's no way to manage several kernels from a single console. One kernel = one host.
- **No granular permissions**: the admin has everything; there's no "read-only" or "logs-only" role.

These limitations are documented as explicit decisions in [`PRODUCTVISION.md`](PRODUCTVISION.md) ("Out of scope" section).
