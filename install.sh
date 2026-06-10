#!/usr/bin/env bash
# =============================================================================
#  QueAI — Instalador
# =============================================================================
#  Uso:
#    curl -fsSL https://queai.dev/install.sh | bash
#    bash install.sh [--dry-run] [--unattended] [--dir <ruta>] [--branch <name>]
# =============================================================================
set -Eeuo pipefail

# ----------------------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------------------
APP_NAME="QueAI"
REPO_URL="${QUEAI_REPO_URL:-https://github.com/queai-project/QueAI.git}"
REPO_BRANCH="${QUEAI_BRANCH:-main}"
DEFAULT_DIR="${HOME}/QueAI"
INSTALL_DIR="${QUEAI_DIR:-$DEFAULT_DIR}"

DRY_RUN=false
UNATTENDED=false

# Cuando generamos una contraseña de admin (modo --unattended o sin tty),
# la guardamos aquí para mostrarla en el banner final una sola vez.
GENERATED_ADMIN_PASSWORD=""

# ----------------------------------------------------------------------------
# Helpers de salida
# ----------------------------------------------------------------------------
if [ -t 1 ]; then
  # ANSI-C quoting ($'...') deja los bytes ESC reales en la variable,
  # así funcionan igual con echo, printf y heredocs.
  C_RESET=$'\033[0m';   C_INFO=$'\033[1;32m'; C_WARN=$'\033[1;33m'
  C_ERR=$'\033[1;31m';  C_DIM=$'\033[2m';     C_BOLD=$'\033[1m'
else
  C_RESET=""; C_INFO=""; C_WARN=""; C_ERR=""; C_DIM=""; C_BOLD=""
fi

log()  { echo -e "${C_INFO}[INFO]${C_RESET} $*"; }
warn() { echo -e "${C_WARN}[WARN]${C_RESET} $*"; }
err()  { echo -e "${C_ERR}[ERROR]${C_RESET} $*" >&2; }
step() { echo -e "\n${C_BOLD}==>${C_RESET} ${C_BOLD}$*${C_RESET}"; }
dim()  { echo -e "${C_DIM}$*${C_RESET}"; }

usage() {
  cat <<EOF
${C_BOLD}QueAI installer${C_RESET}

Uso:
  bash install.sh [opciones]

Opciones:
  --dir <ruta>      Directorio de instalación (default: ${DEFAULT_DIR})
  --branch <name>   Rama git a clonar (default: ${REPO_BRANCH})
  --dry-run         Mostrar qué haría sin ejecutar acciones destructivas
  --unattended      No hacer preguntas; usar defaults seguros
  -h, --help        Mostrar esta ayuda

Variables de entorno:
  QUEAI_REPO_URL    URL del repositorio (default: ${REPO_URL})
  QUEAI_BRANCH      Rama git (default: ${REPO_BRANCH})
  QUEAI_DIR         Directorio de instalación (default: ${DEFAULT_DIR})
EOF
}

# ----------------------------------------------------------------------------
# Parseo de argumentos
# ----------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)        INSTALL_DIR="$2"; shift 2 ;;
    --branch)     REPO_BRANCH="$2"; shift 2 ;;
    --dry-run)    DRY_RUN=true; shift ;;
    --unattended) UNATTENDED=true; shift ;;
    -h|--help)    usage; exit 0 ;;
    *)            err "Opción desconocida: $1"; usage; exit 2 ;;
  esac
done

# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
have() { command -v "$1" >/dev/null 2>&1; }

gen_secret() {
  # Genera un token urlsafe del largo dado. Prefiere python3 (siempre presente
  # en distros modernas y macOS); openssl como fallback. El kernel rechaza
  # arrancar con DEBUG=False sin SECRET_KEY, así que esto NO es opcional.
  local len="${1:-50}"
  if have python3; then
    python3 -c "import secrets; print(secrets.token_urlsafe($len))"
  elif have openssl; then
    openssl rand -base64 $(( len * 3 / 4 + 4 )) 2>/dev/null | tr -d '/+=\n' | head -c "$len"
    echo
  else
    err "Necesito python3 u openssl para generar SECRET_KEY/QUEAI_API_TOKEN."
    exit 1
  fi
}

