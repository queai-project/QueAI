#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="QueAI"
REPO_URL="https://github.com/alejandrofonsecacuza/QueAI.git"
INSTALL_DIR="$HOME/$APP_NAME"

log()  { echo -e "\033[1;32m[INFO]\033[0m $1"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $1"; }
err()  { echo -e "\033[1;31m[ERROR]\033[0m $1"; }

require_root() {
  if [[ $EUID -ne 0 ]]; then
    err "Este script requiere privilegios root (usa sudo)."
    exit 1
  fi
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

purge_old_docker() {
  warn "Eliminando cualquier instalación previa de Docker..."
  systemctl stop docker 2>/dev/null || true
  systemctl stop docker.socket 2>/dev/null || true

  apt-get remove --purge -y \
    docker docker-engine docker.io containerd runc \
    docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin || true

  rm -rf /var/lib/docker
  rm -rf /var/lib/containerd
  rm -rf /etc/docker
  rm -f /etc/apt/sources.list.d/docker.list
  rm -f /etc/apt/keyrings/docker.asc

  systemctl daemon-reload
  apt-get update
}

install_docker_official() {
  log "Instalando Docker oficial..."
  curl -fsSL https://get.docker.com | sh
}

verify_docker_running() {
  log "Verificando estado de Docker..."

  if ! systemctl is-active --quiet docker; then
    err "Docker no está corriendo. Mostrando diagnóstico:"
    systemctl status docker --no-pager
    exit 1
  fi

  log "Docker está activo."
}

install_git_if_missing() {
  if ! command_exists git; then
    log "Instalando Git..."
    apt-get update
    apt-get install -y git
  fi
}

clone_repository() {
  log "Preparando directorio en $INSTALL_DIR..."

  if [[ -d "$INSTALL_DIR" ]]; then
    warn "El directorio ya existe. Eliminándolo para instalación limpia..."
    rm -rf "$INSTALL_DIR"
  fi

  git clone "$REPO_URL" "$INSTALL_DIR"
}

start_application() {
  cd "$INSTALL_DIR"
  log "Levantando servicios con Docker Compose..."
  docker compose up -d
}

main() {
  require_root

  log "Iniciando instalación de $APP_NAME..."

  install_git_if_missing

  if command_exists docker; then
    warn "Docker detectado. Se realizará reinstalación limpia para evitar conflictos."
    purge_old_docker
  fi

  install_docker_official
  verify_docker_running

  clone_repository
  start_application

  log "--------------------------------------------"
  log "Instalación completada correctamente."
  log "Ver logs: cd $INSTALL_DIR && docker compose logs -f"
  log "--------------------------------------------"
}

main "$@"
