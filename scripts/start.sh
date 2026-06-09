#!/usr/bin/env bash
set -euo pipefail

# Build frontend, sync static assets, then build Docker image and run container.
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
IMAGE_NAME=pm-mvp-app
CONTAINER_NAME=pm-mvp-app

echo "Building frontend static assets..."
cd "${ROOT_DIR}/frontend"
npm run build

echo "Syncing frontend output to backend/static..."
mkdir -p "${ROOT_DIR}/backend/static"
rm -rf "${ROOT_DIR}/backend/static"/*
cp -R "${ROOT_DIR}/frontend/out/." "${ROOT_DIR}/backend/static/"

echo "Building Docker image ${IMAGE_NAME}..."
docker build -t ${IMAGE_NAME} "${ROOT_DIR}"

echo "Starting container ${CONTAINER_NAME}..."
ENV_MOUNTS=()
if [ -f "${ROOT_DIR}/.env" ]; then
  ENV_MOUNTS+=( -v "${ROOT_DIR}/.env:/app/.env:ro" )
fi

docker run -d --name ${CONTAINER_NAME} -p 8000:8000 \
  -v "${ROOT_DIR}/backend/data:/app/backend/data" \
  "${ENV_MOUNTS[@]}" \
  ${IMAGE_NAME}

echo "Container started. Visit http://localhost:8000"