port_in_use() {
  # True si el puerto TCP está siendo escuchado en cualquier interfaz local.
  # Prefiere ss (iproute2, presente en todas las distros modernas), luego
  # lsof, luego /dev/tcp como último recurso (requiere bash con netredirs).
  local p="$1"
  if have ss; then
    ss -tlnH 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${p}\$"
  elif have lsof; then
    lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | awk '{print $9}' | grep -qE "[:.]${p}\$"
  else
    # Si nadie escucha, este connect se cierra rápido con TRUE/FALSE distintos.
    (timeout 1 bash -c "exec 3<>/dev/tcp/127.0.0.1/$p" 2>/dev/null) && return 0
    return 1
  fi
}

update_env_kv() {
  # Inserta o reemplaza KEY=VAL en .env. Usa awk para no chocar con caracteres
  # especiales en el valor (URLs con /, tokens base64url, etc.).
  local key="$1" val="$2"
  local file="$INSTALL_DIR/.env"
  if grep -qE "^${key}=" "$file" 2>/dev/null; then
    awk -v k="$key" -v v="$val" '
      BEGIN { FS = OFS = "=" }
      $1 == k { print k "=" v; next }
      { print }
    ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
  else
    printf '%s=%s\n' "$key" "$val" >> "$file"
  fi
}

run() {
  # Ejecuta o simula según --dry-run
  if $DRY_RUN; then
    echo -e "${C_DIM}[dry-run]${C_RESET} $*"
  else
    eval "$@"
  fi
}

confirm() {
  # Pregunta sí/no.
  # - En --unattended responde "no" (lo seguro).
  # - Cuando nos ejecutan vía `curl | bash` el stdin del script es el pipe
  #   del curl, no la tty. Leemos directamente de /dev/tty para que la
  #   pregunta funcione sin romper el pipe del que bash está consumiendo
  #   el script. Si /dev/tty no es accesible (CI, contenedor sin -t),
  #   abortamos con un mensaje claro.
  local prompt="${1:-¿Continuar?}"
  if $UNATTENDED; then
    warn "$prompt → (unattended: no)"
    return 1
  fi
  if [ -r /dev/tty ]; then
    read -r -p "$prompt [y/N] " ans </dev/tty
  elif [ -t 0 ]; then
    read -r -p "$prompt [y/N] " ans
  else
    err "No hay tty disponible para preguntar: \"$prompt\""
    err "Re-ejecuta con --unattended para usar defaults, o descarga el script primero:"
    err "  curl -fsSL https://queai.dev/install.sh -o install.sh && bash install.sh"
    exit 1
  fi
  [[ "$ans" =~ ^[yYsS]$ ]]
}

SUDO=""
need_sudo() {
  # Devuelve el prefijo sudo si hace falta y existe. Vacío si ya somos root.
  if [[ $EUID -eq 0 ]]; then
    SUDO=""
  elif have sudo; then
    SUDO="sudo"
  else
    err "Se necesitan permisos administrativos pero sudo no está instalado."
    exit 1
  fi
}

# ----------------------------------------------------------------------------
# Detección de sistema
# ----------------------------------------------------------------------------
OS=""           # linux | macos
DISTRO=""       # debian | ubuntu | fedora | rhel | centos | arch | manjaro | macos
PKG_MGR=""      # apt | dnf | yum | pacman | brew
ARCH=""         # amd64 | arm64

