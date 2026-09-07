#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${PROJECT_ROOT}/api.pid"
HEALTH_URL="http://127.0.0.1:8000/health"

if [[ ! -f "${PID_FILE}" ]]; then
    echo "Prediction API is not running: no PID file exists"
    exit 1
fi

API_PID="$(cat "${PID_FILE}")"

if ! kill -0 "${API_PID}" 2>/dev/null; then
    echo "Prediction API is not running: stale PID ${API_PID}"
    exit 1
fi

if curl --fail --silent "${HEALTH_URL}" >/dev/null; then
    echo "Prediction API is healthy"
    echo "PID:       ${API_PID}"
    echo "API URL:   http://127.0.0.1:8000"
    echo "API docs:  http://127.0.0.1:8000/docs"
else
    echo "API process exists but its health endpoint is unavailable"
    exit 1
fi
