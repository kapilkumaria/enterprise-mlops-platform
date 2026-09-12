from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException

MODEL_PATH = Path("/mnt/models/model.joblib")

FEATURES = [
    "tenure_months",
    "monthly_charges",
    "total_charges",
    "senior_citizen",
    "contract_type",
    "internet_service",
    "tech_support",
    "online_security",
    "paperless_billing",
    "payment_method",
    "dependents",
]

app = FastAPI(title="KServe churn predictor")
model = None


@app.on_event("startup")
def load_model() -> None:
    global model
    model = joblib.load(MODEL_PATH)


@app.get("/v1/models/churn-model")
def model_status() -> dict[str, object]:
    return {"name": "churn-model", "ready": model is not None}


@app.post("/v1/models/churn-model:predict")
def predict(payload: dict) -> dict[str, list[int]]:
    instances = payload.get("instances")
    if not isinstance(instances, list) or not instances:
        raise HTTPException(400, "instances must be a non-empty list")

    frame = pd.DataFrame(instances)
    missing = [column for column in FEATURES if column not in frame.columns]
    if missing:
        raise HTTPException(400, f"missing features: {missing}")

    predictions = model.predict(frame[FEATURES])
    return {"predictions": [int(value) for value in predictions]}
