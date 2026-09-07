"""Tests for the generated customer-churn dataset."""

from pathlib import Path

import pandas as pd

DATASET_PATH = Path("data/raw/customer_churn.csv")
EXPECTED_ROWS = 2000

EXPECTED_COLUMNS = {
    "customer_id",
    "tenure_months",
    "monthly_charges",
    "total_charges",
    "contract_type",
    "internet_service",
    "tech_support",
    "online_security",
    "paperless_billing",
    "payment_method",
    "senior_citizen",
    "dependents",
    "churn",
}


def load_dataset() -> pd.DataFrame:
    """Load the generated dataset."""
    assert DATASET_PATH.is_file(), f"Dataset does not exist: {DATASET_PATH}"
    return pd.read_csv(DATASET_PATH)


def test_dataset_shape_and_columns() -> None:
    """Dataset must have the expected size and schema."""
    dataset = load_dataset()

    assert len(dataset) == EXPECTED_ROWS
    assert set(dataset.columns) == EXPECTED_COLUMNS


def test_dataset_has_no_missing_values() -> None:
    """Dataset must not contain missing values."""
    dataset = load_dataset()

    assert int(dataset.isna().sum().sum()) == 0


def test_customer_ids_are_unique() -> None:
    """Each synthetic customer must have a unique identifier."""
    dataset = load_dataset()

    assert dataset["customer_id"].is_unique


def test_binary_columns_are_valid() -> None:
    """Binary columns must contain only expected values."""
    dataset = load_dataset()

    assert set(dataset["churn"].unique()).issubset({0, 1})
    assert set(dataset["senior_citizen"].unique()).issubset({0, 1})


def test_numeric_values_are_valid() -> None:
    """Numeric customer attributes must be in valid ranges."""
    dataset = load_dataset()

    assert dataset["tenure_months"].between(1, 72).all()
    assert dataset["monthly_charges"].between(20.0, 120.0).all()
    assert dataset["total_charges"].gt(0).all()


def test_churn_distribution_is_reasonable() -> None:
    """Both target classes must be sufficiently represented."""
    dataset = load_dataset()
    churn_rate = dataset["churn"].mean()

    assert 0.15 <= churn_rate <= 0.60
