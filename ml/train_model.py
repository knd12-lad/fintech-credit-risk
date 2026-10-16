"""
Model helpers for the FinTech Credit Risk project.

Phase 5 (notebook 04) uses these to train + compare models.
Phase 6 uses the same functions to save the final model.
"""

from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.tree import DecisionTreeClassifier

BASE_DIR = Path(__file__).resolve().parent.parent      # project root
DATASET_DIR = BASE_DIR / "dataset"
MODEL_DIR = BASE_DIR / "ml" / "saved_models"

TARGET = "loan_status"
RANDOM_STATE = 42


def load_train_test():
    """Load the processed files made in Phase 4."""
    train = pd.read_csv(DATASET_DIR / "train_processed.csv")
    test = pd.read_csv(DATASET_DIR / "test_processed.csv")
    X_train, y_train = train.drop(columns=TARGET), train[TARGET]
    X_test, y_test = test.drop(columns=TARGET), test[TARGET]
    return X_train, X_test, y_train, y_test


def get_models():
    """Three models to compare (fresh, unfitted copies every call)."""
    return {
        "Logistic Regression": LogisticRegression(
            max_iter=1000, random_state=RANDOM_STATE
        ),
        "Decision Tree": DecisionTreeClassifier(
            max_depth=6, min_samples_leaf=20, random_state=RANDOM_STATE
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_leaf=5,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }


def evaluate_model(model, X, y, threshold=0.5):
    """Return Accuracy, Precision, Recall, F1, ROC-AUC for a fitted model."""
    proba = model.predict_proba(X)[:, 1]            # probability of Default
    pred = (proba >= threshold).astype(int)
    return {
        "Accuracy": accuracy_score(y, pred),
        "Precision": precision_score(y, pred, zero_division=0),
        "Recall": recall_score(y, pred),
        "F1": f1_score(y, pred),
        "ROC-AUC": roc_auc_score(y, proba),
    }