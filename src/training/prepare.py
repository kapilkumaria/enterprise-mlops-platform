"""Prepare deterministic training and testing datasets."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

DEFAULT_INPUT = Path("data/raw/customer_churn.csv")
DEFAULT_TRAIN_OUTPUT = Path("data/processed/train.csv")
DEFAULT_TEST_OUTPUT = Path("data/processed/test.csv")
DEFAULT_TEST_SIZE = 0.20
DEFAULT_RANDOM_STATE = 42

TARGET_COLUMN = "churn"
IDENTIFIER_COLUMN = "customer_id"


def load_and_validate_dataset(input_path: Path) -> pd.DataFrame:
    """Load and validate the raw customer-churn dataset."""
    if not input_path.is_file():
        raise FileNotFoundError(f"Dataset does not exist: {input_path}")

    dataset = pd.read_csv(input_path)

    if dataset.empty:
        raise ValueError("Dataset is empty")

    if TARGET_COLUMN not in dataset.columns:
        raise ValueError(f"Missing target column: {TARGET_COLUMN}")

    if IDENTIFIER_COLUMN not in dataset.columns:
        raise ValueError(f"Missing identifier column: {IDENTIFIER_COLUMN}")

    if dataset.isna().any().any():
        raise ValueError("Dataset contains missing values")

    if not dataset[IDENTIFIER_COLUMN].is_unique:
        raise ValueError("Dataset contains duplicate customer IDs")

    if not set(dataset[TARGET_COLUMN].unique()).issubset({0, 1}):
        raise ValueError("Target column must contain only 0 and 1")

    if dataset[TARGET_COLUMN].nunique() != 2:
        raise ValueError("Dataset must contain both target classes")

    return dataset


def split_dataset(
    dataset: pd.DataFrame,
    test_size: float,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split data while preserving the target-class distribution."""
    if not 0.10 <= test_size <= 0.50:
        raise ValueError("test_size must be between 0.10 and 0.50")

    train_data, test_data = train_test_split(
        dataset,
        test_size=test_size,
        random_state=random_state,
        stratify=dataset[TARGET_COLUMN],
    )

    train_data = train_data.sort_values(IDENTIFIER_COLUMN).reset_index(drop=True)
    test_data = test_data.sort_values(IDENTIFIER_COLUMN).reset_index(drop=True)

    return train_data, test_data


def validate_split(
    source_data: pd.DataFrame,
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
) -> None:
    """Validate completeness and isolation of the resulting datasets."""
    train_ids = set(train_data[IDENTIFIER_COLUMN])
    test_ids = set(test_data[IDENTIFIER_COLUMN])

    if train_ids & test_ids:
        raise ValueError("Training and testing datasets overlap")

    if len(train_data) + len(test_data) != len(source_data):
        raise ValueError("Split datasets do not preserve the source row count")

    if train_data.isna().any().any() or test_data.isna().any().any():
        raise ValueError("Split datasets contain missing values")

    if train_data[TARGET_COLUMN].nunique() != 2:
        raise ValueError("Training dataset does not contain both target classes")

    if test_data[TARGET_COLUMN].nunique() != 2:
        raise ValueError("Testing dataset does not contain both target classes")


def write_dataset(dataset: pd.DataFrame, output_path: Path) -> None:
    """Write a prepared dataset to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(output_path, index=False)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Prepare customer-churn train and test datasets."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )

    parser.add_argument(
        "--train-output",
        type=Path,
        default=DEFAULT_TRAIN_OUTPUT,
    )

    parser.add_argument(
        "--test-output",
        type=Path,
        default=DEFAULT_TEST_OUTPUT,
    )

    parser.add_argument(
        "--test-size",
        type=float,
        default=DEFAULT_TEST_SIZE,
    )

    parser.add_argument(
        "--random-state",
        type=int,
        default=DEFAULT_RANDOM_STATE,
    )

    return parser.parse_args()


def main() -> None:
    """Prepare and save deterministic training and testing datasets."""
    arguments = parse_arguments()

    source_data = load_and_validate_dataset(arguments.input)

    train_data, test_data = split_dataset(
        dataset=source_data,
        test_size=arguments.test_size,
        random_state=arguments.random_state,
    )

    validate_split(
        source_data=source_data,
        train_data=train_data,
        test_data=test_data,
    )

    write_dataset(train_data, arguments.train_output)
    write_dataset(test_data, arguments.test_output)

    print(f"Source rows:        {len(source_data)}")
    print(f"Training rows:      {len(train_data)}")
    print(f"Testing rows:       {len(test_data)}")
    print(f"Source churn rate:  {source_data[TARGET_COLUMN].mean():.2%}")
    print(f"Training churn rate:{train_data[TARGET_COLUMN].mean():.2%}")
    print(f"Testing churn rate: {test_data[TARGET_COLUMN].mean():.2%}")
    print(f"Training output:    {arguments.train_output}")
    print(f"Testing output:     {arguments.test_output}")


if __name__ == "__main__":
    main()
