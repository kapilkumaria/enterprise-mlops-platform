#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${PROJECT_ROOT}/api.pid"
LOG_FILE="${PROJECT_ROOT}/api-server.log"
HEALTH_URL="http://127.0.0.1:8000/health"
MLFLOW_URL="http://127.0.0.1:5000/health"

cd "${PROJECT_ROOT}"

if [[ -f "${PID_FILE}" ]]; then
    EXISTING_PID="$(cat "${PID_FILE}")"

    if kill -0 "${EXISTING_PID}" 2>/dev/null; then
        echo "Prediction API is already running with PID ${EXISTING_PID}"
        echo "API URL:  http://127.0.0.1:8000"
        echo "API docs: http://127.0.0.1:8000/docs"
        exit 0
    fi

    echo "Removing stale API PID file"
    rm -f "${PID_FILE}"
fi

if ! curl --fail --silent "${MLFLOW_URL}" >/dev/null; then
    echo "ERROR: MLflow must be healthy before starting the API"
    exit 1
fi

if [[ ! -x "${PROJECT_ROOT}/.venv/bin/uvicorn" ]]; then
    echo "ERROR: Uvicorn is not installed in the virtual environment"
    exit 1
fi

nohup env \
    MLFLOW_TRACKING_URI="http://127.0.0.1:5000" \
    MODEL_URI="models:/customer-churn-model@candidate" \
    "${PROJECT_ROOT}/.venv/bin/uvicorn" \
    src.api.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    >"${LOG_FILE}" 2>&1 &

API_PID=$!
echo "${API_PID}" >"${PID_FILE}"

for attempt in $(seq 1 60); do
    if curl --fail --silent "${HEALTH_URL}" >/dev/null; then
        echo "Prediction API started successfully"
        echo "PID:       ${API_PID}"
        echo "API URL:   http://127.0.0.1:8000"
        echo "API docs:  http://127.0.0.1:8000/docs"
        echo "Log file:  ${LOG_FILE}"
        exit 0
    fi

    if ! kill -0 "${API_PID}" 2>/dev/null; then
        echo "ERROR: Prediction API exited before becoming healthy"
        tail -60 "${LOG_FILE}"
        rm -f "${PID_FILE}"
        exit 1
    fi

    sleep 1
done

echo "ERROR: API did not become healthy within 60 seconds"
tail -60 "${LOG_FILE}"
exit 1