detect_system() {
  step "Detectando sistema"

  case "$(uname -s)" in
    Linux)  OS="linux" ;;
    Darwin) OS="macos" ;;
    *)      err "Sistema operativo no soportado: $(uname -s). Soportados: Linux, macOS."; exit 1 ;;
  esac

  case "$(uname -m)" in
    x86_64|amd64) ARCH="amd64" ;;
    arm64|aarch64) ARCH="arm64" ;;
    *)            err "Arquitectura no soportada: $(uname -m)"; exit 1 ;;
  esac

  if [[ "$OS" == "macos" ]]; then
    DISTRO="macos"
    PKG_MGR="brew"
  else
    if [[ -f /etc/os-release ]]; then
      # shellcheck disable=SC1091
      . /etc/os-release
      DISTRO="${ID:-unknown}"
    fi

    if   have apt-get; then PKG_MGR="apt"
    elif have dnf;     then PKG_MGR="dnf"
    elif have yum;     then PKG_MGR="yum"
    elif have pacman;  then PKG_MGR="pacman"
    else
      err "No se encontró un gestor de paquetes soportado (apt/dnf/yum/pacman)."
      err "Instala Docker y Git manualmente y re-ejecuta el instalador."
      exit 1
    fi
  fi

  log "OS:      $OS ($DISTRO)"
  log "Arch:    $ARCH"
  log "PkgMgr:  $PKG_MGR"
}

# ----------------------------------------------------------------------------
# Instalación de paquetes
# ----------------------------------------------------------------------------
pkg_install() {
  # pkg_install <paquete>...
  case "$PKG_MGR" in
    apt)    run "$SUDO apt-get update -qq && $SUDO apt-get install -y --no-install-recommends $*" ;;
    dnf)    run "$SUDO dnf install -y $*" ;;
    yum)    run "$SUDO yum install -y $*" ;;
    pacman) run "$SUDO pacman -Sy --noconfirm $*" ;;
    brew)   run "brew install $*" ;;
  esac
}

ensure_git() {
  if have git; then
    log "Git ya instalado ($(git --version))"
    return
  fi
  step "Instalando Git"
  pkg_install git
}

ensure_curl() {
  if have curl; then
    return
  fi
  pkg_install curl
}

# ----------------------------------------------------------------------------
# Docker
# ----------------------------------------------------------------------------
docker_ok() {
  # Docker presente y el demonio responde
  have docker && docker info >/dev/null 2>&1
}

ensure_docker() {
  step "Verificando Docker"

  if have docker; then
    if docker info >/dev/null 2>&1; then
      log "Docker funcionando ($(docker --version))"
    else
      warn "Docker instalado pero el demonio no responde."
      warn "Posibles causas: servicio detenido o tu usuario no está en el grupo 'docker'."
      if [[ "$OS" == "linux" ]]; then
        if confirm "¿Intento iniciar el servicio docker?"; then
          need_sudo
          run "$SUDO systemctl enable --now docker || $SUDO service docker start"
        fi
      else
        warn "Abre Docker Desktop manualmente antes de continuar."
      fi
    fi
    return
  fi

  warn "Docker no está instalado."
  if [[ "$OS" == "macos" ]]; then
    err "En macOS instala Docker Desktop manualmente desde:"
    err "  https://www.docker.com/products/docker-desktop/"
    err "Re-ejecuta el instalador cuando Docker esté corriendo."
    exit 1
  fi

  if ! confirm "¿Instalar Docker oficial desde get.docker.com?"; then
    err "Docker es requerido para continuar."
    exit 1
  fi

  need_sudo
  ensure_curl
  run "curl -fsSL https://get.docker.com -o /tmp/get-docker.sh"
  run "$SUDO sh /tmp/get-docker.sh"
  run "rm -f /tmp/get-docker.sh"
}

