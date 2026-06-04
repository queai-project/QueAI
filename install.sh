#!/usr/bin/env bash
# =============================================================================
#  QueAI — Instalador
# =============================================================================
#  Filosofía:
#    * NO destruir nada existente sin permiso explícito.
#    * Detectar lo que ya hay y reutilizarlo (Docker, repo, etc).
#    * Soportar Linux multi-distro (Debian/Ubuntu/Fedora/RHEL/Arch) y macOS.
#    * Idempotente: correrlo dos veces no rompe nada.
#
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

# ----------------------------------------------------------------------------
# Helpers de salida
# ----------------------------------------------------------------------------
if [ -t 1 ]; then
  C_RESET="\033[0m"; C_INFO="\033[1;32m"; C_WARN="\033[1;33m"
  C_ERR="\033[1;31m"; C_DIM="\033[2m"; C_BOLD="\033[1m"
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
    log "Repo ya existe — actualizando rama '$REPO_BRANCH'"
    run "git -C '$INSTALL_DIR' fetch --depth=1 origin '$REPO_BRANCH'"
    run "git -C '$INSTALL_DIR' checkout '$REPO_BRANCH'"
    run "git -C '$INSTALL_DIR' pull --ff-only origin '$REPO_BRANCH'"
    return
  fi

  if [[ -e "$INSTALL_DIR" ]]; then
    err "$INSTALL_DIR existe pero no es un repo git."
    err "Mueve el directorio o usa --dir <ruta> para indicar otro destino."
    exit 1
  fi

  run "git clone --branch '$REPO_BRANCH' --depth=1 '$REPO_URL' '$INSTALL_DIR'"
}

bootstrap_env() {
  step "Preparando configuración"
  if [[ ! -f "$INSTALL_DIR/.env" && -f "$INSTALL_DIR/.env.example" ]]; then
    log "Creando .env desde .env.example"
    run "cp '$INSTALL_DIR/.env.example' '$INSTALL_DIR/.env'"
  else
    log ".env ya existe (no se sobrescribe)"
  fi
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
  local port
  port="$(grep -E '^QUEAI_PORT=' "$INSTALL_DIR/.env" 2>/dev/null | cut -d= -f2 | tr -d '"' || true)"
  port="${port:-8080}"

  cat <<EOF

${C_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}
${C_INFO}✓ $APP_NAME instalado correctamente${C_RESET}
${C_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}

  Hub:                http://localhost:${port}/
  Catálogo:           http://localhost:${port}/manager/
  Marketplace:        http://localhost:${port}/marketplace/
  Monitor:            http://localhost:${port}/monitor/

  Directorio:         $INSTALL_DIR
  Logs:               cd $INSTALL_DIR && docker compose logs -f
  Detener:            cd $INSTALL_DIR && docker compose down

  Documentación:      $INSTALL_DIR/docs/
  Reportar bugs:      https://github.com/queai-project

EOF
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
  ensure_docker_runtime
  start_services
  print_summary
}

main "$@"
