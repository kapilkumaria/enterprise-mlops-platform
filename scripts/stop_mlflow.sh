#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${PROJECT_ROOT}/mlflow.pid"

if [[ ! -f "${PID_FILE}" ]]; then
    echo "MLflow is not running: no PID file exists"
    exit 0
fi

MLFLOW_PID="$(cat "${PID_FILE}")"

if ! kill -0 "${MLFLOW_PID}" 2>/dev/null; then
    echo "Removing stale PID file for process ${MLFLOW_PID}"
    rm -f "${PID_FILE}"
    exit 0
fi

kill "${MLFLOW_PID}"

for attempt in $(seq 1 20); do
    if ! kill -0 "${MLFLOW_PID}" 2>/dev/null; then
        rm -f "${PID_FILE}"
        echo "MLflow stopped successfully"
        exit 0
    fi

    sleep 1
done

echo "MLflow is still shutting down; PID ${MLFLOW_PID}"
exit 1
