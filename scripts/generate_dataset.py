"""Generate a deterministic synthetic customer-churn dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_ROWS = 2000
DEFAULT_SEED = 42
DEFAULT_OUTPUT = Path("data/raw/customer_churn.csv")


def sigmoid(values: np.ndarray) -> np.ndarray:
    """Convert model scores into probabilities."""
    return 1.0 / (1.0 + np.exp(-values))


def generate_dataset(rows: int, seed: int) -> pd.DataFrame:
    """Create a synthetic customer-churn dataset."""
    if rows < 100:
        raise ValueError("rows must be at least 100")

    rng = np.random.default_rng(seed)

    tenure_months = rng.integers(1, 73, size=rows)
    monthly_charges = np.round(rng.uniform(20.0, 120.0, size=rows), 2)

    contract_type = rng.choice(
        ["Month-to-month", "One year", "Two year"],
        size=rows,
        p=[0.55, 0.25, 0.20],
    )

    internet_service = rng.choice(
        ["DSL", "Fiber optic", "No internet"],
        size=rows,
        p=[0.35, 0.50, 0.15],
    )

    tech_support = rng.choice(
        ["Yes", "No"],
        size=rows,
        p=[0.42, 0.58],
    )

    online_security = rng.choice(
        ["Yes", "No"],
        size=rows,
        p=[0.45, 0.55],
    )

    paperless_billing = rng.choice(
        ["Yes", "No"],
        size=rows,
        p=[0.62, 0.38],
    )

    payment_method = rng.choice(
        [
            "Electronic check",
            "Mailed check",
            "Bank transfer",
            "Credit card",
        ],
        size=rows,
        p=[0.35, 0.20, 0.23, 0.22],
    )

    senior_citizen = rng.choice(
        [0, 1],
        size=rows,
        p=[0.82, 0.18],
    )

    dependents = rng.choice(
        ["Yes", "No"],
        size=rows,
        p=[0.35, 0.65],
    )

    total_charges = np.round(
        monthly_charges * tenure_months * rng.normal(loc=1.0, scale=0.03, size=rows),
        2,
    )

    # Create understandable churn relationships:
    # shorter tenure, month-to-month contracts, higher charges,
    # fiber service and missing support increase churn probability.
    churn_score = (
        -1.50
        - (0.025 * tenure_months)
        + (0.012 * (monthly_charges - 70.0))
        + (1.20 * (contract_type == "Month-to-month"))
        - (0.45 * (contract_type == "One year"))
        - (1.00 * (contract_type == "Two year"))
        + (0.45 * (internet_service == "Fiber optic"))
        + (0.45 * (tech_support == "No"))
        + (0.35 * (online_security == "No"))
        + (0.25 * (paperless_billing == "Yes"))
        + (0.30 * (payment_method == "Electronic check"))
        + (0.30 * senior_citizen)
        - (0.30 * (dependents == "Yes"))
    )

    churn_probability = sigmoid(churn_score)
    churn = rng.binomial(1, churn_probability)

    return pd.DataFrame(
        {
            "customer_id": [f"CUST-{number:05d}" for number in range(1, rows + 1)],
            "tenure_months": tenure_months,
            "monthly_charges": monthly_charges,
            "total_charges": total_charges,
            "contract_type": contract_type,
            "internet_service": internet_service,
            "tech_support": tech_support,
            "online_security": online_security,
            "paperless_billing": paperless_billing,
            "payment_method": payment_method,
            "senior_citizen": senior_citizen,
            "dependents": dependents,
            "churn": churn,
        }
    )


def validate_dataset(dataset: pd.DataFrame, expected_rows: int) -> None:
    """Validate the generated dataset before saving it."""
    required_columns = {
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

    if len(dataset) != expected_rows:
        raise ValueError("generated row count does not match requested row count")

    if set(dataset.columns) != required_columns:
        raise ValueError("generated dataset columns are invalid")

    if dataset.isna().any().any():
        raise ValueError("generated dataset contains missing values")

    if not dataset["customer_id"].is_unique:
        raise ValueError("customer_id contains duplicates")

    if not set(dataset["churn"].unique()).issubset({0, 1}):
        raise ValueError("churn must contain only 0 and 1")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a synthetic customer-churn dataset."
    )

    parser.add_argument(
        "--rows",
        type=int,
        default=DEFAULT_ROWS,
        help=f"Number of customers to generate (default: {DEFAULT_ROWS}).",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed (default: {DEFAULT_SEED}).",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT}).",
    )

    return parser.parse_args()


def main() -> None:
    """Generate, validate and save the dataset."""
    arguments = parse_arguments()

    dataset = generate_dataset(
        rows=arguments.rows,
        seed=arguments.seed,
    )

    validate_dataset(
        dataset=dataset,
        expected_rows=arguments.rows,
    )

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(arguments.output, index=False)

    print(f"Dataset written to: {arguments.output}")
    print(f"Rows:               {len(dataset)}")
    print(f"Columns:            {len(dataset.columns)}")
    print(f"Missing values:     {int(dataset.isna().sum().sum())}")
    print(f"Duplicate IDs:      {int(dataset['customer_id'].duplicated().sum())}")
    print(f"Churned customers:  {int(dataset['churn'].sum())}")
    print(f"Churn rate:         {dataset['churn'].mean():.2%}")


if __name__ == "__main__":
    main()
