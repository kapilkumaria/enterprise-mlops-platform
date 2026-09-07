"""Tests for MLflow experiment-tracking helpers."""

from src.training.track_experiment import (
    build_logged_parameters,
    select_metrics,
)


def test_select_metrics_returns_expected_metrics() -> None:
    """Only intended model metrics should be logged."""
    source_metrics = {
        "accuracy": 0.75,
        "precision": 0.62,
        "recall": 0.44,
        "f1_score": 0.51,
        "roc_auc": 0.77,
        "false_positive": 33,
        "quality_gate_passed": True,
    }

    selected = select_metrics(source_metrics)

    assert selected == {
        "accuracy": 0.75,
        "precision": 0.62,
        "recall": 0.44,
        "f1_score": 0.51,
        "roc_auc": 0.77,
    }


def test_logged_parameters_include_pipeline_configuration() -> None:
    """Training, preparation and evaluation settings are logged."""
    project_params = {
        "prepare": {
            "test_size": 0.2,
            "random_state": 42,
        },
        "train": {
            "regularization_strength": 1.0,
            "max_iterations": 1000,
            "random_state": 42,
        },
        "evaluate": {
            "minimum_accuracy": 0.65,
            "minimum_roc_auc": 0.70,
        },
    }

    selected = build_logged_parameters(project_params)

    assert selected["model_type"] == "logistic_regression"
    assert selected["regularization_strength"] == 1.0
    assert selected["max_iterations"] == 1000
    assert selected["test_size"] == 0.2
    assert selected["minimum_accuracy"] == 0.65
    assert selected["minimum_roc_auc"] == 0.70
