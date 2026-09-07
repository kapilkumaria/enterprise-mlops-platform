"""Register a validated MLflow model and assign a lifecycle alias."""

from __future__ import annotations

import argparse
from typing import Any

import mlflow
from mlflow import MlflowClient

DEFAULT_TRACKING_URI = "http://127.0.0.1:5000"
DEFAULT_EXPERIMENT_NAME = "customer-churn-classification"
DEFAULT_MODEL_NAME = "customer-churn-model"
DEFAULT_ALIAS = "candidate"


def run_passed_quality_gate(run: Any) -> bool:
    """Return whether an MLflow run passed the model quality gate."""
    quality_tag = run.data.tags.get(
        "quality_gate_passed",
        "false",
    ).lower()

    accuracy = run.data.metrics.get("accuracy", 0.0)
    roc_auc = run.data.metrics.get("roc_auc", 0.0)

    minimum_accuracy = float(run.data.params.get("minimum_accuracy", 1.0))
    minimum_roc_auc = float(run.data.params.get("minimum_roc_auc", 1.0))

    return (
        run.info.status == "FINISHED"
        and quality_tag == "true"
        and accuracy >= minimum_accuracy
        and roc_auc >= minimum_roc_auc
    )


def build_run_model_uri(run_id: str) -> str:
    """Build the MLflow URI for the model logged by a run."""
    if not run_id:
        raise ValueError("Run ID must not be empty")

    return f"runs:/{run_id}/model"


def find_latest_eligible_run(
    client: MlflowClient,
    experiment_name: str,
) -> Any:
    """Find the newest successful run that passed validation."""
    experiment = client.get_experiment_by_name(experiment_name)

    if experiment is None:
        raise ValueError(f"MLflow experiment does not exist: {experiment_name}")

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["attributes.start_time DESC"],
    )

    for run in runs:
        if run_passed_quality_gate(run):
            return run

    raise ValueError("No finished MLflow run passed the configured quality gate")


def register_candidate_model(
    tracking_uri: str,
    experiment_name: str,
    model_name: str,
    alias: str,
) -> tuple[str, str]:
    """Register the newest eligible model and assign its alias."""
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_registry_uri(tracking_uri)

    client = MlflowClient(
        tracking_uri=tracking_uri,
        registry_uri=tracking_uri,
    )

    selected_run = find_latest_eligible_run(
        client=client,
        experiment_name=experiment_name,
    )

    model_uri = build_run_model_uri(selected_run.info.run_id)

    model_version = mlflow.register_model(
        model_uri=model_uri,
        name=model_name,
    )

    version = str(model_version.version)

    client.set_registered_model_alias(
        name=model_name,
        alias=alias,
        version=version,
    )

    client.set_registered_model_tag(
        name=model_name,
        key="project",
        value="enterprise-mlops-platform",
    )
    client.set_registered_model_tag(
        name=model_name,
        key="problem_type",
        value="binary-classification",
    )

    client.set_model_version_tag(
        name=model_name,
        version=version,
        key="validation_status",
        value="passed",
    )
    client.set_model_version_tag(
        name=model_name,
        version=version,
        key="source_run_id",
        value=selected_run.info.run_id,
    )
    client.set_model_version_tag(
        name=model_name,
        version=version,
        key="quality_gate_passed",
        value="true",
    )

    client.update_model_version(
        name=model_name,
        version=version,
        description=(
            "Validated logistic-regression customer-churn model. "
            "This version passed the configured accuracy and "
            "ROC-AUC quality gates."
        ),
    )

    return version, selected_run.info.run_id


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Register a validated MLflow model.")
    parser.add_argument(
        "--tracking-uri",
        default=DEFAULT_TRACKING_URI,
    )
    parser.add_argument(
        "--experiment-name",
        default=DEFAULT_EXPERIMENT_NAME,
    )
    parser.add_argument(
        "--model-name",
        default=DEFAULT_MODEL_NAME,
    )
    parser.add_argument(
        "--alias",
        default=DEFAULT_ALIAS,
    )
    return parser.parse_args()


def main() -> None:
    """Register the latest validated model."""
    arguments = parse_arguments()

    version, run_id = register_candidate_model(
        tracking_uri=arguments.tracking_uri,
        experiment_name=arguments.experiment_name,
        model_name=arguments.model_name,
        alias=arguments.alias,
    )

    print(f"Registered model: {arguments.model_name}")
    print(f"Model version:    {version}")
    print(f"Model alias:      {arguments.alias}")
    print(f"Source run ID:    {run_id}")
    print(f"Model URI:       models:/{arguments.model_name}@{arguments.alias}")
    print("PASS: validated model registered successfully")


if __name__ == "__main__":
    main()
