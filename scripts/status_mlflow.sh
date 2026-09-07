#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${PROJECT_ROOT}/mlflow.pid"
HEALTH_URL="http://127.0.0.1:5000/health"

if [[ ! -f "${PID_FILE}" ]]; then
    echo "MLflow is not running: no PID file exists"
    exit 1
fi

MLFLOW_PID="$(cat "${PID_FILE}")"

if ! kill -0 "${MLFLOW_PID}" 2>/dev/null; then
    echo "MLflow is not running: stale PID ${MLFLOW_PID}"
    exit 1
fi

if curl --fail --silent "${HEALTH_URL}" >/dev/null; then
    echo "MLflow is healthy"
    echo "PID:       ${MLFLOW_PID}"
    echo "MLflow UI: http://127.0.0.1:5000"
else
    echo "MLflow process exists but its health endpoint is unavailable"
    exit 1
fi
