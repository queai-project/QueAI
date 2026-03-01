#!/bin/bash

# Detener el script si algo falla
set -e

echo "🚀 Iniciando la instalación de QueAI..."

# 1. Verificar dependencias básicas (Git)
if ! command -v git &> /dev/null; then
    echo "📦 Git no está instalado. Instalándolo..."
    sudo apt-get update && sudo apt-get install -y git
fi

# 2. Verificar e instalar Docker si no existe
if ! command -v docker &> /dev/null; then
    echo "🐳 Docker no encontrado. Iniciando instalación oficial..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    # Añadir el usuario actual al grupo docker para evitar usar sudo siempre
    sudo usermod -aG docker $USER
    echo "✅ Docker instalado correctamente."
    rm get-docker.sh
else
    echo "✅ Docker ya está instalado."
fi

# 3. Verificar Docker Compose (Plugin V2)
if ! docker compose version &> /dev/null; then
    echo "🔧 Instalando Docker Compose Plugin..."
    sudo apt-get update && sudo apt-get install -y docker-compose-plugin
fi

# 4. Clonar el repositorio
INSTALL_DIR="$HOME/QueAI"
echo "📂 Preparando directorio en $INSTALL_DIR..."

if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️ El directorio ya existe, actualizando contenido..."
    rm -rf "$INSTALL_DIR"
fi

git clone https://github.com/alejandrofonsecacuza/QueAI.git "$INSTALL_DIR"

# 5. Iniciar la aplicación
cd "$INSTALL_DIR"
echo "🚀 Levantando servicios con Docker Compose..."

# Usamos sudo aquí por si el cambio de grupo de arriba aún no ha hecho efecto en esta sesión
sudo docker compose up -d

echo "--------------------------------------------------"
echo "✅ ¡Todo listo! QueAI se está ejecutando en segundo plano."
echo "Puedes ver los logs con: cd $INSTALL_DIR && sudo docker compose logs -f"
echo "--------------------------------------------------"