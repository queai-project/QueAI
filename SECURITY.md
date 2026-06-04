# Security Policy

Gracias por ayudar a mantener QueAI seguro para sus usuarios.

## Versiones soportadas

| Versión | Soporte de seguridad |
|---|---|
| `1.x` (rama `main`) | ✅ activamente mantenida |
| `< 1.0` (release candidates) | sin garantía retroactiva — actualízate al último tag |

## Cómo reportar una vulnerabilidad

**No abras un issue público** para vulnerabilidades de seguridad.

Usa uno de estos canales (en orden de preferencia):

1. **GitHub Private Vulnerability Reporting** —
   https://github.com/queai-project/QueAI/security/advisories/new
2. **Email** — `security@queai.dev`

Incluye al menos:
- Versión del kernel y de los plugins involucrados (`queai health`,
  `git rev-parse HEAD`).
- Pasos para reproducir el problema.
- Impacto observado o esperado (lectura no autorizada, escritura,
  RCE, escalada de privilegios, etc.).
- Tu disponibilidad para coordinar la divulgación.

## Qué esperar

- **Acuse de recibo en 72 h** desde el envío.
- **Triage en 7 días**: confirmamos si es un problema, su severidad
  estimada y la fecha objetivo de fix.
- **Disclosure coordinado**: trabajamos en un fix privado, te
  acreditamos al publicar el aviso de seguridad y la versión
  parcheada, salvo que prefieras anonimato.
- Si pasados **30 días** sin respuesta de nuestra parte, eres libre
  de divulgar — pero no es un objetivo, queremos resolverlo antes.

## Qué consideramos in-scope

- Vulnerabilidades en el código del kernel (`core/`,
  `module_manager/`, `marketplace/`, `system_monitor/`, `cli/`).
- Vulnerabilidades en la API REST `/api/v1/*`.
- Vulnerabilidades en la cadena de instalación (`install.sh`).
- Defectos del flujo de auth / sesión / token.
- Riesgos de la integración con Docker socket que no estén
  documentados.

## Qué consideramos out-of-scope

- Vulnerabilidades en plugins individuales (reportar al mantenedor
  del plugin afectado; lista en `register.json`).
- Problemas que requieran acceso físico al host.
- Ataques que requieran credenciales válidas del operador del
  kernel (DoS por carga legítima, abuso intencional).
- Configuraciones inseguras explícitamente desaconsejadas en
  [`docs/SECURITY.md`](docs/SECURITY.md) (p.ej. `DEBUG=True` en
  producción).

## Modelo de seguridad y recomendaciones

El detalle técnico (superficie de ataque, mitigaciones aplicadas y
configuración recomendada por entorno) vive en
[`docs/SECURITY.md`](docs/SECURITY.md).

## Bug bounty

QueAI no ofrece recompensas monetarias. Sí ofrece crédito público
en el changelog y en el aviso de seguridad publicado, salvo que
prefieras anonimato.
