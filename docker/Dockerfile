FROM python:3.12-slim

ARG APP_USER=appuser
ARG APP_UID=10001

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV MLFLOW_TRACKING_URI=http://127.0.0.1:5000
ENV MODEL_URI=models:/customer-churn-model@candidate

WORKDIR /app

RUN groupadd \
        --gid "${APP_UID}" \
        "${APP_USER}" \
    && useradd \
        --uid "${APP_UID}" \
        --gid "${APP_UID}" \
        --create-home \
        --shell /usr/sbin/nologin \
        "${APP_USER}"

COPY requirements-serving.txt .

RUN python -m pip install \
        --upgrade pip \
    && python -m pip install \
        --requirement requirements-serving.txt

COPY src ./src

USER ${APP_UID}:${APP_UID}

EXPOSE 8000

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=30s \
    --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
