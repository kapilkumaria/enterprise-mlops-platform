"""Tests for the customer-churn prediction API."""

from typing import Any

from fastapi.testclient import TestClient

from src.api.main import (
    PredictionRequest,
    PredictionResponse,
    create_app,
)

VALID_PAYLOAD = {
    "tenure_months": 7,
    "monthly_charges": 92.50,
    "total_charges": 647.50,
    "contract_type": "Month-to-month",
    "internet_service": "Fiber optic",
    "tech_support": "No",
    "online_security": "No",
    "paperless_billing": "Yes",
    "payment_method": "Electronic check",
    "senior_citizen": 0,
    "dependents": "No",
}


class FakeModelService:
    """Small deterministic replacement for the MLflow model."""

    tracking_uri = "http://mlflow.test"
    model_uri = "models:/customer-churn-model@candidate"
    loaded = True

    def load(self) -> None:
        """Fake model is already loaded."""

    def predict(
        self,
        prediction_request: PredictionRequest,
    ) -> PredictionResponse:
        """Return a deterministic prediction for API testing."""
        assert prediction_request.tenure_months == 7

        return PredictionResponse(
            prediction=1,
            prediction_label="Churn",
            churn_probability=0.81,
            model_uri=self.model_uri,
        )


def create_test_client() -> TestClient:
    """Create an API client using the fake model."""
    application = create_app(FakeModelService())
    return TestClient(application)


def test_health_endpoint() -> None:
    """Health endpoint reports that the model is loaded."""
    with create_test_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "model_loaded": True,
    }


def test_model_endpoint() -> None:
    """Model endpoint reports the configured registry alias."""
    with create_test_client() as client:
        response = client.get("/model")

    assert response.status_code == 200
    assert response.json() == {
        "model_uri": "models:/customer-churn-model@candidate",
        "tracking_uri": "http://mlflow.test",
        "model_loaded": True,
    }


def test_prediction_endpoint() -> None:
    """Prediction endpoint returns a classification result."""
    with create_test_client() as client:
        response = client.post(
            "/predict",
            json=VALID_PAYLOAD,
        )

    assert response.status_code == 200
    assert response.json() == {
        "prediction": 1,
        "prediction_label": "Churn",
        "churn_probability": 0.81,
        "model_uri": "models:/customer-churn-model@candidate",
    }


def test_prediction_rejects_invalid_category() -> None:
    """Unknown categorical values fail request validation."""
    invalid_payload: dict[str, Any] = {
        **VALID_PAYLOAD,
        "contract_type": "Weekly",
    }

    with create_test_client() as client:
        response = client.post(
            "/predict",
            json=invalid_payload,
        )

    assert response.status_code == 422


def test_prediction_rejects_unknown_fields() -> None:
    """Unexpected request properties fail validation."""
    invalid_payload = {
        **VALID_PAYLOAD,
        "unknown_feature": "unexpected",
    }

    with create_test_client() as client:
        response = client.post(
            "/predict",
            json=invalid_payload,
        )

    assert response.status_code == 422
