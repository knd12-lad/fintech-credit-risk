"""
Preprocessing helpers for the FinTech Credit Risk project.

Phase 4 notebook (training) AND Django (prediction, Phase 9) both import
from this file, so the same logic is used everywhere.
"""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

# ---------------------------------------------------------------------
# Column groups
# ---------------------------------------------------------------------
TARGET = "loan_status"          # 0 = No Default, 1 = Default

GRADE_ORDER = ["A", "B", "C", "D", "E", "F", "G"]   # A = best, G = worst
YES_NO_ORDER = ["N", "Y"]

NUMERIC_FEATURES = [
    "person_age",
    "person_income",
    "person_emp_length",
    "loan_amnt",
    "loan_int_rate",
    "cb_person_cred_hist_length",
    "loan_to_income",          # engineered
    "interest_to_income",      # engineered
]
ORDINAL_FEATURES = ["loan_grade", "cb_person_default_on_file"]
NOMINAL_FEATURES = ["person_home_ownership", "loan_intent"]

FEATURE_COLUMNS = NUMERIC_FEATURES + ORDINAL_FEATURES + NOMINAL_FEATURES


# ---------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add engineered columns. Needs person_income > 0."""
    df = df.copy()
    # Loan-to-Income: how big is the loan compared to yearly income
    df["loan_to_income"] = df["loan_amnt"] / df["person_income"]
    # Interest-to-Income: yearly interest cost compared to yearly income
    df["interest_to_income"] = (
        df["loan_amnt"] * df["loan_int_rate"] / 100
    ) / df["person_income"]
    return df


# ---------------------------------------------------------------------
# Encoding + scaling
# ---------------------------------------------------------------------
def build_preprocessor() -> ColumnTransformer:
    """Unfitted preprocessor: scale numbers, encode categories."""
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            (
                "ord",
                OrdinalEncoder(categories=[GRADE_ORDER, YES_NO_ORDER]),
                ORDINAL_FEATURES,
            ),
            (
                "nom",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                NOMINAL_FEATURES,
            ),
        ]
    )
    # keep column names (returns a DataFrame instead of a numpy array)
    preprocessor.set_output(transform="pandas")
    return preprocessor