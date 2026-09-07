"""Log the trained customer-churn model as an MLflow experiment."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
from mlflow.models import infer_signature

from src.training.train import MODEL_FEATURES

DEFAULT_TRACKING_URI = "http://127.0.0.1:5000"
DEFAULT_EXPERIMENT_NAME = "customer-churn-classification"
DEFAULT_RUN_NAME = "logistic-regression-baseline"

MODEL_PATH = Path("models/churn_model.joblib")
TEST_DATA_PATH = Path("data/processed/test.csv")
METRICS_PATH = Path("reports/metrics/metrics.json")
PARAMS_PATH = Path("params.yaml")
DVC_PIPELINE_PATH = Path("dvc.yaml")
DVC_LOCK_PATH = Path("dvc.lock")
DVC_DATASET_PATH = Path("data/raw/customer_churn.csv.dvc")

TRACKED_METRICS = (
    "accuracy",
    "precision",
    "recall",
    "f1_score",
    "roc_auc",
)


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def read_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML mapping from disk."""
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    return content if isinstance(content, dict) else {}


def get_git_commit() -> str:
    """Return the current Git commit hash."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_dataset_hash() -> str:
    """Return the DVC hash for the raw dataset."""
    metadata = read_yaml(DVC_DATASET_PATH)
    outputs = metadata.get("outs", [])

    if not outputs:
        raise ValueError("DVC dataset metadata does not contain an output")

    dataset_hash = outputs[0].get("md5")

    if not dataset_hash:
        raise ValueError("DVC dataset metadata does not contain an MD5 hash")

    return str(dataset_hash)


def select_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    """Return metrics that should be recorded by MLflow."""
    missing = [name for name in TRACKED_METRICS if name not in metrics]

    if missing:
        raise ValueError(
            "Metrics report is missing required metrics: " + ", ".join(missing)
        )

    return {name: float(metrics[name]) for name in TRACKED_METRICS}


def build_logged_parameters(
    project_params: dict[str, Any],
) -> dict[str, Any]:
    """Build a concise parameter set for the MLflow run."""
    train_params = project_params.get("train", {})
    prepare_params = project_params.get("prepare", {})
    evaluate_params = project_params.get("evaluate", {})

    return {
        "model_type": "logistic_regression",
        "regularization_strength": train_params["regularization_strength"],
        "max_iterations": train_params["max_iterations"],
        "training_random_state": train_params["random_state"],
        "test_size": prepare_params["test_size"],
        "split_random_state": prepare_params["random_state"],
        "minimum_accuracy": evaluate_params["minimum_accuracy"],
        "minimum_roc_auc": evaluate_params["minimum_roc_auc"],
    }


def log_experiment(
    tracking_uri: str,
    experiment_name: str,
    run_name: str,
) -> tuple[str, str]:
    """Log one trained-model experiment and return its IDs."""
    model = joblib.load(MODEL_PATH)
    test_data = pd.read_csv(TEST_DATA_PATH)
    input_example = test_data[MODEL_FEATURES].head(5)

    predictions = model.predict(input_example)
    signature = infer_signature(input_example, predictions)

    metrics_report = read_json(METRICS_PATH)
    project_params = read_yaml(PARAMS_PATH)

    logged_metrics = select_metrics(metrics_report)
    logged_parameters = build_logged_parameters(project_params)

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=run_name) as active_run:
        mlflow.log_params(logged_parameters)
        mlflow.log_metrics(logged_metrics)

        mlflow.set_tags(
            {
                "project": "enterprise-mlops-platform",
                "problem_type": "binary-classification",
                "dataset": "synthetic-customer-churn",
                "git_commit": get_git_commit(),
                "dvc_dataset_hash": get_dataset_hash(),
                "quality_gate_passed": str(
                    metrics_report["quality_gate_passed"]
                ).lower(),
            }
        )

        mlflow.log_artifact(
            str(METRICS_PATH),
            artifact_path="evaluation",
        )
        mlflow.log_artifact(
            str(PARAMS_PATH),
            artifact_path="pipeline",
        )
        mlflow.log_artifact(
            str(DVC_PIPELINE_PATH),
            artifact_path="pipeline",
        )
        mlflow.log_artifact(
            str(DVC_LOCK_PATH),
            artifact_path="pipeline",
        )

        model_info = mlflow.sklearn.log_model(
            sk_model=model,
            name="model",
            signature=signature,
            input_example=input_example,
        )

        run_id = active_run.info.run_id

    return run_id, model_info.model_uri


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Log the churn model to MLflow.")
    parser.add_argument(
        "--tracking-uri",
        default=DEFAULT_TRACKING_URI,
    )
    parser.add_argument(
        "--experiment-name",
        default=DEFAULT_EXPERIMENT_NAME,
    )
    parser.add_argument(
        "--run-name",
        default=DEFAULT_RUN_NAME,
    )
    return parser.parse_args()


def main() -> None:
    """Run experiment tracking."""
    arguments = parse_arguments()

    run_id, model_uri = log_experiment(
        tracking_uri=arguments.tracking_uri,
        experiment_name=arguments.experiment_name,
        run_name=arguments.run_name,
    )

    print(f"Experiment: {arguments.experiment_name}")
    print(f"Run name:   {arguments.run_name}")
    print(f"Run ID:     {run_id}")
    print(f"Model URI:  {model_uri}")
    print("PASS: model experiment logged successfully")


if __name__ == "__main__":
    main()
