import json
import sys
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.predict import REQUIRED_FIELDS
CSV_PATH = BASE_DIR / "dataset" / "loan_data_cleaned.csv"
OUT_PATH = BASE_DIR / "ml" / "background_rows.json"


def generate_background_rows():
    df = pd.read_csv(CSV_PATH)
    sample_df = df[REQUIRED_FIELDS].sample(8, random_state=42)
    # Convert numpy types to native Python types for clean JSON
    rows = sample_df.to_dict(orient="records")
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    print(f"Generated {len(rows)} background rows at {OUT_PATH}")


if __name__ == "__main__":
    generate_background_rows()
