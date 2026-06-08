# Product Vision — QueAI

## TL;DR

**QueAI es un orquestador modular de capacidades de IA.** El kernel es un
runtime open-source; las capacidades (chat, OCR, STT, TTS, RAG, etc.) son
módulos Docker desacoplados. Un módulo puede correr un modelo localmente
en CPU, ser un *thin proxy* a una API pública, o encadenar varios pasos
en un pipeline. El kernel **no asume nada sobre el modelo** — su trabajo
es descubrir, instalar, configurar, monitorizar y auditar.

## El problema

Quien quiere construir algo "con IA" hoy se encuentra con tres frentes:

1. **Heterogeneidad.** Cada modelo y cada API trae su propio servidor,
   su propio `.env`, su propio puerto, su propio formato de logs.
   Mezclar tres se convierte en un proyecto de integración.
2. **Falsa dicotomía local vs cloud.** La discusión "self-host vs
   provider" se plantea como excluyente. En la práctica casi todos los
   proyectos reales acaban mezclando: OCR offline + LLM en Anthropic +
   embeddings locales. Conectarlo todo a mano es donde se va el tiempo.
3. **Operación.** Probar, instalar, parar, reconfigurar, ver logs,
   monitorizar, hacer backup, rotar credenciales: cada cosa es un comando
   manual en un servidor que el usuario no quería administrar.

## La hipótesis

Si las capacidades de IA se distribuyen y operan como **contenedores con
un contrato común** (un `manifest.json` + un `docker-compose.yml`),
entonces:

- El kernel orquesta sin preocuparse del backend.
- El usuario instala un módulo "OCR Tesseract" igual que "Chat OpenAI proxy".
- La operación (start/stop/logs/healthcheck/backup) es uniforme.
- La sustitución es barata: cambiar el módulo "CHAT local Ollama" por
  "CHAT proxy Anthropic" no implica reescribir nada del kernel.

## El producto

### Capacidades del kernel (v1.0)

| Capacidad | Estado |
|---|---|
| Descubrimiento de módulos en `plugins/` por `manifest.json` | ✅ |
| Ciclo de vida: install / start / stop / uninstall / delete | ✅ |
| Configuración por módulo vía `.env` con recreación atómica | ✅ |
| Logs por módulo en tiempo real (SSE) | ✅ |
| Métricas CPU / RAM / red por contenedor | ✅ |
| Healthcheck real por módulo con estado `starting` durante el grace | ✅ |
| Marketplace remoto + descarga desde URL Git arbitraria | ✅ |
| Audit log de operaciones (UI / API / CLI / system) con auto-purga | ✅ |
| Auth obligatoria + endpoint `/health` público | ✅ |
| API REST `/api/v1` con bearer token + Swagger UI | ✅ |
| CLI `queai` para automatizar desde scripts / CI | ✅ |
| Backup / restore *light* (db + envs) desde CLI | ✅ |

### Módulos oficiales en v1.0

| Módulo | Backend | Tipo |
|---|---|---|
| **OCR** | Tesseract + Redis RQ workers | Local, CPU |
| **STT** | faster-whisper int8, VAD opcional | Local, CPU |
| **TTS** | Piper EN/ES, baja latencia | Local, CPU |

### Roadmap próximo

| Módulo | Backend planeado | Tipo |
|---|---|---|
| **CHAT** | Ollama + adapters a OpenAI / Anthropic | Local **o** cloud |
| **RAG** | Chroma / Qdrant local + embeddings de proveedor | Local **o** híbrido |
| **VISION** | Modelo local o proxy a Gemini / GPT-4V | Local **o** cloud |

## Usuario objetivo

- **Desarrolladores** que están construyendo productos sobre IA y necesitan
  poder cambiar el modelo subyacente sin reescribir el wiring.
- **Equipos** que quieren autonomía operacional: poder ver logs, healthcheck
  reales, audit log, hacer rollback, sin depender del soporte de un SaaS.
- **Operadores técnicos** que quieren un entorno reproducible entre dev,
  staging y prod sin reinventar la stack en cada paso.

QueAI **no** está pensado para:
- Usuario final no técnico que solo quiere un chatbot.
- Empresas con requisitos enterprise pesados (SSO, audit firmado, SLA) —
  podría llegar ahí pero hoy no es el alcance.

## Principios

1. **Contrato sobre tecnología.** Lo que define un módulo es el contrato
   (`manifest.json` + endpoints declarados), no la librería que use.
2. **Local y cloud son iguales para el kernel.** El cliente que usa un
   módulo no sabe (ni necesita saber) si el cómputo es local o remoto.
   El operador elige por módulo, no por arquitectura.
3. **Operación primero, marketing después.** Healthcheck, audit, logs en
   vivo y backup son requisitos, no extras.
4. **CLI = API = UI.** Cualquier cosa que se pueda hacer en el navegador
   se puede hacer con un comando `queai` y un POST a `/api/v1`. Sin
   asimetría.
5. **Open source MIT, sin freemium escondido.** El core no tiene puertas
   pagas. Servicios alrededor (registries privados, soporte) son
   negocio aparte y no se camuflan dentro del producto.

## Fuera de alcance (a propósito)

- **Multi-tenant / multi-usuario con roles.** Single user, single admin.
- **Firma criptográfica de plugins.** Confianza por procedencia (URL Git)
  por ahora.
- **Telemetría histórica persistente.** Las métricas son el "ahora" — si
  necesitas series temporales, exporta a Prometheus desde la API.
- **Auto-scaling / clustering.** Un kernel por host.
- **Marketplace con pagos.** Solo distribución open source.

## Hacia dónde va (post-v1.0)

1. **Módulo CHAT** con adapter local + cloud unificados.
2. **Módulo RAG** que se integra con CHAT.
3. **Self-update** del kernel desde la UI (hoy es manual).
4. **Múltiples registries** para que cada equipo pueda tener su propio
   catálogo privado además del oficial.
5. **Firma de plugins** (cadena de procedencia opcional).

Para sugerencias y prioridades de la comunidad, abre un *issue* en
[GitHub](https://github.com/queai-project/QueAI/issues).