ensure_docker_user() {
  # Asegura que el usuario actual pueda hablar con el socket Docker sin sudo
  [[ "$OS" != "linux" ]] && return 0
  [[ $EUID -eq 0 ]] && return 0
  if docker info >/dev/null 2>&1; then
    return 0
  fi

  if ! id -nG "$USER" | grep -qw docker; then
    warn "Tu usuario no está en el grupo 'docker'."
    if confirm "¿Agregarlo? (necesitarás reiniciar la sesión después)"; then
      need_sudo
      run "$SUDO usermod -aG docker $USER"
      warn "Cierra sesión y vuelve a entrar para que el cambio surta efecto,"
      warn "o ejecuta 'newgrp docker' en esta terminal."
    fi
  fi
}

# DOCKER_RUNTIME_WRAP: vacío por defecto; "sg docker -c" si tenemos que
# envolver los comandos de docker porque el shell actual no tiene aplicados
# los permisos del grupo 'docker' (típico después de instalar Docker o de
# añadir el usuario al grupo en esta misma sesión).
DOCKER_RUNTIME_WRAP=""

ensure_docker_runtime() {
  # Cuando funciona sin envolver, no hacemos nada.
  if docker info >/dev/null 2>&1; then
    return 0
  fi

  # Si está en macOS y aquí seguimos, el Docker Desktop no está corriendo.
  if [[ "$OS" == "macos" ]]; then
    err "Docker está instalado pero no responde. Abre Docker Desktop y vuelve a ejecutar."
    exit 1
  fi

  # En Linux: el caso más común es que acabamos de instalar Docker o de
  # añadir al usuario al grupo 'docker' en esta misma ejecución. La sesión
  # no tiene aplicados los permisos hasta el siguiente login. 'sg docker'
  # nos deja ejecutar comandos con el grupo aplicado sin re-loguearse.
  if command -v sg >/dev/null 2>&1 && sg docker -c "docker info" >/dev/null 2>&1; then
    DOCKER_RUNTIME_WRAP="sg docker -c"
    warn "Tu sesión todavía no aplica el grupo 'docker' (es normal si te lo acabamos de añadir)."
    warn "Para este instalador uso 'sg docker' como wrapper. Después, cierra sesión y vuelve a entrar."
    return 0
  fi

  # No se pudo. Damos un mensaje útil según el caso.
  err "Docker no responde desde este shell."
  if id -nG "$USER" 2>/dev/null | grep -qw docker; then
    err "Estás en el grupo 'docker' pero el demonio no responde."
    err "Verifica que esté corriendo:  sudo systemctl status docker"
  else
    err "Tu usuario no está en el grupo 'docker'."
    err "Manualmente:"
    err "  sudo usermod -aG docker \$USER"
    err "Después cierra sesión, vuelve a entrar y re-ejecuta el instalador."
  fi
  exit 1
}

ensure_compose() {
  # En instalaciones modernas viene como `docker compose` (plugin).
  # En sistemas viejos puede ser `docker-compose` binario.
  if docker compose version >/dev/null 2>&1; then
    log "Docker Compose v2 disponible"
    return
  fi
  if have docker-compose; then
    warn "Detectado docker-compose v1 (legacy). Funcionará pero v2 es recomendado."
    return
  fi
  err "Docker Compose no está disponible. Reinstala Docker desde get.docker.com."
  exit 1
}

# ----------------------------------------------------------------------------
# Repo y arranque
# ----------------------------------------------------------------------------
clone_or_update_repo() {
  step "Preparando $APP_NAME en $INSTALL_DIR"

  if [[ -d "$INSTALL_DIR/.git" ]]; then
    log "Repo ya existe — sincronizando con 'origin/$REPO_BRANCH'"
    # El directorio de instalación lo maneja el instalador; no esperamos
    # commits locales. Si remoto y local divergen (force-push del kernel,
    # ediciones manuales), hacemos hard-reset a origin para garantizar
    # un estado conocido. El .env es untracked, no se toca.
    run "git -C '$INSTALL_DIR' fetch --depth=1 origin '$REPO_BRANCH'"
    run "git -C '$INSTALL_DIR' checkout -B '$REPO_BRANCH' 'origin/$REPO_BRANCH'"
    run "git -C '$INSTALL_DIR' reset --hard 'origin/$REPO_BRANCH'"
    return
  fi

  if [[ -e "$INSTALL_DIR" ]]; then
    err "$INSTALL_DIR existe pero no es un repo git."
    err "Mueve el directorio o usa --dir <ruta> para indicar otro destino."
    exit 1
  fi

  run "git clone --branch '$REPO_BRANCH' --depth=1 '$REPO_URL' '$INSTALL_DIR'"
}

