#!/usr/bin/env bash
set -euo pipefail

# Build Docker image and run container for the FastAPI backend
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
IMAGE_NAME=pm-mvp-app
CONTAINER_NAME=pm-mvp-app

echo "Building Docker image ${IMAGE_NAME}..."
docker build -t ${IMAGE_NAME} "${ROOT_DIR}"

echo "Starting container ${CONTAINER_NAME}..."
docker run -d --name ${CONTAINER_NAME} -p 8000:8000 \
  -v "${ROOT_DIR}/backend/data:/app/backend/data" \
  ${IMAGE_NAME}

echo "Container started. Visit http://localhost:8000"
