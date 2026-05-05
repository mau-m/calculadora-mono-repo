#!/bin/bash
set -e

# Instala dependencias de sistema necesarias
apt-get update
apt-get install -y \
  aws-cli \
  docker.io \
  python3-pip

# Limpia el directorio de aplicación anterior
rm -rf /opt/mi-app
mkdir -p /opt/mi-app