"""Idempotently register the configured MLflow model artifact."""

from __future__ import annotations

import os
import time

import mlflow
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException

TRACKING_URI = os.environ["MLFLOW_TRACKING_URI"]
MODEL_ARTIFACT_URI = os.environ["MODEL_ARTIFACT_URI"]
MODEL_NAME = os.getenv("MODEL_NAME", "customer-churn-model")
MODEL_ALIAS = os.getenv("MODEL_ALIAS", "candidate")


def wait_for_mlflow(client: MlflowClient) -> None:
    """Wait until the MLflow tracking server responds."""
    for attempt in range(60):
        try:
            client.search_experiments()
            return
        except Exception as exc:
            if attempt == 59:
                raise RuntimeError("MLflow did not become ready") from exc
            time.sleep(2)


def ensure_registered_model(client: MlflowClient) -> None:
    """Create the registered model when it does not exist."""
    try:
        client.get_registered_model(MODEL_NAME)
    except MlflowException as exc:
        if "RESOURCE_DOES_NOT_EXIST" not in str(exc):
            raise
        client.create_registered_model(MODEL_NAME)


def main() -> None:
    """Register the configured model and assign its alias."""
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_registry_uri(TRACKING_URI)

    client = MlflowClient(
        tracking_uri=TRACKING_URI,
        registry_uri=TRACKING_URI,
    )

    wait_for_mlflow(client)
    ensure_registered_model(client)

    try:
        current = client.get_model_version_by_alias(
            MODEL_NAME,
            MODEL_ALIAS,
        )
    except MlflowException as exc:
        if "RESOURCE_DOES_NOT_EXIST" in str(exc):
            current = None
        else:
            raise

    if current is not None and current.source == MODEL_ARTIFACT_URI:
        print(
            f"PASS: {MODEL_NAME}@{MODEL_ALIAS} already points to "
            f"{MODEL_ARTIFACT_URI}"
        )
        return

    model_version = mlflow.register_model(
        model_uri=MODEL_ARTIFACT_URI,
        name=MODEL_NAME,
    )

    client.set_registered_model_alias(
        name=MODEL_NAME,
        alias=MODEL_ALIAS,
        version=str(model_version.version),
    )

    client.set_registered_model_tag(
        name=MODEL_NAME,
        key="project",
        value="enterprise-mlops-platform",
    )

    client.set_model_version_tag(
        name=MODEL_NAME,
        version=str(model_version.version),
        key="validation_status",
        value="passed",
    )

    print(
        f"PASS: registered {MODEL_NAME}@{MODEL_ALIAS} "
        f"as version {model_version.version}"
    )


if __name__ == "__main__":
    main()