inject_secret_if_empty() {
  # Si la clave existe en .env con valor vacío, la rellena con un secreto
  # generado. Si ya tiene valor, no la toca (idempotente). Si no existe, la
  # añade al final del archivo.
  local key="$1"
  local len="$2"
  local file="$INSTALL_DIR/.env"

  if grep -qE "^${key}=.+" "$file" 2>/dev/null; then
    log "${key} ya configurado — no se sobrescribe"
    return
  fi

  if $DRY_RUN; then
    dim "[dry-run] generaría ${key} (${len} bytes) y lo inyectaría en .env"
    return
  fi

  update_env_kv "$key" "$(gen_secret "$len")"
  log "${key} generado automáticamente"
}

queai_already_running() {
  # True si los containers oficiales del kernel ya están corriendo en este
  # host. Sin esto, ensure_port_free aborta la segunda ejecución del
  # instalador porque el puerto está "ocupado" — por el propio QueAI.
  # Comprobamos los dos containers porque el kernel puede estar parado
  # mientras Traefik sigue de pie, o viceversa: si CUALQUIERA está vivo
  # estamos en una reinstall, no en un primer arranque.
  if ! have docker; then
    return 1
  fi
  docker ps --format '{{.Names}}' 2>/dev/null \
    | grep -qE '^(queai_traefik|queai_kernel)$'
}

ensure_port_free() {
  # QueAI se publica con un puerto fijo (8473 hub, 9473 dashboard Traefik).
  # Decisión deliberada de no reasignar dinámicamente: la landing, README
  # y docs anuncian 8473 sin condiciones; un puerto dinámico generaría
  # incongruencia entre lo que prometemos y lo que el usuario ve.
  #
  # PERO si los containers oficiales del propio QueAI ya están corriendo,
  # el puerto está "ocupado por nosotros mismos" — eso es una reinstall
  # legítima, no una colisión real. Skipear la verificación deja que
  # docker compose up -d --build haga su trabajo: recrear con la imagen
  # nueva sin perder estado. Esto cierra el último hueco de idempotencia
  # del instalador (correrlo dos veces no rompe nada).
  step "Verificando puertos"

  if queai_already_running; then
    log "QueAI ya está desplegado en este host — saltando verificación de puertos"
    log "(el propio container ocupa 8473/9473; docker compose se encargará del refresh)"
    return 0
  fi

  local web_port dash_port
  web_port="$(grep -E '^QUEAI_PORT=' "$INSTALL_DIR/.env" | head -1 | cut -d= -f2 | tr -d '\"')"
  dash_port="$(grep -E '^QUEAI_TRAEFIK_DASHBOARD_PORT=' "$INSTALL_DIR/.env" | head -1 | cut -d= -f2 | tr -d '\"')"
  web_port="${web_port:-8473}"
  dash_port="${dash_port:-9473}"

  _abort_if_port_busy "$web_port" "hub web (QUEAI_PORT)"
  _abort_if_port_busy "$dash_port" "dashboard Traefik (QUEAI_TRAEFIK_DASHBOARD_PORT)"
  log "Puertos libres: $web_port, $dash_port"
}

