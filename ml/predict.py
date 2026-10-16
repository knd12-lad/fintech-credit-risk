"""
Prediction helper for the FinTech Credit Risk project.

Django (Phase 9) calls predict_credit_risk() with the form data and gets back
default probability, credit score (300-900) and risk level.
"""

from pathlib import Path

import joblib
import pandas as pd

from ml.preprocess import FEATURE_COLUMNS, add_features

MODEL_DIR = Path(__file__).resolve().parent / "saved_models"

# Risk level bands (score based). Change here if Step 2 table says so.
LOW_RISK_MIN_SCORE = 780        # score >= 780        -> Low
MEDIUM_RISK_MIN_SCORE = 600     # 600 <= score < 780  -> Medium, below 600 -> High

REQUIRED_FIELDS = [
    "person_age", "person_income", "person_emp_length", "loan_amnt",
    "loan_int_rate", "cb_person_cred_hist_length", "loan_grade",
    "cb_person_default_on_file", "person_home_ownership", "loan_intent",
]

_preprocessor = None
_model = None


def _load():
    """Load model files only once (first prediction), not on every request."""
    global _preprocessor, _model
    if _preprocessor is None or _model is None:
        _preprocessor = joblib.load(MODEL_DIR / "preprocessor.joblib")
        _model = joblib.load(MODEL_DIR / "credit_risk_model.joblib")
    return _preprocessor, _model


def probability_to_score(probability: float) -> int:
    """0% default -> 900, 100% default -> 300."""
    return int(round(900 - probability * 600))


def score_to_risk_level(score: int) -> str:
    if score >= LOW_RISK_MIN_SCORE:
        return "Low"
    if score >= MEDIUM_RISK_MIN_SCORE:
        return "Medium"
    return "High"


def predict_credit_risk(data: dict) -> dict:
    """
    data: dict with the 10 REQUIRED_FIELDS (same names as the dataset).
    Returns: prediction (0/1), default_probability (0-1), credit_score, risk_level.
    """
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise ValueError(f"Missing fields: {missing}")
    if float(data["person_income"]) <= 0:
        raise ValueError("person_income must be greater than 0")

    preprocessor, model = _load()

    row = pd.DataFrame([{f: data[f] for f in REQUIRED_FIELDS}])
    row = add_features(row)[FEATURE_COLUMNS]
    processed = preprocessor.transform(row)

    probability = float(model.predict_proba(processed)[0, 1])
    score = probability_to_score(probability)

    return {
        "prediction": int(probability >= 0.5),      # 1 = Default, 0 = No Default
        "default_probability": round(probability, 4),
        "credit_score": score,
        "risk_level": score_to_risk_level(score),
    }