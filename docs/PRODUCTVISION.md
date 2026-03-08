# Product Vision - QueAI

## Resumen
QueAI es un **kernel de orquestación de módulos de IA** que permite instalar, ejecutar, detener, configurar y monitorear aplicaciones de IA desacopladas desde una única interfaz.

En lugar de construir una sola aplicación monolítica, QueAI propone un modelo de "hub + plugins" para acelerar pruebas, despliegue local y evolución funcional.

## Problema que resuelve
Equipos técnicos que prueban soluciones de IA suelen enfrentar:

- Integraciones manuales entre herramientas heterogéneas.
- Arranques lentos de entornos por conflictos de puertos/dependencias.
- Dificultad para operar varios servicios de IA desde una vista unificada.
- Falta de un ciclo simple para instalar/desinstalar módulos de forma reversible.

## Propuesta de valor
QueAI centraliza la operación de módulos de IA en cuatro capacidades principales:

1. Descubrimiento automático de módulos locales (carpeta `plugins/`).
2. Gestión de ciclo de vida (instalar, iniciar, detener, desinstalar).
3. Configuración por módulo vía archivos `.env`.
4. Observabilidad básica (logs y métricas de CPU/RAM/red por contenedor).

## Usuario objetivo
- Desarrolladores que crean módulos de IA reutilizables.
- Equipos de innovación que validan PoCs de IA de forma rápida.
- Operadores técnicos que necesitan estandarizar despliegues locales o de laboratorio.

## Principios del producto
- **Modularidad primero**: cada módulo es independiente y reemplazable.
- **Operación simple**: acciones comunes disponibles desde UI web.
- **Aislamiento por contenedor**: cada módulo corre como servicio propio.
- **Escalabilidad funcional**: nuevas capacidades se agregan como plugin, no como refactor del kernel.

## Alcance actual (MVP funcional)
- Kernel en Django.
- Reverse proxy con Traefik.
- Marketplace para descarga de módulos desde registro remoto y repositorios Git.
- Catálogo local de módulos con sincronización disco/BD.
- Panel de monitoreo básico por módulo instalado.

## Fuera de alcance actual
- Multi-tenant y control avanzado de usuarios/permisos.
- Firma/verificación criptográfica de módulos.
- Catálogo empresarial con versionado semántico y políticas de aprobación.
- Telemetría histórica persistente y alertas avanzadas.

## Dirección evolutiva sugerida
1. Seguridad de cadena de suministro (validación de origen de módulos).
2. Mejoras de DX para crear plugins (plantillas y validadores automáticos).
3. Pipeline de publicación al marketplace con checks automáticos.
4. Observabilidad extendida (históricos, alertas y paneles).
