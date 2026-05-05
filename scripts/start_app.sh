#!/bin/bash
set -euo pipefail

# Lee la versión desplegada (se escribió durante el workflow). Fallback: latest
APP_VERSION="latest"
if [[ -f /opt/mi-app/.app-version ]]; then
  APP_VERSION="$(cat /opt/mi-app/.app-version)"
fi
export APP_VERSION

cd /opt/mi-app

# Autentica Docker con ECR usando el rol de la instancia (sin credenciales hardcodeadas)
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REGISTRY="940075379174.dkr.ecr.us-east-1.amazonaws.com"

aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin \
  "$ECR_REGISTRY"

# Descarga las nuevas imágenes (backend + frontend)
docker compose -f docker-compose-aws.yml pull

# Detiene los contenedores actuales y levanta los nuevos
docker compose -f docker-compose-aws.yml down --remove-orphans
docker compose -f docker-compose-aws.yml up -d

# Limpia imágenes antiguas para no llenar el disco
docker image prune -f