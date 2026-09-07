"""Train a customer-churn classification model."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DEFAULT_TRAIN_INPUT = Path("data/processed/train.csv")
DEFAULT_MODEL_OUTPUT = Path("models/churn_model.joblib")

TARGET_COLUMN = "churn"
IDENTIFIER_COLUMN = "customer_id"

NUMERIC_FEATURES = [
    "tenure_months",
    "monthly_charges",
    "total_charges",
    "senior_citizen",
]

CATEGORICAL_FEATURES = [
    "contract_type",
    "internet_service",
    "tech_support",
    "online_security",
    "paperless_billing",
    "payment_method",
    "dependents",
]

MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def load_training_data(input_path: Path) -> tuple[pd.DataFrame, pd.Series]:
    """Load and validate training features and labels."""
    if not input_path.is_file():
        raise FileNotFoundError(f"Training dataset does not exist: {input_path}")

    dataset = pd.read_csv(input_path)

    required_columns = set(MODEL_FEATURES + [TARGET_COLUMN, IDENTIFIER_COLUMN])
    missing_columns = required_columns - set(dataset.columns)

    if missing_columns:
        raise ValueError(
            "Training dataset is missing columns: " + ", ".join(sorted(missing_columns))
        )

    if dataset.isna().any().any():
        raise ValueError("Training dataset contains missing values")

    if not set(dataset[TARGET_COLUMN].unique()).issubset({0, 1}):
        raise ValueError("Training target must contain only 0 and 1")

    features = dataset[MODEL_FEATURES]
    target = dataset[TARGET_COLUMN]

    return features, target


def build_model(
    regularization_strength: float,
    max_iterations: int,
    random_state: int,
) -> Pipeline:
    """Build the preprocessing and classification pipeline."""
    if regularization_strength <= 0:
        raise ValueError("regularization_strength must be greater than zero")

    if max_iterations < 100:
        raise ValueError("max_iterations must be at least 100")

    numeric_transformer = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            (
                "one_hot_encoder",
                OneHotEncoder(handle_unknown="ignore"),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_transformer,
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                categorical_transformer,
                CATEGORICAL_FEATURES,
            ),
        ]
    )

    classifier = LogisticRegression(
        C=regularization_strength,
        max_iter=max_iterations,
        random_state=random_state,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )


def save_model(model: Pipeline, output_path: Path) -> None:
    """Serialize the complete preprocessing and model pipeline."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_path)


def parse_arguments() -> argparse.Namespace:
    """Parse training arguments."""
    parser = argparse.ArgumentParser(description="Train the customer-churn model.")

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_TRAIN_INPUT,
    )

    parser.add_argument(
        "--model-output",
        type=Path,
        default=DEFAULT_MODEL_OUTPUT,
    )

    parser.add_argument(
        "--regularization-strength",
        type=float,
        default=1.0,
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=1000,
    )

    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
    )

    return parser.parse_args()


def main() -> None:
    """Train and save the customer-churn model."""
    arguments = parse_arguments()

    features, target = load_training_data(arguments.input)

    model = build_model(
        regularization_strength=arguments.regularization_strength,
        max_iterations=arguments.max_iterations,
        random_state=arguments.random_state,
    )

    model.fit(features, target)
    save_model(model, arguments.model_output)

    training_accuracy = model.score(features, target)

    print(f"Training rows:       {len(features)}")
    print(f"Numeric features:    {len(NUMERIC_FEATURES)}")
    print(f"Categorical features:{len(CATEGORICAL_FEATURES)}")
    print(f"Training accuracy:   {training_accuracy:.4f}")
    print(f"Model output:        {arguments.model_output}")


if __name__ == "__main__":
    main()
