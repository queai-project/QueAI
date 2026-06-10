#!/usr/bin/env bash
# =============================================================================
#  QueAI — Installer
# =============================================================================
#  Usage:
#    curl -fsSL https://queai.dev/install.sh | bash
#    bash install.sh [--dry-run] [--unattended] [--dir <path>] [--branch <name>]
# =============================================================================
set -Eeuo pipefail

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
APP_NAME="QueAI"
REPO_URL="${QUEAI_REPO_URL:-https://github.com/queai-project/QueAI.git}"
REPO_BRANCH="${QUEAI_BRANCH:-main}"
DEFAULT_DIR="${HOME}/QueAI"
INSTALL_DIR="${QUEAI_DIR:-$DEFAULT_DIR}"

DRY_RUN=false
UNATTENDED=false

# When we generate an admin password (--unattended mode or no tty), we save
# it here so we can show it in the final banner exactly once.
GENERATED_ADMIN_PASSWORD=""

# ----------------------------------------------------------------------------
# Output helpers
# ----------------------------------------------------------------------------
if [ -t 1 ]; then
  # ANSI-C quoting ($'...') stores the real ESC bytes in the variable, so it
  # works the same way with echo, printf and heredocs.
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

Usage:
  bash install.sh [options]

Options:
  --dir <path>      Install directory (default: ${DEFAULT_DIR})
  --branch <name>   Git branch to clone (default: ${REPO_BRANCH})
  --dry-run         Show what it would do without running destructive actions
  --unattended      No prompts; use safe defaults
  -h, --help        Show this help

Environment variables:
  QUEAI_REPO_URL    Repository URL (default: ${REPO_URL})
  QUEAI_BRANCH      Git branch (default: ${REPO_BRANCH})
  QUEAI_DIR         Install directory (default: ${DEFAULT_DIR})
EOF
}

# ----------------------------------------------------------------------------
# Argument parsing
# ----------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)        INSTALL_DIR="$2"; shift 2 ;;
    --branch)     REPO_BRANCH="$2"; shift 2 ;;
    --dry-run)    DRY_RUN=true; shift ;;
    --unattended) UNATTENDED=true; shift ;;
    -h|--help)    usage; exit 0 ;;
    *)            err "Unknown option: $1"; usage; exit 2 ;;
  esac
done

# ----------------------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------------------
have() { command -v "$1" >/dev/null 2>&1; }

gen_secret() {
  # Generates a urlsafe token of the given length. Prefers python3 (always
  # present on modern distros and macOS); openssl as fallback. The kernel
  # refuses to start with DEBUG=False and no SECRET_KEY, so this is NOT
  # optional.
  local len="${1:-50}"
  if have python3; then
    python3 -c "import secrets; print(secrets.token_urlsafe($len))"
  elif have openssl; then
    openssl rand -base64 $(( len * 3 / 4 + 4 )) 2>/dev/null | tr -d '/+=\n' | head -c "$len"
    echo
  else
    err "Need python3 or openssl to generate SECRET_KEY/QUEAI_API_TOKEN."
    exit 1
  fi
}

port_in_use() {
  # True if the TCP port is being listened to on any local interface.
  # Prefers ss (iproute2, present on every modern distro), then lsof,
  # then /dev/tcp as last resort (requires bash with net redirects).
  local p="$1"
  if have ss; then
    ss -tlnH 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${p}\$"
  elif have lsof; then
    lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | awk '{print $9}' | grep -qE "[:.]${p}\$"
  else
    # If nothing is listening, this connect closes fast with TRUE/FALSE distinct.
    (timeout 1 bash -c "exec 3<>/dev/tcp/127.0.0.1/$p" 2>/dev/null) && return 0
    return 1
  fi
}

update_env_kv() {
  # Inserts or replaces KEY=VAL in .env. Uses awk to avoid clashing with
  # special characters in the value (URLs with /, base64url tokens, etc.).
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
  # Run or simulate according to --dry-run
  if $DRY_RUN; then
    echo -e "${C_DIM}[dry-run]${C_RESET} $*"
  else
    eval "$@"
  fi
}