_abort_if_port_busy() {
  local port="$1" label="$2"
  if ! port_in_use "$port"; then
    return 0
  fi
  err "Puerto $port ocupado ($label)."
  err ""
  err "QueAI usa puertos fijos (8473 / 9473) para mantener documentación"
  err "y UI consistentes. Si necesitas un puerto distinto, instala manual:"
  err ""
  err "  git clone https://github.com/queai-project/QueAI.git ~/QueAI"
  err "  cd ~/QueAI"
  err "  cp .env.example .env"
  err "  # Edita .env y cambia QUEAI_PORT a algo libre"
  err "  docker compose up -d --build"
  err ""
  err "Para liberar el puerto: 'sudo ss -tlnp sport = :$port' te dice qué lo usa."
  exit 1
}

bootstrap_env() {
  step "Preparando configuración"
  if [[ ! -f "$INSTALL_DIR/.env" && -f "$INSTALL_DIR/.env.example" ]]; then
    log "Creando .env desde .env.example"
    run "cp '$INSTALL_DIR/.env.example' '$INSTALL_DIR/.env'"
  else
    log ".env ya existe (no se sobrescribe)"
  fi

  # El kernel rechaza arrancar con DEBUG=False y SECRET_KEY vacío, y el
  # .env.example viene con ambos secretos en blanco a propósito (no
  # commiteamos defaults). Generamos valores fuertes en el primer arranque
  # — pero respetamos cualquier valor que el usuario haya puesto.
  if [[ -f "$INSTALL_DIR/.env" ]]; then
    inject_secret_if_empty "SECRET_KEY" 50
    inject_secret_if_empty "QUEAI_API_TOKEN" 40
  fi
}

