"""FastAPI service for customer-churn model inference."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, Literal

import mlflow
import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from src.training.train import MODEL_FEATURES

DEFAULT_TRACKING_URI = "http://127.0.0.1:5000"
DEFAULT_MODEL_URI = "models:/customer-churn-model@candidate"


class PredictionRequest(BaseModel):
    """Customer features accepted by the prediction endpoint."""

    model_config = ConfigDict(extra="forbid")

    tenure_months: int = Field(ge=0, le=120)
    monthly_charges: float = Field(gt=0, le=500)
    total_charges: float = Field(ge=0)
    contract_type: Literal[
        "Month-to-month",
        "One year",
        "Two year",
    ]
    internet_service: Literal[
        "DSL",
        "Fiber optic",
        "No internet",
    ]
    tech_support: Literal["Yes", "No"]
    online_security: Literal["Yes", "No"]
    paperless_billing: Literal["Yes", "No"]
    payment_method: Literal[
        "Bank transfer",
        "Credit card",
        "Electronic check",
        "Mailed check",
    ]
    senior_citizen: Literal[0, 1]
    dependents: Literal["Yes", "No"]

    def to_dataframe(self) -> pd.DataFrame:
        """Convert one request into the model input format."""
        row = self.model_dump()
        return pd.DataFrame([{feature: row[feature] for feature in MODEL_FEATURES}])


class PredictionResponse(BaseModel):
    """Prediction returned by the API."""

    prediction: Literal[0, 1]
    prediction_label: Literal["No churn", "Churn"]
    churn_probability: float = Field(ge=0, le=1)
    model_uri: str


class HealthResponse(BaseModel):
    """Application health information."""

    status: str
    model_loaded: bool


class ModelResponse(BaseModel):
    """Information about the currently configured model."""

    model_uri: str
    tracking_uri: str
    model_loaded: bool


class ModelService:
    """Load and invoke the candidate churn model."""

    def __init__(
        self,
        tracking_uri: str,
        model_uri: str,
    ) -> None:
        self.tracking_uri = tracking_uri
        self.model_uri = model_uri
        self.model: Any | None = None

    @property
    def loaded(self) -> bool:
        """Return whether the model has been loaded."""
        return self.model is not None

    def load(self) -> None:
        """Load the configured model from MLflow Registry."""
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_registry_uri(self.tracking_uri)
        self.model = mlflow.sklearn.load_model(self.model_uri)

    def predict(
        self,
        prediction_request: PredictionRequest,
    ) -> PredictionResponse:
        """Generate a churn prediction and probability."""
        if self.model is None:
            raise RuntimeError("Model is not loaded")

        model_input = prediction_request.to_dataframe()
        prediction = int(self.model.predict(model_input)[0])
        probabilities = self.model.predict_proba(model_input)[0]
        churn_probability = float(probabilities[1])

        return PredictionResponse(
            prediction=prediction,
            prediction_label=("Churn" if prediction == 1 else "No churn"),
            churn_probability=churn_probability,
            model_uri=self.model_uri,
        )


def create_app(
    supplied_service: ModelService | Any | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    tracking_uri = os.getenv(
        "MLFLOW_TRACKING_URI",
        DEFAULT_TRACKING_URI,
    )
    model_uri = os.getenv(
        "MODEL_URI",
        DEFAULT_MODEL_URI,
    )

    service = supplied_service or ModelService(
        tracking_uri=tracking_uri,
        model_uri=model_uri,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        if not service.loaded:
            service.load()

        application.state.model_service = service
        yield

    application = FastAPI(
        title="Customer Churn Prediction API",
        description=(
            "Serve the validated customer-churn model from MLflow Model Registry."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    @application.get(
        "/health",
        response_model=HealthResponse,
        tags=["Operations"],
    )
    def health(request: Request) -> HealthResponse:
        current_service = request.app.state.model_service

        if not current_service.loaded:
            raise HTTPException(
                status_code=503,
                detail="Model is not loaded",
            )

        return HealthResponse(
            status="healthy",
            model_loaded=True,
        )

    @application.get(
        "/model",
        response_model=ModelResponse,
        tags=["Model"],
    )
    def model_information(request: Request) -> ModelResponse:
        current_service = request.app.state.model_service

        return ModelResponse(
            model_uri=current_service.model_uri,
            tracking_uri=current_service.tracking_uri,
            model_loaded=current_service.loaded,
        )

    @application.post(
        "/predict",
        response_model=PredictionResponse,
        tags=["Inference"],
    )
    def predict(
        payload: PredictionRequest,
        request: Request,
    ) -> PredictionResponse:
        current_service = request.app.state.model_service

        try:
            return current_service.predict(payload)
        except RuntimeError as error:
            raise HTTPException(
                status_code=503,
                detail=str(error),
            ) from error

    return application


app = create_app()