confirm() {
  # Yes/no question.
  # - In --unattended it answers "no" (the safe choice).
  # - When we're executed via `curl | bash`, the script's stdin is the curl
  #   pipe, not the tty. We read directly from /dev/tty so the prompt works
  #   without breaking the pipe bash is consuming the script from. If
  #   /dev/tty is not accessible (CI, container without -t), we abort with
  #   a clear message.
  local prompt="${1:-Continue?}"
  if $UNATTENDED; then
    warn "$prompt → (unattended: no)"
    return 1
  fi
  if [ -r /dev/tty ]; then
    read -r -p "$prompt [y/N] " ans </dev/tty
  elif [ -t 0 ]; then
    read -r -p "$prompt [y/N] " ans
  else
    err "No tty available to ask: \"$prompt\""
    err "Re-run with --unattended to use defaults, or download the script first:"
    err "  curl -fsSL https://queai.dev/install.sh -o install.sh && bash install.sh"
    exit 1
  fi
  [[ "$ans" =~ ^[yYsS]$ ]]
}

SUDO=""
need_sudo() {
  # Returns the sudo prefix if needed and available. Empty if we're already root.
  if [[ $EUID -eq 0 ]]; then
    SUDO=""
  elif have sudo; then
    SUDO="sudo"
  else
    err "Administrative permissions needed but sudo is not installed."
    exit 1
  fi
}

# ----------------------------------------------------------------------------
# System detection
# ----------------------------------------------------------------------------
OS=""           # linux | macos
DISTRO=""       # debian | ubuntu | fedora | rhel | centos | arch | manjaro | macos
PKG_MGR=""      # apt | dnf | yum | pacman | brew
ARCH=""         # amd64 | arm64

detect_system() {
  step "Detecting system"

  case "$(uname -s)" in
    Linux)  OS="linux" ;;
    Darwin) OS="macos" ;;
    *)      err "Unsupported operating system: $(uname -s). Supported: Linux, macOS."; exit 1 ;;
  esac

  case "$(uname -m)" in
    x86_64|amd64) ARCH="amd64" ;;
    arm64|aarch64) ARCH="arm64" ;;
    *)            err "Unsupported architecture: $(uname -m)"; exit 1 ;;
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
      err "No supported package manager found (apt/dnf/yum/pacman)."
      err "Install Docker and Git manually and re-run the installer."
      exit 1
    fi
  fi

  log "OS:      $OS ($DISTRO)"
  log "Arch:    $ARCH"
  log "PkgMgr:  $PKG_MGR"
}

# ----------------------------------------------------------------------------
# Package installation
# ----------------------------------------------------------------------------
pkg_install() {
  # pkg_install <package>...
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
    log "Git already installed ($(git --version))"
    return
  fi
  step "Installing Git"
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
  # Docker present and the daemon responds
  have docker && docker info >/dev/null 2>&1
}

ensure_docker() {
  step "Checking Docker"

  if have docker; then
    if docker info >/dev/null 2>&1; then
      log "Docker working ($(docker --version))"
    else
      warn "Docker installed but the daemon is not responding."
      warn "Possible causes: service stopped or your user is not in the 'docker' group."
      if [[ "$OS" == "linux" ]]; then
        if confirm "Try to start the docker service?"; then
          need_sudo
          run "$SUDO systemctl enable --now docker || $SUDO service docker start"
        fi
      else
        warn "Open Docker Desktop manually before continuing."
      fi
    fi
    return
  fi

  warn "Docker is not installed."
  if [[ "$OS" == "macos" ]]; then
    err "On macOS install Docker Desktop manually from:"
    err "  https://www.docker.com/products/docker-desktop/"
    err "Re-run the installer once Docker is running."
    exit 1
  fi

  if ! confirm "Install the official Docker from get.docker.com?"; then
    err "Docker is required to continue."
    exit 1
  fi

  need_sudo
  ensure_curl
  run "curl -fsSL https://get.docker.com -o /tmp/get-docker.sh"
  run "$SUDO sh /tmp/get-docker.sh"
  run "rm -f /tmp/get-docker.sh"
}

ensure_docker_user() {
  # Make sure the current user can talk to the Docker socket without sudo
  [[ "$OS" != "linux" ]] && return 0
  [[ $EUID -eq 0 ]] && return 0
  if docker info >/dev/null 2>&1; then
    return 0
  fi

  if ! id -nG "$USER" | grep -qw docker; then
    warn "Your user is not in the 'docker' group."
    if confirm "Add it? (you'll need to log out and back in afterwards)"; then
      need_sudo
      run "$SUDO usermod -aG docker $USER"
      warn "Log out and back in for the change to take effect,"
      warn "or run 'newgrp docker' in this terminal."
    fi
  fi
}

