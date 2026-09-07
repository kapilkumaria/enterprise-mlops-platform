#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${PROJECT_ROOT}/mlflow.pid"
LOG_FILE="${PROJECT_ROOT}/mlflow-server.log"
HEALTH_URL="http://127.0.0.1:5000/health"

cd "${PROJECT_ROOT}"

if [[ -f "${PID_FILE}" ]]; then
    EXISTING_PID="$(cat "${PID_FILE}")"

    if kill -0 "${EXISTING_PID}" 2>/dev/null; then
        echo "MLflow is already running with PID ${EXISTING_PID}"
        echo "MLflow UI: http://127.0.0.1:5000"
        exit 0
    fi

    echo "Removing stale MLflow PID file"
    rm -f "${PID_FILE}"
fi

if [[ ! -x "${PROJECT_ROOT}/.venv/bin/mlflow" ]]; then
    echo "ERROR: MLflow is not installed in the project virtual environment"
    exit 1
fi

nohup "${PROJECT_ROOT}/.venv/bin/mlflow" server \
    --backend-store-uri "sqlite:///${PROJECT_ROOT}/mlflow.db" \
    --artifacts-destination "${PROJECT_ROOT}/mlartifacts" \
    --host 127.0.0.1 \
    --port 5000 \
    >"${LOG_FILE}" 2>&1 &

MLFLOW_PID=$!
echo "${MLFLOW_PID}" >"${PID_FILE}"

for attempt in $(seq 1 60); do
    if curl --fail --silent "${HEALTH_URL}" >/dev/null; then
        echo "MLflow started successfully"
        echo "PID:       ${MLFLOW_PID}"
        echo "MLflow UI: http://127.0.0.1:5000"
        echo "Log file:  ${LOG_FILE}"
        exit 0
    fi

    if ! kill -0 "${MLFLOW_PID}" 2>/dev/null; then
        echo "ERROR: MLflow exited before becoming healthy"
        tail -40 "${LOG_FILE}"
        rm -f "${PID_FILE}"
        exit 1
    fi

    sleep 1
done

echo "ERROR: MLflow did not become healthy within 60 seconds"
tail -40 "${LOG_FILE}"
exit 1
