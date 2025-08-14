#!/bin/bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

echo "--- Building Services ---"

# Очистка переменных
unset APP_TAG SERVER_HOST SERVER_PORT 

# Создаем необходимые директории
mkdir -p "$PROJECT_ROOT/docker/app_logs"

# Загрузка .env
if [[ -f "$ENV_FILE" ]]; then
    while IFS='=' read -r key value; do
        if [[ -n $key && $key != '#'* ]]; then
            key=$(echo "$key" | tr -d '\r')
            value=$(echo "$value" | tr -d '\r')
            export "$key"="$value"
        fi
    done < "$ENV_FILE"
else
    echo "WARNING: .env file not found, using defaults"
fi

if [[ -z "${APP_TAG:-}" ]]; then
  echo "ERROR: APP_TAG is not set in .env"
  exit 1
fi

# Build
echo "Building Docker images..."
docker-compose -f "$PROJECT_ROOT/docker/docker-compose.yml" build --build-arg APP_TAG="$APP_TAG" vggt-app
docker image prune -f
docker system prune -f

echo "--- Build completed successfully ---"