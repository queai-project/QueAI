# Product Vision — QueAI

## TL;DR

**QueAI is a modular orchestrator for AI capabilities.** The kernel is an
open-source runtime; capabilities (chat, OCR, STT, TTS, RAG, etc.) are
decoupled Docker modules. A module can run a model locally on CPU, act as
a *thin proxy* to a public API, or chain several steps in a pipeline. The
kernel **assumes nothing about the model** — its job is to discover,
install, configure, monitor and audit.

## The problem

Anyone trying to build something "with AI" today faces three fronts:

1. **Heterogeneity.** Every model and every API ships its own server, its
   own `.env`, its own port, its own log format. Mixing three turns into
   an integration project.
2. **The false local-vs-cloud dichotomy.** The "self-host vs provider"
   discussion is framed as either/or. In practice, almost every real
   project ends up mixing both: offline OCR + Anthropic LLM + local
   embeddings. Wiring it together by hand is where the time goes.
3. **Operations.** Trying, installing, stopping, reconfiguring, reading
   logs, monitoring, backing up, rotating credentials: each one is a
   manual command on a server the user never wanted to administer.

## The hypothesis

If AI capabilities are distributed and operated as **containers with a
shared contract** (a `manifest.json` + a `docker-compose.yml`), then:

- The kernel orchestrates without caring about the backend.
- The user installs an "OCR Tesseract" module the same way as
  "Chat OpenAI proxy".
- Operations (start/stop/logs/healthcheck/backup) are uniform.
- Swapping is cheap: replacing "CHAT local Ollama" with "CHAT proxy
  Anthropic" requires zero rewriting in the kernel.

## The product

### Kernel capabilities (v1.0)

| Capability | Status |
|---|---|
| Module discovery in `plugins/` via `manifest.json` | ✅ |
| Lifecycle: install / start / stop / uninstall / delete | ✅ |
| Per-module configuration via `.env` with atomic recreation | ✅ |
| Real-time per-module logs (SSE) | ✅ |
| CPU / RAM / network metrics per container | ✅ |
| Real per-module healthcheck with a `starting` grace state | ✅ |
| Remote marketplace + install from any Git URL | ✅ |
| Audit log of operations (UI / API / CLI / system) with auto-purge | ✅ |
| Mandatory auth + public `/health` endpoint | ✅ |
| REST API `/api/v1` with bearer token + Swagger UI | ✅ |
| `queai` CLI to automate from scripts / CI | ✅ |
| Lightweight backup / restore (db + envs) from the CLI | ✅ |

### Official modules in v1.0

| Module | Backend | Type |
|---|---|---|
| **OCR** | Tesseract + Redis RQ workers | Local, CPU |
| **STT** | faster-whisper int8, optional VAD | Local, CPU |
| **TTS** | Piper EN/ES, low latency | Local, CPU |

### What's coming next

| Module | Planned backend | Type |
|---|---|---|
| **CHAT** | Ollama + adapters for OpenAI / Anthropic | Local **or** cloud |
| **RAG** | Local Chroma / Qdrant + provider embeddings | Local **or** hybrid |
| **VISION** | Local model or proxy to Gemini / GPT-4V | Local **or** cloud |

## Target user

- **Developers** building products on top of AI who need to be able to
  swap the underlying model without rewriting the wiring.
- **Teams** that want operational autonomy: real logs, real healthchecks,
  an audit log, the ability to roll back — without depending on a SaaS
  vendor's support.
- **Technical operators** who want a reproducible environment across
  dev, staging and prod without reinventing the stack at each step.

QueAI **is not** aimed at:
- Non-technical end users who just want a chatbot.
- Enterprises with heavy enterprise requirements (SSO, signed audit, SLA)
  — it could get there, but that's not today's scope.

## Principles

1. **Contract over technology.** What defines a module is its contract
   (`manifest.json` + declared endpoints), not the library it uses.
2. **Local and cloud are equal to the kernel.** A client using a module
   doesn't know (and doesn't need to know) whether the compute is local
   or remote. The operator picks per module, not per architecture.
3. **Operations first, marketing second.** Healthchecks, audit, live
   logs and backup are requirements, not extras.
4. **CLI = API = UI.** Anything you can do in the browser you can do
   with a `queai` command and a `POST` to `/api/v1`. No asymmetry.
5. **Open source MIT, no hidden freemium.** The core has no paywalls.
   Services around it (private registries, support) are a separate
   business and don't get camouflaged inside the product.

## Out of scope (on purpose)

- **Multi-tenant / multi-user with roles.** Single user, single admin.
- **Cryptographic plugin signing.** Trust by provenance (Git URL) for
  now.
- **Persistent historical telemetry.** Metrics are the "now" — if you
  need time series, export to Prometheus from the API.
- **Auto-scaling / clustering.** One kernel per host.
- **Marketplace with payments.** Open-source distribution only.

## Where it's going (post-v1.0)

1. **CHAT module** with unified local + cloud adapter.
2. **RAG module** that integrates with CHAT.
3. **Kernel self-update** from the UI (currently manual).
4. **Multiple registries** so each team can have its own private catalog
   alongside the official one.
5. **Plugin signing** (optional provenance chain).

For community suggestions and prioritization, open an *issue* on
[GitHub](https://github.com/queai-project/QueAI/issues).
