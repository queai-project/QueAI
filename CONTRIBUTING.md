# Contribuir a QueAI

¡Gracias por interesarte en QueAI! Esta guía cubre lo mínimo que necesitas
saber para abrir un issue, mandar un parche o publicar un módulo.

Si algo no queda claro, abre un issue de tipo *Question* y lo resolvemos.

---

## Tabla de contenidos

- [Antes de empezar](#antes-de-empezar)
- [Cómo abrir un issue](#cómo-abrir-un-issue)
- [Cómo abrir un Pull Request](#cómo-abrir-un-pull-request)
  - [Setup local](#setup-local)
  - [Estilo de código y commits](#estilo-de-código-y-commits)
  - [Tests y lint](#tests-y-lint)
- [Publicar un módulo nuevo](#publicar-un-módulo-nuevo)
- [Reportar una vulnerabilidad](#reportar-una-vulnerabilidad)
- [Código de conducta](#código-de-conducta)
- [Licencia de tus contribuciones](#licencia-de-tus-contribuciones)

---

## Antes de empezar

1. **Lee la [Product Vision](docs/PRODUCTVISION.md)** — entender qué
   pretende ser QueAI evita propuestas que choquen con el rumbo (ej.
   pedir multi-tenant cuando explícitamente está fuera de alcance).
2. **Busca en issues abiertos y cerrados** antes de crear uno nuevo:
   `https://github.com/queai-project/QueAI/issues?q=...`.

## Cómo abrir un issue

Usa siempre las plantillas. La razón es que filtran la información
mínima que necesitamos para no rebotar el ticket:

| Tipo | Cuándo usarla |
|---|---|
| **Bug report** | Algo se comporta distinto a lo que dice la doc o tira un error |
| **Feature request** | Una capacidad nueva o un cambio de comportamiento del kernel |
| **Plugin proposal** | Quieres publicar un módulo nuevo en el registry oficial |
| **Question** | Duda sobre uso o arquitectura — primero busca en docs |

Para reportes de seguridad **no abras un issue público**. Usa el flujo
en [SECURITY.md](SECURITY.md).

## Cómo abrir un Pull Request

### Setup local

Necesitas Python 3.11+, Docker, Docker Compose v2 y git.

```bash
git clone https://github.com/queai-project/QueAI.git
cd QueAI

# Entorno virtual + dependencias
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install ruff                # para lint local

# Variables mínimas para correr el kernel en modo dev
cp .env.example .env
# (Edita .env: como mínimo, define SECRET_KEY y QUEAI_ADMIN_PASSWORD)

# Smoke test sin levantar Docker
SECRET_KEY=dev DEBUG=True python manage.py check
SECRET_KEY=dev DEBUG=True python manage.py test
```

Para probar con Docker:

```bash
docker compose up -d --build
docker compose logs -f django-kernel
# El hub queda en http://localhost:8473
```

### Estilo de código y commits

**Python**:
- Formateo: el repo usa `ruff` (configurado en `pyproject.toml`).
  Antes de mandar PR:
  ```bash
  ruff check .
  ```
- Imports ordenados (lo hace `ruff` también).
- Type hints donde aporten claridad — no obligatorios en todos lados,
  sí en interfaces públicas (vistas, helpers reusables, CLI commands).

**Commits**:
- Mensajes en inglés, imperativo presente (`fix: ...`, `feat: ...`,
  `docs: ...`). No es Conventional Commits estricto pero sí cercano.
- Cuerpos descriptivos: explica el **por qué**, no solo el qué — el qué
  ya lo dice el diff. Si tu cambio responde a un issue, refiérelo.
- Co-author en el footer cuando aplique:
  ```
  Co-Authored-By: Nombre <email@example.com>
  ```

**Templates**:
- Si tocas una vista que tiene template, mantén el estilo minimalista
  acordado (sin emojis decorativos, paleta del kernel, dot único de
  estado por elemento). Ver [`docs/BRAND.md`](docs/BRAND.md) cuando
  exista.

### Tests y lint

Todo PR pasa el workflow `ci.yml`:
- `ruff check .` en Python 3.11 y 3.12.
- `python manage.py test` en Python 3.11 y 3.12.

Si tu cambio toca lógica de negocio (no solo docs o templates):

1. **Añade test** que falle sin tu fix / que ejerce la rama nueva.
2. Si mockeás un comando externo (Docker, requests), prefiere mocks
   estrechos en lugar de monkey-patching global.
3. Tests rápidos: el suite entero tarda menos de 10s en CI hoy.
   Mantengámoslo así.

Si tu cambio introduce una migración Django:
- `python manage.py makemigrations <app>` y commiteá el archivo.
- Verificá que `python manage.py migrate` se aplica limpio sobre la BD
  de testing (lo hace CI).

## Publicar un módulo nuevo

Si querés que tu módulo aparezca en el marketplace oficial:

1. Lee [`docs/PLUGIN_DEVELOPMENT.md`](docs/PLUGIN_DEVELOPMENT.md) —
   contrato del manifest, layout del repo, dos ejemplos completos
   (local CPU y proxy cloud).
2. Tu repo del módulo debe ser público y tener LICENSE compatible
   con MIT (MIT, Apache-2, BSD-3, ISC).
3. Abre un issue del tipo **Plugin proposal** apuntando a tu repo
   con manifest visible.
4. Para módulos que se conectan a APIs externas: documenta claramente
   en su README qué credenciales necesita, qué tráfico saliente
   genera y qué se queda en el host vs. qué viaja al provider.

Los módulos no se mergean al repo del kernel — se mantienen como
repos independientes. El registry (`register.json`) referencia su
`git_url`, no su código.

## Reportar una vulnerabilidad

Ver [SECURITY.md](SECURITY.md). **Por favor no abras un issue público**
para problemas de seguridad.

## Código de conducta

Este proyecto adopta el [Contributor Covenant 2.1](CODE_OF_CONDUCT.md).
Al participar (issues, PRs, discussions) aceptas seguirlo.

## Licencia de tus contribuciones

QueAI se distribuye bajo licencia MIT. Cualquier contribución que mandes
se incorpora bajo la misma licencia. No requerimos CLA — el commit de
firma estándar de git es suficiente.
