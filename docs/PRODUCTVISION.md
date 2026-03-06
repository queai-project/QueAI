# QueAI — Product Vision (1 página)

## 1) Visión
Centralizar el acceso a soluciones de Inteligencia Artificial **locales**, **gratuitas** y **open source**, permitiendo que cualquier persona o equipo pueda instalar, ejecutar y combinar módulos de IA (Chat, RAG, STT, TTS, OCR, etc.) en su propio equipo sin depender de la nube.

## 2) Problema que resolvemos
Hoy, usar IA de forma práctica suele implicar:
- Costos variables por API/token.
- Riesgos de privacidad al enviar datos sensibles a terceros.
- Integraciones fragmentadas (muchas herramientas sueltas, sin centro de control).
- Curva técnica alta para montar soluciones locales.

## 3) Propuesta de valor
**QueAI** es una plataforma local-first que funciona como un **orquestador modular** de apps de IA:
- Instala y gestiona módulos mediante una experiencia tipo “App Store local”.
- Ejecuta servicios de IA localmente (Docker/Docker Compose).
- Ofrece control operativo simple (instalar, iniciar, detener, desinstalar, logs).
- Permite extender capacidades mediante plugins con `manifest.json`.

## 4) Qué es (y qué no es)
### Es
- Una **plataforma AI local self-hosted** para uso personal/equipo pequeño.
- Un punto único de operación para capacidades IA on-device.
- Un proyecto open source orientado a comunidad.

### No es (por ahora)
- Un SaaS multi-tenant en la nube.
- Una plataforma enterprise con IAM complejo/aislamiento organizacional avanzado.

## 5) Usuario objetivo (ICP inicial)
1. **Developers/Makers**: quieren IA local sin complejidad de infraestructura.
2. **Pymes y equipos pequeños**: necesitan chat/RAG/OCR privado para documentos internos.
3. **Perfiles sensibles a privacidad** (legal, salud, consultoría): prefieren mantener datos on-prem/local.

## 6) Principios de producto
- **Local-first y privacidad por defecto**.
- **100% usable gratis** (núcleo libre y abierto).
- **Modularidad extrema** (plugins desacoplados).
- **Simplicidad operativa** (UX clara para no expertos).
- **Interoperabilidad** (estándares de manifest y APIs).

## 7) Diferenciadores
- Enfoque unificado en IA local (no solo un chatbot).
- Ecosistema de módulos reutilizables (Chat, RAG, STT, TTS, OCR, agentes).
- Control total del entorno y de los datos.
- Costo predecible (sin consumo por token de terceros).

## 8) Métricas de éxito (12 meses)
- # instalaciones activas locales (autorreportadas/opcional).
- # plugins comunitarios publicados y mantenidos.
- Tiempo promedio de “instalación → primer resultado útil”.
- Retención mensual de usuarios que ejecutan >1 módulo.
- % issues resueltos por comunidad (salud OSS).

## 9) Estrategia de go-to-community
- Repositorio público con documentación clara y quickstart.
- Plantillas para creación de plugins y guías de contribución.
- Roadmap transparente y etiquetado de issues para newcomers.
- Demos de casos reales: “RAG local de PDFs”, “STT+TTS offline”, “OCR + extracción”.

## 10) Norte estratégico
QueAI aspira a ser el **“entorno operativo de IA local”** de referencia en open source: instalable, modular, privado y gratuito.
