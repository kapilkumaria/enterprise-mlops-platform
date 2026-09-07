#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${PROJECT_ROOT}/api.pid"

if [[ ! -f "${PID_FILE}" ]]; then
    echo "Prediction API is not running: no PID file exists"
    exit 0
fi

API_PID="$(cat "${PID_FILE}")"

if ! kill -0 "${API_PID}" 2>/dev/null; then
    echo "Removing stale API PID file for process ${API_PID}"
    rm -f "${PID_FILE}"
    exit 0
fi

kill "${API_PID}"

for attempt in $(seq 1 20); do
    if ! kill -0 "${API_PID}" 2>/dev/null; then
        rm -f "${PID_FILE}"
        echo "Prediction API stopped successfully"
        exit 0
    fi

    sleep 1
done

echo "Prediction API is still shutting down; PID ${API_PID}"
exit 1
