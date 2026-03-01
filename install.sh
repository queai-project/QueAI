#!/usr/bin/env bash

set -Eeuo pipefail

########################################
# CONFIG
########################################

REPO_URL="https://github.com/alejandrofonsecacuza/QueAI.git"
INSTALL_DIR="$HOME/QueAI"

########################################
# HELPERS
########################################

log() { echo -e "\033[1;32m[INFO]\033[0m $1"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $1"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $1"; }

require_root_if_needed() {
  if [ "$EUID" -ne 0 ]; then
    SUDO="sudo"
  else
    SUDO=""
  fi
}

abort_if_container() {
  if grep -qa docker /proc/1/cgroup 2>/dev/null; then
    error "Detectado entorno contenedor. Este instalador requiere un sistema real."
    exit 1
  fi
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

########################################
# START
########################################

log "Iniciando instalación de QueAI..."

require_root_if_needed
abort_if_container

########################################
# 1. Dependencias básicas
########################################

if ! command_exists git; then
  log "Instalando Git..."
  $SUDO apt-get update -qq
  $SUDO apt-get install -y git
fi

if ! command_exists curl; then
  log "Instalando curl..."
  $SUDO apt-get update -qq
  $SUDO apt-get install -y curl
fi

########################################
# 2. Docker Installation Logic
########################################

install_official_docker() {
  log "Instalando Docker oficial (docker-ce)..."
  curl -fsSL https://get.docker.com | $SUDO sh
}

remove_docker_io_if_present() {
  if dpkg -l | grep -q docker.io; then
    warn "Detectado docker.io (Ubuntu package). Removiendo..."
    $SUDO apt-get remove -y docker.io || true
  fi
}

docker_needs_install=false

if ! command_exists docker; then
  docker_needs_install=true
else
  if ! docker info >/dev/null 2>&1; then
    warn "Docker binario existe pero daemon no funcional."
    docker_needs_install=true
  fi
fi

if [ "$docker_needs_install" = true ]; then
  remove_docker_io_if_present
  install_official_docker
else
  log "Docker detectado."
fi

########################################
# 3. Ensure Docker is running
########################################

if ! $SUDO systemctl is-active --quiet docker; then
  log "Iniciando servicio Docker..."
  $SUDO systemctl enable docker >/dev/null 2>&1 || true
  $SUDO systemctl start docker
fi

########################################
# 4. Docker Compose V2
########################################

if ! docker compose version >/dev/null 2>&1; then
  warn "Docker Compose V2 no encontrado. Reinstalando Docker oficial..."
  install_official_docker
fi

########################################
# 5. Add user to docker group (non-root)
########################################

if [ "$EUID" -ne 0 ]; then
  if ! groups "$USER" | grep -q docker; then
    log "Añadiendo usuario $USER al grupo docker..."
    $SUDO usermod -aG docker "$USER"
    warn "Deberás cerrar sesión y volver a entrar para aplicar el grupo."
  fi
fi

########################################
# 6. Clone or Update Repo
########################################

log "Preparando directorio $INSTALL_DIR"

if [ -d "$INSTALL_DIR/.git" ]; then
  log "Repositorio existente detectado. Actualizando..."
  git -C "$INSTALL_DIR" pull
else
  rm -rf "$INSTALL_DIR"
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

########################################
# 7. Start Services
########################################

cd "$INSTALL_DIR"

log "Levantando servicios con Docker Compose..."
$SUDO docker compose up -d --build

########################################
# DONE
########################################

log "--------------------------------------"
log "QueAI está ejecutándose correctamente."
log "Logs: cd $INSTALL_DIR && docker compose logs -f"
log "--------------------------------------"