# DOCKER_RUNTIME_WRAP: empty by default; "sg docker -c" when we have to wrap
# docker commands because the current shell doesn't have the 'docker' group
# permissions applied yet (typical right after installing Docker or after
# adding the user to the group in this very session).
DOCKER_RUNTIME_WRAP=""

ensure_docker_runtime() {
  # When it works without wrapping, we do nothing.
  if docker info >/dev/null 2>&1; then
    return 0
  fi

  # If we're on macOS and we're still here, Docker Desktop is not running.
  if [[ "$OS" == "macos" ]]; then
    err "Docker is installed but not responding. Open Docker Desktop and re-run."
    exit 1
  fi

  # On Linux: the most common case is that we just installed Docker or
  # added the user to the 'docker' group in this very run. The session
  # doesn't have the permissions applied until the next login. 'sg docker'
  # lets us execute commands with the group applied without re-login.
  if command -v sg >/dev/null 2>&1 && sg docker -c "docker info" >/dev/null 2>&1; then
    DOCKER_RUNTIME_WRAP="sg docker -c"
    warn "Your session has not picked up the 'docker' group yet (normal if we just added it)."
    warn "For this installer I use 'sg docker' as a wrapper. Afterwards, log out and back in."
    return 0
  fi

  # Couldn't do it. Give a useful message based on the case.
  err "Docker is not responding from this shell."
  if id -nG "$USER" 2>/dev/null | grep -qw docker; then
    err "You're in the 'docker' group but the daemon is not responding."
    err "Check that it's running:  sudo systemctl status docker"
  else
    err "Your user is not in the 'docker' group."
    err "Manually:"
    err "  sudo usermod -aG docker \$USER"
    err "Then log out, log back in, and re-run the installer."
  fi
  exit 1
}

ensure_compose() {
  # On modern installations it comes as `docker compose` (plugin).
  # On older systems it can be the `docker-compose` binary.
  if docker compose version >/dev/null 2>&1; then
    log "Docker Compose v2 available"
    return
  fi
  if have docker-compose; then
    warn "Detected docker-compose v1 (legacy). It will work but v2 is recommended."
    return
  fi
  err "Docker Compose is not available. Reinstall Docker from get.docker.com."
  exit 1
}

# ----------------------------------------------------------------------------
# Repo and bring-up
# ----------------------------------------------------------------------------
clone_or_update_repo() {
  step "Preparing $APP_NAME in $INSTALL_DIR"

  if [[ -d "$INSTALL_DIR/.git" ]]; then
    log "Repo already exists — syncing with 'origin/$REPO_BRANCH'"
    # The install directory is owned by the installer; we don't expect
    # local commits. If remote and local diverge (kernel force-push, manual
    # edits), we hard-reset to origin to guarantee a known state. The .env
    # is untracked, so it's not touched.
    run "git -C '$INSTALL_DIR' fetch --depth=1 origin '$REPO_BRANCH'"
    run "git -C '$INSTALL_DIR' checkout -B '$REPO_BRANCH' 'origin/$REPO_BRANCH'"
    run "git -C '$INSTALL_DIR' reset --hard 'origin/$REPO_BRANCH'"
    return
  fi

  if [[ -e "$INSTALL_DIR" ]]; then
    err "$INSTALL_DIR exists but is not a git repo."
    err "Move the directory or use --dir <path> to point somewhere else."
    exit 1
  fi

  run "git clone --branch '$REPO_BRANCH' --depth=1 '$REPO_URL' '$INSTALL_DIR'"
}

inject_secret_if_empty() {
  # If the key exists in .env with an empty value, fills it with a generated
  # secret. If it already has a value, leaves it alone (idempotent). If it
  # doesn't exist, appends it to the file.
  local key="$1"
  local len="$2"
  local file="$INSTALL_DIR/.env"

  if grep -qE "^${key}=.+" "$file" 2>/dev/null; then
    log "${key} already configured — not overwriting"
    return
  fi

  if $DRY_RUN; then
    dim "[dry-run] would generate ${key} (${len} bytes) and inject into .env"
    return
  fi

  update_env_kv "$key" "$(gen_secret "$len")"
  log "${key} generated automatically"
}

