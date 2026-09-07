"""Tests for deterministic train/test data preparation."""

from pathlib import Path

import pandas as pd

RAW_PATH = Path("data/raw/customer_churn.csv")
TRAIN_PATH = Path("data/processed/train.csv")
TEST_PATH = Path("data/processed/test.csv")

EXPECTED_RAW_ROWS = 2000
EXPECTED_TRAIN_ROWS = 1600
EXPECTED_TEST_ROWS = 400


def load_datasets() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load raw, training and testing datasets."""
    assert RAW_PATH.is_file()
    assert TRAIN_PATH.is_file()
    assert TEST_PATH.is_file()

    return (
        pd.read_csv(RAW_PATH),
        pd.read_csv(TRAIN_PATH),
        pd.read_csv(TEST_PATH),
    )


def test_prepared_dataset_sizes() -> None:
    """Prepared datasets must have the expected sizes."""
    raw_data, train_data, test_data = load_datasets()

    assert len(raw_data) == EXPECTED_RAW_ROWS
    assert len(train_data) == EXPECTED_TRAIN_ROWS
    assert len(test_data) == EXPECTED_TEST_ROWS
    assert len(train_data) + len(test_data) == len(raw_data)


def test_prepared_schemas_match_source() -> None:
    """Training and testing schemas must match the raw schema."""
    raw_data, train_data, test_data = load_datasets()

    assert list(train_data.columns) == list(raw_data.columns)
    assert list(test_data.columns) == list(raw_data.columns)


def test_prepared_datasets_have_no_missing_values() -> None:
    """Prepared datasets must not contain missing values."""
    _, train_data, test_data = load_datasets()

    assert int(train_data.isna().sum().sum()) == 0
    assert int(test_data.isna().sum().sum()) == 0


def test_prepared_customer_ids_are_isolated() -> None:
    """A customer must not appear in both datasets."""
    _, train_data, test_data = load_datasets()

    train_ids = set(train_data["customer_id"])
    test_ids = set(test_data["customer_id"])

    assert train_ids.isdisjoint(test_ids)


def test_all_source_customers_are_preserved() -> None:
    """The split must preserve every source customer exactly once."""
    raw_data, train_data, test_data = load_datasets()

    source_ids = set(raw_data["customer_id"])
    prepared_ids = set(train_data["customer_id"]) | set(test_data["customer_id"])

    assert prepared_ids == source_ids


def test_target_classes_are_preserved() -> None:
    """Both datasets must contain churn and non-churn records."""
    _, train_data, test_data = load_datasets()

    assert set(train_data["churn"].unique()) == {0, 1}
    assert set(test_data["churn"].unique()) == {0, 1}


def test_stratified_churn_rates_are_consistent() -> None:
    """Training and testing churn rates should remain closely aligned."""
    raw_data, train_data, test_data = load_datasets()

    raw_rate = raw_data["churn"].mean()
    train_rate = train_data["churn"].mean()
    test_rate = test_data["churn"].mean()

    assert abs(train_rate - raw_rate) < 0.01
    assert abs(test_rate - raw_rate) < 0.01