prompt_admin_credentials() {
  # El kernel auto-crea un superuser en cada boot a partir de
  # QUEAI_ADMIN_USER/QUEAI_ADMIN_PASSWORD. El .env.example viene con
  # `admin/changeme` como marcador — eso NO debe llegar a un kernel real.
  # Si los valores siguen siendo los defaults, pedimos credenciales nuevas.
  step "Cuenta de administración"

  local cur_user cur_pass
  cur_user="$(grep -E '^QUEAI_ADMIN_USER=' "$INSTALL_DIR/.env" | head -1 | cut -d= -f2 | tr -d '"')"
  cur_pass="$(grep -E '^QUEAI_ADMIN_PASSWORD=' "$INSTALL_DIR/.env" | head -1 | cut -d= -f2 | tr -d '"')"

  # Re-ejecución del installer: si la pass ya no es el marcador "changeme",
  # significa que la primera corrida (o el propio usuario) ya configuró
  # algo real. No tocamos.
  if [[ -n "$cur_pass" && "$cur_pass" != "changeme" ]]; then
    log "Credenciales de admin ya configuradas — no se sobrescriben"
    return
  fi

  if $DRY_RUN; then
    dim "[dry-run] pediría usuario y contraseña de admin"
    return
  fi

  # Sin tty (curl|bash en CI, contenedor sin -t) o --unattended: generamos
  # una password fuerte automáticamente y la mostramos al final del install
  # — UNA sola vez. El usuario debe anotarla.
  if $UNATTENDED || [ ! -r /dev/tty ]; then
    GENERATED_ADMIN_PASSWORD="$(gen_secret 18)"
    update_env_kv "QUEAI_ADMIN_USER" "${cur_user:-admin}"
    update_env_kv "QUEAI_ADMIN_PASSWORD" "$GENERATED_ADMIN_PASSWORD"
    warn "Sin terminal interactiva: generé una contraseña aleatoria para admin."
    warn "Se mostrará al final del instalador (no se vuelve a mostrar)."
    return
  fi

  # Modo interactivo
  local admin_user pass1 pass2
  log "Configura la cuenta administradora del kernel."
  read -r -p "Usuario [admin]: " admin_user </dev/tty
  admin_user="${admin_user:-admin}"

  while true; do
    read -r -s -p "Contraseña (mín. 8 caracteres): " pass1 </dev/tty
    echo
    if [[ ${#pass1} -lt 8 ]]; then
      warn "Demasiado corta. Mínimo 8 caracteres."
      continue
    fi
    # Estos caracteres rompen el parseo del .env por Docker Compose.
    case "$pass1" in
      *['"\$`']*)
        warn "Evita los caracteres: \" \\ \$ \` (rompen el .env)."
        continue
        ;;
    esac
    read -r -s -p "Repite la contraseña: " pass2 </dev/tty
    echo
    if [[ "$pass1" != "$pass2" ]]; then
      warn "Las contraseñas no coinciden. Vuelve a intentarlo."
      continue
    fi
    break
  done

  update_env_kv "QUEAI_ADMIN_USER" "$admin_user"
  update_env_kv "QUEAI_ADMIN_PASSWORD" "$pass1"
  log "Credenciales guardadas (usuario: $admin_user)"
}

start_services() {
  step "Levantando servicios"
  if $DRY_RUN; then
    dim "[dry-run] cd $INSTALL_DIR && docker compose up -d --build"
    return
  fi

  cd "$INSTALL_DIR"

  # Elegimos el binario de compose disponible (v2 plugin o v1 binario).
  local compose_bin="docker compose"
  if ! docker compose version >/dev/null 2>&1; then
    compose_bin="docker-compose"
  fi

  if [ -n "$DOCKER_RUNTIME_WRAP" ]; then
    # sg docker -c "..." abre una sub-shell con el grupo docker aplicado.
    # Le pasamos el cd + el comando completo en una sola string.
    $DOCKER_RUNTIME_WRAP "cd '$INSTALL_DIR' && $compose_bin up -d --build"
  else
    $compose_bin up -d --build
  fi
}

print_summary() {
  local port admin_user
  port="$(grep -E '^QUEAI_PORT=' "$INSTALL_DIR/.env" 2>/dev/null | cut -d= -f2 | tr -d '"' || true)"
  port="${port:-8473}"
  admin_user="$(grep -E '^QUEAI_ADMIN_USER=' "$INSTALL_DIR/.env" 2>/dev/null | cut -d= -f2 | tr -d '"' || true)"
  admin_user="${admin_user:-admin}"

  cat <<EOF

${C_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}
${C_INFO}✓ $APP_NAME instalado correctamente${C_RESET}
${C_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}

  Abrir QueAI:        ${C_BOLD}http://localhost:${port}/${C_RESET}

  Directorio:         $INSTALL_DIR
  Logs:               cd $INSTALL_DIR && docker compose logs -f
  Detener:            cd $INSTALL_DIR && docker compose down

  Documentación:      $INSTALL_DIR/docs/
  Reportar bugs:      https://github.com/queai-project/QueAI/issues

EOF

  if [[ -n "$GENERATED_ADMIN_PASSWORD" ]]; then
    cat <<EOF
${C_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}
${C_WARN}⚠ Credenciales generadas — anótalas, NO se mostrarán de nuevo${C_RESET}
${C_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}

  Usuario:    ${admin_user}
  Contraseña: ${GENERATED_ADMIN_PASSWORD}

  Cámbiala desde la UI (Cuenta → Cambiar contraseña) tras el
  primer login, o pon QUEAI_ADMIN_ROTATE_PASSWORD=true en .env
  para que el kernel rote en el próximo arranque.

EOF
  fi
}

# ----------------------------------------------------------------------------
# Flujo principal
# ----------------------------------------------------------------------------
main() {
  echo -e "${C_BOLD}$APP_NAME — instalador${C_RESET}"
  $DRY_RUN  && warn "Modo --dry-run: no se realizarán cambios reales."
  $UNATTENDED && warn "Modo --unattended: usando defaults sin preguntar."

  detect_system
  ensure_git
  ensure_curl
  ensure_docker
  ensure_docker_user
  ensure_compose
  clone_or_update_repo
  bootstrap_env
  prompt_admin_credentials
  ensure_port_free
  ensure_docker_runtime
  start_services
  print_summary
}

main "$@"
