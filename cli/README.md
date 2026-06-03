# queai — CLI del kernel QueAI

Cliente de línea de comandos para [`queai-project/QueAI`](https://github.com/queai-project/QueAI). Mismo set de operaciones que la UI (`http://localhost:8080/`) pero accesibles desde scripts, CI y la terminal.

## Instalación

Desde el repo del kernel:

```bash
pipx install ./cli            # recomendado, aislado del system Python
# o
pip install -e ./cli          # modo dev
```

Verifica que está disponible:

```bash
queai --version
```

## Configuración

Primer uso — guarda endpoint y token en `~/.config/queai/config.toml`:

```bash
queai login http://localhost:8080
# Token API: <pega tu QUEAI_API_TOKEN>
```

El token vive en el `.env` del kernel como `QUEAI_API_TOKEN`. Si lo dejaste vacío y `DEBUG=True`, el kernel autogenera uno en cada arranque y lo imprime en logs.

Override puntual desde flags o env:

```bash
queai --endpoint http://otra-host:8080 --token xyz list
QUEAI_ENDPOINT=http://x QUEAI_API_TOKEN=y queai list
```

## Comandos

| Comando | Hace |
|---|---|
| `queai health` | Estado del kernel (sin token) |
| `queai list` | Tabla de plugins con estado |
| `queai show <folder>` | Detalle JSON de un plugin |
| `queai install <folder>` | `docker compose up --build` del módulo |
| `queai start <folder>` | Arranca un módulo detenido |
| `queai stop <folder>` | Detiene un módulo |
| `queai uninstall <folder>` | Down + limpieza (carpeta conservada) |
| `queai delete <folder>` | Borra todo, incluida la carpeta del plugin |
| `queai logs <folder> [-n 200]` | Últimas líneas de logs |
| `queai stats <folder>` | CPU/RAM/red por contenedor |
| `queai env <folder>` | Muestra el `.env` |
| `queai env <folder> --edit` | Abre `$EDITOR`, guarda y recrea el contenedor |
| `queai marketplace` | Lista del registry remoto |
| `queai download <git_url>` | Descarga un plugin desde Git |
| `queai logout` | Olvida el token |

## Ejemplos

Bootstrap rápido en una máquina nueva:

```bash
queai download https://github.com/queai-project/QueAI-OCR-CPU-LOCAL-MS.git
queai install QueAI-OCR-CPU-LOCAL-MS
queai logs QueAI-OCR-CPU-LOCAL-MS -n 50
```

Editar el `.env` del módulo de STT con tu editor favorito:

```bash
EDITOR=vim queai env QueAI-STT-CPU-LOCAL-MS --edit
```

Health check para un cron:

```bash
queai health || alert "kernel offline"
```

## Códigos de salida

- `0` — todo OK.
- `1` — error reportado por la API (status >= 400) o problema de red.

## Schema OpenAPI

Si prefieres construir tu propio cliente, el schema vive en
`http://localhost:8080/api/v1/openapi.json` y hay una UI navegable en
`http://localhost:8080/api/v1/docs`.