queai_already_running() {
  # True if the official kernel containers are already running on this host.
  # Without this, ensure_port_free aborts the second run of the installer
  # because the port is "in use" — by QueAI itself. We check both containers
  # because the kernel can be stopped while Traefik is up, or vice-versa: if
  # ANY of the two is alive we're in a reinstall, not a first boot.
  if ! have docker; then
    return 1
  fi
  docker ps --format '{{.Names}}' 2>/dev/null \
    | grep -qE '^(queai_traefik|queai_kernel)$'
}

ensure_port_free() {
  # QueAI ships with fixed ports (8473 hub, 9473 Traefik dashboard).
  # Deliberate choice not to reassign dynamically: the landing page, README
  # and docs advertise 8473 unconditionally; a dynamic port would create
  # inconsistency between what we promise and what the user sees.
  #
  # BUT if the official QueAI containers are already running, the port is
  # "occupied by ourselves" — that's a legitimate reinstall, not a real
  # collision. Skipping the check lets docker compose up -d --build do its
  # job: recreate with the new image without losing state. This closes the
  # last gap in installer idempotency (running it twice doesn't break).
  step "Checking ports"

  if queai_already_running; then
    log "QueAI is already deployed on this host — skipping port check"
    log "(the container itself uses 8473/9473; docker compose will handle the refresh)"
    return 0
  fi

  local web_port dash_port
  web_port="$(grep -E '^QUEAI_PORT=' "$INSTALL_DIR/.env" | head -1 | cut -d= -f2 | tr -d '\"')"
  dash_port="$(grep -E '^QUEAI_TRAEFIK_DASHBOARD_PORT=' "$INSTALL_DIR/.env" | head -1 | cut -d= -f2 | tr -d '\"')"
  web_port="${web_port:-8473}"
  dash_port="${dash_port:-9473}"

  _abort_if_port_busy "$web_port" "web hub (QUEAI_PORT)"
  _abort_if_port_busy "$dash_port" "Traefik dashboard (QUEAI_TRAEFIK_DASHBOARD_PORT)"
  log "Ports free: $web_port, $dash_port"
}

_abort_if_port_busy() {
  local port="$1" label="$2"
  if ! port_in_use "$port"; then
    return 0
  fi
  err "Port $port is in use ($label)."
  err ""
  err "QueAI uses fixed ports (8473 / 9473) to keep the documentation and"
  err "the UI consistent. If you need a different port, install manually:"
  err ""
  err "  git clone https://github.com/queai-project/QueAI.git ~/QueAI"
  err "  cd ~/QueAI"
  err "  cp .env.example .env"
  err "  # Edit .env and change QUEAI_PORT to a free port"
  err "  docker compose up -d --build"
  err ""
  err "To see what's using it: 'sudo ss -tlnp sport = :$port'."
  exit 1
}

bootstrap_env() {
  step "Preparing configuration"
  if [[ ! -f "$INSTALL_DIR/.env" && -f "$INSTALL_DIR/.env.example" ]]; then
    log "Creating .env from .env.example"
    run "cp '$INSTALL_DIR/.env.example' '$INSTALL_DIR/.env'"
  else
    log ".env already exists (not overwriting)"
  fi

  # The kernel refuses to start with DEBUG=False and an empty SECRET_KEY,
  # and .env.example ships with both secrets blank on purpose (we don't
  # commit defaults). We generate strong values on first boot — but respect
  # any value the user has already put in place.
  if [[ -f "$INSTALL_DIR/.env" ]]; then
    inject_secret_if_empty "SECRET_KEY" 50
    inject_secret_if_empty "QUEAI_API_TOKEN" 40
  fi
}

