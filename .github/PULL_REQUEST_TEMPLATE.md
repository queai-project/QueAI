<!--
Gracias por contribuir. Resume el cambio en el primer bloque; el resto
del template es checklist que confirmás antes de pedir review.

Cosas que NO pertenecen a un PR (abrir issue antes):
- Cambios al rumbo del producto (ver docs/PRODUCTVISION.md).
- Refactors masivos sin discusión previa.
- Sumar un módulo al registry oficial (usar la plantilla "Plugin proposal").
-->

## Qué cambia y por qué

<!--
Explica el por qué. El qué ya está en el diff.
Si responde a un issue, refiéralo con "Closes #123" o "Refs #123".
-->

## Cómo probarlo

<!--
Pasos concretos para que el reviewer reproduzca el efecto.
Si añadiste tests automatizados, indicá cuáles ejercen tu cambio.
-->

## Capturas / output

<!-- Opcional. Útil para cambios visibles. -->

## Checklist

- [ ] `ruff check .` pasa localmente.
- [ ] `python manage.py test` pasa localmente.
- [ ] Si hay cambio de lógica, añadí (o ajusté) tests automatizados.
- [ ] Si hay cambio de modelo, generé y commitié la migración (`makemigrations`).
- [ ] Si toqué un endpoint REST, actualicé `docs/API_REFERENCE.md`.
- [ ] Si toqué env vars, actualicé `.env.example` y `docs/CONFIGURATION.md` (si existe).
- [ ] No incluí secretos ni `.env` reales en el diff.
- [ ] Leí y cumplí [CONTRIBUTING.md](../CONTRIBUTING.md) y [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md).

## Notas para el reviewer

<!-- Cualquier contexto adicional, decisiones de diseño que sentís que deberían discutirse, dudas. -->
