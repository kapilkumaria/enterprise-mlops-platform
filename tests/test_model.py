"""Tests for the trained customer-churn model."""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from src.training.train import MODEL_FEATURES

MODEL_PATH = Path("models/churn_model.joblib")
TEST_PATH = Path("data/processed/test.csv")
METRICS_PATH = Path("reports/metrics/metrics.json")


def test_serialized_model_exists_and_loads() -> None:
    """The serialized artifact must contain a Scikit-learn pipeline."""
    assert MODEL_PATH.is_file()

    model = joblib.load(MODEL_PATH)

    assert isinstance(model, Pipeline)
    assert "preprocessor" in model.named_steps
    assert "classifier" in model.named_steps


def test_model_returns_binary_predictions() -> None:
    """The model must return one binary prediction per customer."""
    model = joblib.load(MODEL_PATH)
    test_data = pd.read_csv(TEST_PATH)
    sample = test_data[MODEL_FEATURES].head(10)

    predictions = model.predict(sample)

    assert len(predictions) == len(sample)
    assert set(predictions).issubset({0, 1})


def test_model_returns_valid_probabilities() -> None:
    """The model must return churn probabilities between zero and one."""
    model = joblib.load(MODEL_PATH)
    test_data = pd.read_csv(TEST_PATH)
    sample = test_data[MODEL_FEATURES].head(10)

    probabilities = model.predict_proba(sample)[:, 1]

    assert len(probabilities) == len(sample)
    assert ((probabilities >= 0.0) & (probabilities <= 1.0)).all()


def test_metrics_file_contains_expected_metrics() -> None:
    """The evaluation report must contain operational model metrics."""
    assert METRICS_PATH.is_file()

    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    expected_metrics = {
        "accuracy",
        "precision",
        "recall",
        "f1_score",
        "roc_auc",
        "true_negative",
        "false_positive",
        "false_negative",
        "true_positive",
        "test_samples",
        "quality_gate_passed",
    }

    assert expected_metrics.issubset(metrics)


def test_model_quality_gate_passes() -> None:
    """The baseline model must satisfy the agreed quality thresholds."""
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    assert metrics["accuracy"] >= 0.65
    assert metrics["roc_auc"] >= 0.70
    assert metrics["quality_gate_passed"] is True
