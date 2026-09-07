"""Evaluate the trained customer-churn model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.training.train import MODEL_FEATURES, TARGET_COLUMN

DEFAULT_TEST_INPUT = Path("data/processed/test.csv")
DEFAULT_MODEL_INPUT = Path("models/churn_model.joblib")
DEFAULT_METRICS_OUTPUT = Path("reports/metrics/metrics.json")


def evaluate_model(
    test_input: Path,
    model_input: Path,
) -> dict[str, float | int]:
    """Evaluate the saved model against the test dataset."""
    if not test_input.is_file():
        raise FileNotFoundError(f"Test dataset does not exist: {test_input}")

    if not model_input.is_file():
        raise FileNotFoundError(f"Model does not exist: {model_input}")

    test_data = pd.read_csv(test_input)

    if test_data.isna().any().any():
        raise ValueError("Test dataset contains missing values")

    model = joblib.load(model_input)

    features = test_data[MODEL_FEATURES]
    target = test_data[TARGET_COLUMN]

    predictions = model.predict(features)
    probabilities = model.predict_proba(features)[:, 1]

    true_negative, false_positive, false_negative, true_positive = confusion_matrix(
        target, predictions
    ).ravel()

    return {
        "accuracy": float(accuracy_score(target, predictions)),
        "precision": float(precision_score(target, predictions, zero_division=0)),
        "recall": float(recall_score(target, predictions, zero_division=0)),
        "f1_score": float(f1_score(target, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(target, probabilities)),
        "true_negative": int(true_negative),
        "false_positive": int(false_positive),
        "false_negative": int(false_negative),
        "true_positive": int(true_positive),
        "test_samples": len(test_data),
    }


def write_metrics(
    metrics: dict[str, float | int],
    output_path: Path,
) -> None:
    """Write evaluation metrics as stable JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_arguments() -> argparse.Namespace:
    """Parse evaluation arguments."""
    parser = argparse.ArgumentParser(description="Evaluate the customer-churn model.")

    parser.add_argument(
        "--test-input",
        type=Path,
        default=DEFAULT_TEST_INPUT,
    )

    parser.add_argument(
        "--model-input",
        type=Path,
        default=DEFAULT_MODEL_INPUT,
    )

    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=DEFAULT_METRICS_OUTPUT,
    )

    parser.add_argument(
        "--minimum-accuracy",
        type=float,
        default=0.65,
    )

    parser.add_argument(
        "--minimum-roc-auc",
        type=float,
        default=0.70,
    )

    return parser.parse_args()


def main() -> None:
    """Evaluate the model and enforce baseline quality gates."""
    arguments = parse_arguments()

    metrics = evaluate_model(
        test_input=arguments.test_input,
        model_input=arguments.model_input,
    )

    accuracy_passed = metrics["accuracy"] >= arguments.minimum_accuracy
    roc_auc_passed = metrics["roc_auc"] >= arguments.minimum_roc_auc
    quality_gate_passed = accuracy_passed and roc_auc_passed

    metrics["minimum_accuracy"] = arguments.minimum_accuracy
    metrics["minimum_roc_auc"] = arguments.minimum_roc_auc
    metrics["quality_gate_passed"] = quality_gate_passed

    write_metrics(metrics, arguments.metrics_output)

    print(json.dumps(metrics, indent=2, sort_keys=True))

    if not quality_gate_passed:
        raise SystemExit("Model failed the configured quality gate")

    print("PASS: model satisfied the configured quality gate")


if __name__ == "__main__":
    main()