prompt_admin_credentials() {
  # The kernel auto-creates a superuser on every boot from
  # QUEAI_ADMIN_USER/QUEAI_ADMIN_PASSWORD. The .env.example ships with
  # `admin/changeme` as a marker — that should NOT reach a real kernel. If
  # the values are still the defaults, we ask for new credentials.
  step "Admin account"

  local cur_user cur_pass
  cur_user="$(grep -E '^QUEAI_ADMIN_USER=' "$INSTALL_DIR/.env" | head -1 | cut -d= -f2 | tr -d '"')"
  cur_pass="$(grep -E '^QUEAI_ADMIN_PASSWORD=' "$INSTALL_DIR/.env" | head -1 | cut -d= -f2 | tr -d '"')"

  # Installer re-run: if the password is no longer the "changeme" marker,
  # the first run (or the user themselves) already configured something
  # real. We don't touch it.
  if [[ -n "$cur_pass" && "$cur_pass" != "changeme" ]]; then
    log "Admin credentials already configured — not overwriting"
    return
  fi

  if $DRY_RUN; then
    dim "[dry-run] would prompt for admin username and password"
    return
  fi

  # No tty (curl|bash in CI, container without -t) or --unattended: we
  # generate a strong password automatically and show it at the end of the
  # install — ONCE. The user must write it down.
  if $UNATTENDED || [ ! -r /dev/tty ]; then
    GENERATED_ADMIN_PASSWORD="$(gen_secret 18)"
    update_env_kv "QUEAI_ADMIN_USER" "${cur_user:-admin}"
    update_env_kv "QUEAI_ADMIN_PASSWORD" "$GENERATED_ADMIN_PASSWORD"
    warn "No interactive terminal: I generated a random password for admin."
    warn "It will be shown at the end of the installer (won't be shown again)."
    return
  fi

  # Interactive mode
  local admin_user pass1 pass2
  log "Set up the kernel administrator account."
  read -r -p "Username [admin]: " admin_user </dev/tty
  admin_user="${admin_user:-admin}"

  while true; do
    read -r -s -p "Password (min. 8 characters): " pass1 </dev/tty
    echo
    if [[ ${#pass1} -lt 8 ]]; then
      warn "Too short. Minimum 8 characters."
      continue
    fi
    # These characters break .env parsing for Docker Compose.
    case "$pass1" in
      *['"\$`']*)
        warn "Avoid the characters: \" \\ \$ \` (they break the .env)."
        continue
        ;;
    esac
    read -r -s -p "Repeat password: " pass2 </dev/tty
    echo
    if [[ "$pass1" != "$pass2" ]]; then
      warn "Passwords don't match. Try again."
      continue
    fi
    break
  done

  update_env_kv "QUEAI_ADMIN_USER" "$admin_user"
  update_env_kv "QUEAI_ADMIN_PASSWORD" "$pass1"
  log "Credentials saved (username: $admin_user)"
}

start_services() {
  step "Bringing services up"
  if $DRY_RUN; then
    dim "[dry-run] cd $INSTALL_DIR && docker compose up -d --build"
    return
  fi

  cd "$INSTALL_DIR"

  # Pick the compose binary we have available (v2 plugin or v1 binary).
  local compose_bin="docker compose"
  if ! docker compose version >/dev/null 2>&1; then
    compose_bin="docker-compose"
  fi

  if [ -n "$DOCKER_RUNTIME_WRAP" ]; then
    # sg docker -c "..." opens a sub-shell with the docker group applied.
    # We pass the cd + the full command as a single string.
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
${C_INFO}✓ $APP_NAME installed successfully${C_RESET}
${C_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}

  Open QueAI:        ${C_BOLD}http://localhost:${port}/${C_RESET}

  Directory:         $INSTALL_DIR
  Logs:              cd $INSTALL_DIR && docker compose logs -f
  Stop:              cd $INSTALL_DIR && docker compose down

  Documentation:     $INSTALL_DIR/docs/
  Report bugs:       https://github.com/queai-project/QueAI/issues

EOF

  if [[ -n "$GENERATED_ADMIN_PASSWORD" ]]; then
    cat <<EOF
${C_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}
${C_WARN}⚠ Generated credentials — write them down, they will NOT be shown again${C_RESET}
${C_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}

  Username:   ${admin_user}
  Password:   ${GENERATED_ADMIN_PASSWORD}

  Change it from the UI (Account → Change password) after your
  first login, or set QUEAI_ADMIN_ROTATE_PASSWORD=true in .env so
  the kernel rotates it on the next boot.

EOF
  fi
}

# ----------------------------------------------------------------------------
# Main flow
# ----------------------------------------------------------------------------
main() {
  echo -e "${C_BOLD}$APP_NAME — installer${C_RESET}"
  $DRY_RUN  && warn "Mode --dry-run: no real changes will be made."
  $UNATTENDED && warn "Mode --unattended: using defaults without asking."

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
