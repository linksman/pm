#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME=pm-mvp-app

echo "Stopping container ${CONTAINER_NAME}..."
docker stop ${CONTAINER_NAME} 2>/dev/null || true
docker rm ${CONTAINER_NAME} 2>/dev/null || true

echo "Stopped and removed ${CONTAINER_NAME}."
