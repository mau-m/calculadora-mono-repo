#!/bin/bash
set -e

# Lee la versión desplegada (se escribió durante el workflow)
APP_VERSION=$(cat /opt/mi-app/.app-version)
export APP_VERSION

cd /opt/mi-app

# Autentica Docker con ECR usando el rol de la instancia (sin credenciales hardcodeadas)
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  940075379174.dkr.ecr.us-east-1.amazonaws.com/calculadora/backend

# Descarga las nuevas imágenes
docker compose -f docker-compose-aws.yml pull

# Detiene los contenedores actuales y levanta los nuevos
docker compose -f docker-compose-aws.yml down --remove-orphans
docker compose -f docker-compose-aws.yml up -d

# Limpia imágenes antiguas para no llenar el disco
docker image prune -f