"""Tests for MLflow Model Registry helpers."""

from types import SimpleNamespace

import pytest

from src.training.register_model import (
    build_run_model_uri,
    run_passed_quality_gate,
)


def create_run(
    status: str = "FINISHED",
    quality_gate: str = "true",
    accuracy: float = 0.745,
    roc_auc: float = 0.772,
) -> SimpleNamespace:
    """Create a minimal MLflow-like run for unit testing."""
    return SimpleNamespace(
        info=SimpleNamespace(status=status),
        data=SimpleNamespace(
            tags={"quality_gate_passed": quality_gate},
            metrics={
                "accuracy": accuracy,
                "roc_auc": roc_auc,
            },
            params={
                "minimum_accuracy": "0.65",
                "minimum_roc_auc": "0.70",
            },
        ),
    )


def test_build_run_model_uri() -> None:
    """Model URI contains the source run and model name."""
    assert build_run_model_uri("abc123") == "runs:/abc123/model"


def test_build_run_model_uri_rejects_empty_id() -> None:
    """An empty run ID cannot produce a valid model URI."""
    with pytest.raises(ValueError, match="must not be empty"):
        build_run_model_uri("")


def test_validated_run_is_eligible() -> None:
    """A finished run passing both thresholds is eligible."""
    assert run_passed_quality_gate(create_run()) is True


def test_failed_quality_tag_is_not_eligible() -> None:
    """A run rejected by its quality gate is not eligible."""
    run = create_run(quality_gate="false")

    assert run_passed_quality_gate(run) is False


def test_low_roc_auc_is_not_eligible() -> None:
    """A run below the ROC-AUC threshold is not eligible."""
    run = create_run(roc_auc=0.60)

    assert run_passed_quality_gate(run) is False


def test_unfinished_run_is_not_eligible() -> None:
    """An unfinished run cannot be registered."""
    run = create_run(status="RUNNING")

    assert run_passed_quality_gate(run) is False
