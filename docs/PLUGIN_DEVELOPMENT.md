# Plugin development guide

## Goal

Define the minimum structure required for a module to be detected and operated by QueAI.

## Minimum layout

Create a folder at `plugins/<module_name>/` with:

```text
plugins/<module_name>/
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

Optional but recommended:

- `.env.example`
- `.env`
- `requirements.txt`

## Required manifest

The `manifest.json` file (fields expected by the kernel):

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
  "description": "Short description of the module",
  "description_en": "Optional English translation of the description",
  "author": "Your Team",
  "license": "MIT"
}
```

Practical rules:

- `name` must be stable and unique.
- `ui_entry_point` must match the service's `root_path`/routes.
- `logo` must exist under `assets/`.
- `description_en` is optional; if present, the Hub will use it when the active UI language is English.

## Minimum backend (FastAPI)

Example `app/main.py`:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="My Module", root_path="/api/my_module")

@app.get("/health")
def health():
    return {"status": "healthy"}

app.mount("/ui", StaticFiles(directory="frontend_dist", html=True), name="ui")
```

## Minimum Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /code
RUN pip install --no-cache-dir fastapi uvicorn
COPY ./app /code/app
COPY ./frontend_dist /code/frontend_dist
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Plugin docker-compose

Critical points:

- Join the external **`queai_network`** (created by the kernel's `docker-compose.yml`).
- Enable Traefik.
- Define a router with `PathPrefix('/api/<your_module>')`.
- Define the service's internal port (`8000`).

Example:

```yaml
services:
  my_module:
    build: .
    container_name: my_module_service
    networks:
      - queai_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.my_module.rule=PathPrefix(`/api/my_module`)"
      - "traefik.http.routers.my_module.entrypoints=web"
      - "traefik.http.services.my_module.loadbalancer.server.port=8000"

networks:
  queai_network:
    external: true
```

> Don't declare `version:` — the directive is obsolete in Compose v2 and produces warnings.

## Environment variables

If you include a `.env.example`, the kernel uses it as a template the first time someone opens the module's configuration.

Good practice:

- Document every variable in comments.
- Never commit real secrets.
- Validate safe defaults at module startup.

## Alternative example: a plugin that proxies an external API

QueAI doesn't assume your plugin runs the model locally. A useful pattern is to expose a standard capability (transcription, chat, OCR) and internally delegate to a public API. Benefits: instant startup, no heavy model downloads, predictable latency. Trade-offs: outbound internet and credentials in the `.env`.

Minimum `app/main.py` for a "chat proxy to OpenAI" plugin:

```python
import os
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Chat Cloud Proxy", root_path="/api/chat_cloud")
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


class ChatIn(BaseModel):
    prompt: str


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/chat")
async def chat(body: ChatIn):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": OPENAI_MODEL,
                "messages": [{"role": "user", "content": body.prompt}],
            },
        )
        r.raise_for_status()
        return r.json()
```

Module `.env.example`:

```env
# Secret. Edit from /manager/ → your plugin → .env (the kernel restarts the container on save).
OPENAI_API_KEY=sk-replace-me
OPENAI_MODEL=gpt-4o-mini
```

Plugin `docker-compose.yml` (identical pattern to local; only the startup command changes and you don't need to download models):

```yaml
services:
  chat_cloud:
    build: .
    container_name: chat_cloud_service
    env_file: .env
    networks:
      - queai_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.chat_cloud.rule=PathPrefix(`/api/chat_cloud`)"
      - "traefik.http.routers.chat_cloud.entrypoints=web"
      - "traefik.http.services.chat_cloud.loadbalancer.server.port=8000"

networks:
  queai_network:
    external: true
```

> **The kernel sees this plugin identically to a local one.** It shows up in the catalog with its name, its healthcheck dot, its logs, its CPU/RAM metric (which will be minimal — just the HTTP client). The audit log records install/start/stop/save_env the same way. The `queai` CLI handles it the same way.
>
> If you publish a plugin of this kind, make it clear in its README that it requires provider credentials and that outbound traffic is on by design. That's information the kernel operator needs before installing it.

## Test flow

1. Create the module structure under `plugins/<your_module>/`.
2. Bring up the kernel: `docker compose up -d --build`.
3. Open `http://localhost:8473/manager/`.
4. Verify the module appears in the catalog.
5. Install the module from the UI.
6. Open the module's UI (`/api/<module>/ui`) and the `/health` endpoint.
7. Check logs and the monitoring dashboard at `/monitor/`.

## Compatibility checklist

Before publishing a plugin:

- Valid `manifest.json`.
- `docker-compose.yml` present and working.
- `Dockerfile` builds without errors.
- `ui_entry_point` route reachable.
- Healthcheck route working.
- Logo renders correctly.
- Environment variables documented.

## Marketplace publication (optional)

To distribute a module, publish its Git repo and register its `git_url` in the remote registry used by QueAI (`register.json`).
