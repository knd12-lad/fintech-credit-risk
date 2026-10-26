import json
import logging
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ml.predict import REQUIRED_FIELDS, _load, probability_to_score
from ml.preprocess import FEATURE_COLUMNS, add_features

logger = logging.getLogger(__name__)

BACKGROUND_JSON_PATH = Path(__file__).resolve().parent / "background_rows.json"

FIELD_LABELS = {
    "person_income": "Annual income",
    "loan_amnt": "Loan amount",
    "loan_int_rate": "Interest rate",
    "loan_grade": "Loan grade",
    "loan_intent": "Loan purpose",
    "person_home_ownership": "Home ownership",
    "person_age": "Age",
    "person_emp_length": "Employment length (years)",
    "cb_person_cred_hist_length": "Credit history (years)",
    "cb_person_default_on_file": "Previous default on record",
}

# Precompute coalition constants once
N_FEATURES = len(REQUIRED_FIELDS)  # 10
MASKS = np.arange(1024, dtype=np.int32)
BITS = [((MASKS & (1 << j)) != 0) for j in range(N_FEATURES)]

# Shapley weights W(k) = k!(n-k-1)! / n!
W = np.zeros(N_FEATURES + 1, dtype=np.float64)
for k in range(N_FEATURES):
    W[k] = math.factorial(k) * math.factorial(N_FEATURES - k - 1) / math.factorial(N_FEATURES)
POPCOUNTS = np.array([bin(m).count("1") for m in range(1024)], dtype=np.int32)
WEIGHTS_PER_MASK = W[POPCOUNTS]

FEATURE_CONSTANTS = []
for i in range(N_FEATURES):
    has_not_i = (MASKS & (1 << i)) == 0
    with_i = MASKS[has_not_i] | (1 << i)
    without_i = MASKS[has_not_i]
    weights_i = WEIGHTS_PER_MASK[has_not_i]
    FEATURE_CONSTANTS.append((with_i, without_i, weights_i))

_background_rows = None


def _get_background_rows():
    """Load the 8 background rows from JSON (cached)."""
    global _background_rows
    if _background_rows is None:
        with open(BACKGROUND_JSON_PATH, "r", encoding="utf-8") as f:
            _background_rows = json.load(f)
    return _background_rows


def format_display_value(field: str, val) -> str:
    """Format an applicant's raw field value for user display."""
    if field in ("person_income", "loan_amnt"):
        try:
            return f"${int(round(float(val))):,}"
        except (ValueError, TypeError):
            return f"${val}"
    if field == "loan_int_rate":
        try:
            return f"{float(val):.1f}%"
        except (ValueError, TypeError):
            return f"{val}%"
    if field == "cb_person_default_on_file":
        s = str(val).strip().upper()
        return "Yes" if s in ("Y", "YES", "1", "TRUE") else "No"
    if field == "loan_intent":
        intent_map = {
            "DEBTCONSOLIDATION": "Debt Consolidation",
            "MEDICAL": "Medical",
            "HOMEIMPROVEMENT": "Home Improvement",
            "PERSONAL": "Personal",
            "EDUCATION": "Education",
            "VENTURE": "Venture",
        }
        return intent_map.get(str(val).upper(), str(val).title())
    if field == "person_home_ownership":
        return str(val).title()
    if field in ("person_age", "cb_person_cred_hist_length"):
        try:
            return str(int(round(float(val))))
        except (ValueError, TypeError):
            return str(val)
    if field == "person_emp_length":
        try:
            fval = float(val)
            return str(int(fval)) if fval.is_integer() else f"{fval:.1f}"
        except (ValueError, TypeError):
            return str(val)
    if field == "loan_grade":
        return str(val).upper()
    return str(val)


def explain_prediction(data: dict, top_n: int = 4) -> dict:
    """
    Computes exact Shapley values for an applicant's prediction against 8 background rows.
    Returns impact points, factors, and summary metrics.
    """
    start_time = time.time()

    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise ValueError(f"Missing required fields for explanation: {missing}")

    preprocessor, model = _load()
    background_rows = _get_background_rows()

    # Build and evaluate 2^n coalitions for each background row
    v_total = np.zeros(1024, dtype=np.float64)
    for ref in background_rows:
        cols = {
            field: np.where(BITS[j], data[field], ref[field])
            for j, field in enumerate(REQUIRED_FIELDS)
        }
        df_coalition = pd.DataFrame(cols)
        df_features = add_features(df_coalition)[FEATURE_COLUMNS]
        X_trans = preprocessor.transform(df_features)
        v_total += model.predict_proba(X_trans)[:, 1]

    n_ref = len(background_rows)
    v = v_total / n_ref

    baseline_prob = round(float(v[0]), 8)
    applicant_prob = round(float(v[1023]), 8)
    baseline_score = probability_to_score(baseline_prob)
    applicant_score = probability_to_score(applicant_prob)

    # Compute exact Shapley values
    phi = {}
    factors_all = []
    for i, field in enumerate(REQUIRED_FIELDS):
        with_i, without_i, weights_i = FEATURE_CONSTANTS[i]
        val = round(float(np.dot(weights_i, v[with_i] - v[without_i])), 8)
        phi[field] = val

        impact_pts = int(round(-val * 600))
        direction = "helps" if impact_pts >= 0 else "hurts"
        verb = "raised" if impact_pts >= 0 else "lowered"
        label = FIELD_LABELS.get(field, field)
        disp_val = format_display_value(field, data[field])
        pts_abs = abs(impact_pts)

        sentence = (
            f"{label} of {disp_val} {verb} your score by about "
            f"{pts_abs} points compared with the average applicant."
        )

        factors_all.append({
            "field": field,
            "label": label,
            "display_value": disp_val,
            "impact_points": impact_pts,
            "abs_points": pts_abs,
            "direction": direction,
            "sentence": sentence,
            "_abs_val": abs(val),
        })

    # Sort factors by absolute impact descending
    factors_all.sort(key=lambda item: item["_abs_val"], reverse=True)

    # Determine max impact for visual bar proportion
    max_impact = max(f["abs_points"] for f in factors_all) if factors_all else 1
    if max_impact == 0:
        max_impact = 1

    for f in factors_all:
        f["bar_pct"] = max(4, int(round((f["abs_points"] / max_impact) * 100)))
        del f["_abs_val"]

    top_factors = factors_all[:top_n]
    remaining = factors_all[top_n:]
    other_points = sum(f["impact_points"] for f in remaining)

    elapsed = time.time() - start_time
    if elapsed > 1.0:
        logger.warning(f"explain_prediction took {elapsed:.2f}s (> 1.0s limit)")

    return {
        "baseline_probability": baseline_prob,
        "applicant_probability": applicant_prob,
        "baseline_score": baseline_score,
        "applicant_score": applicant_score,
        "factors": top_factors,
        "other_points": other_points,
        "max_impact": max_impact,
        "shapley_values": phi,
        "_phi": phi,  # internal access for test verification
    }
