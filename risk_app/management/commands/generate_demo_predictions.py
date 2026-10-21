"""
Django Management Command: generate_demo_predictions
Generates ~200 clearly identified, synthetic demo prediction records
using real sample rows from dataset/loan_data_cleaned.csv and the actual
ML prediction pipeline (predict_credit_risk).

Strict Safety Guarantees:
- Never exposes or uses real PII. All applicants are named 'Demo Applicant #001' ...
- Linked exclusively to a dedicated synthetic user: demo_portfolio@riskwise.internal
- Fully idempotent: checks existing records and prevents duplicate insertion.
- Supports --preview to inspect generated distributions before committing to MySQL.
- Atomic transaction: rolls back completely on any unexpected error.
"""

from decimal import Decimal
from pathlib import Path
import pandas as pd

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from django.conf import settings

from risk_app.models import LoanType, LoanApplication, Prediction
from ml.predict import predict_credit_risk

User = get_user_model()


class Command(BaseCommand):
    help = "Generate ~200 synthetic demo predictions for Power BI reporting and demo verification."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Number of demo records to generate (default: 200)",
        )
        parser.add_argument(
            "--preview",
            action="store_true",
            help="Preview the data generation and predictions without writing to the database.",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Execute database insertion inside an atomic transaction.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        preview = options["preview"]
        execute = options["execute"]

        if not preview and not execute:
            self.stdout.write(
                self.style.WARNING(
                    "Please specify either --preview (to test logic) or --execute (to write records)."
                )
            )
            return

        dataset_path = Path(settings.BASE_DIR) / "dataset" / "loan_data_cleaned.csv"
        if not dataset_path.exists():
            self.stderr.write(self.style.ERROR(f"Dataset not found at {dataset_path}"))
            return

        self.stdout.write(f"Reading source dataset from: {dataset_path}")
        df = pd.read_csv(dataset_path)

        # Ensure active loan types exist in database
        loan_types = {lt.code: lt for lt in LoanType.objects.filter(is_active=True)}
        if not loan_types:
            self.stderr.write(
                self.style.ERROR(
                    "No active LoanTypes found in the database. Please run seed_initial_data first."
                )
            )
            return

        # Filter valid rows: must have valid loan_intent in loan_types
        valid_mask = df["loan_intent"].isin(loan_types.keys())
        df_valid = df[valid_mask].copy()

        # Select a stratified/representative sample of ~limit rows
        # We take a deterministic head slice of `limit` rows for reproducibility
        sample_df = df_valid.head(limit)

        inspected_count = len(df)
        selected_count = len(sample_df)
        rejected_count = 0
        predictions_generated = 0
        inserted_count = 0
        skipped_duplicates = 0

        self.stdout.write(f"Source rows inspected: {inspected_count}")
        self.stdout.write(f"Targeting {selected_count} clean rows for demo generation...")

        # Find or prepare demo user
        demo_email = "demo_portfolio@riskwise.internal"

        # Pre-check existing demo applications to support idempotency
        existing_demo_names = set(
            LoanApplication.objects.filter(
                full_name__startswith="Demo Applicant #"
            ).values_list("full_name", flat=True)
        )

        preview_records = []
        records_to_insert = []

        risk_distribution = {"Low": 0, "Medium": 0, "High": 0}
        total_scores = []
        total_probs = []

        for idx, row in sample_df.iterrows():
            demo_identifier = f"Demo Applicant #{idx + 1:03d}"

            if demo_identifier in existing_demo_names:
                skipped_duplicates += 1
                continue

            # Prepare data payload for predict_credit_risk
            try:
                feature_dict = {
                    "person_age": int(row["person_age"]),
                    "person_income": float(row["person_income"]),
                    "person_emp_length": float(row["person_emp_length"]),
                    "loan_amnt": float(row["loan_amnt"]),
                    "loan_int_rate": float(row["loan_int_rate"]),
                    "cb_person_cred_hist_length": int(row["cb_person_cred_hist_length"]),
                    "loan_grade": str(row["loan_grade"]),
                    "cb_person_default_on_file": str(row["cb_person_default_on_file"]),
                    "person_home_ownership": str(row["person_home_ownership"]),
                    "loan_intent": str(row["loan_intent"]),
                }

                # Run through the real ML pipeline
                ml_result = predict_credit_risk(feature_dict)
                predictions_generated += 1

                risk_distribution[ml_result["risk_level"]] += 1
                total_scores.append(ml_result["credit_score"])
                total_probs.append(ml_result["default_probability"])

                record_bundle = {
                    "identifier": demo_identifier,
                    "features": feature_dict,
                    "prediction": ml_result,
                    "loan_type": loan_types[feature_dict["loan_intent"]],
                    "observed_status": int(row.get("loan_status", 0)),
                }

                if preview:
                    preview_records.append(record_bundle)
                else:
                    records_to_insert.append(record_bundle)

            except Exception as e:
                rejected_count += 1
                self.stdout.write(self.style.WARNING(f"Row {idx} skipped: {str(e)}"))

        # Summary of calculations
        avg_score = round(sum(total_scores) / len(total_scores), 1) if total_scores else 0
        avg_prob = (
            round((sum(total_probs) / len(total_probs)) * 100, 2) if total_probs else 0
        )

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("DEMO PREDICTION PIPELINE SUMMARY")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Source Rows Inspected:    {inspected_count}")
        self.stdout.write(f"Rows Target Batch:        {selected_count}")
        self.stdout.write(f"Existing Duplicates:      {skipped_duplicates}")
        self.stdout.write(f"Rows Rejected/Error:      {rejected_count}")
        self.stdout.write(f"Predictions Computed:     {predictions_generated}")
        self.stdout.write(f"Risk Distribution:        {risk_distribution}")
        self.stdout.write(f"Average Credit Score:     {avg_score} (Scale 300-900)")
        self.stdout.write(f"Average Default Prob:     {avg_prob}%")
        self.stdout.write("=" * 60)

        if preview:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n[PREVIEW MODE] {predictions_generated} records generated in-memory. 0 database changes made."
                )
            )
            self.stdout.write(
                "Run with --execute to commit these records into MySQL database."
            )
            return

        if execute:
            if not records_to_insert:
                self.stdout.write(
                    self.style.WARNING(
                        "No new records to insert. All target rows are already present in the database."
                    )
                )
                return

            self.stdout.write(
                f"\nCommitting {len(records_to_insert)} records to MySQL inside atomic transaction..."
            )

            try:
                with transaction.atomic():
                    # 1. Ensure the demo user exists
                    demo_user, _ = User.objects.get_or_create(
                        email=demo_email,
                        defaults={
                            "full_name": "Demo Portfolio Account",
                            "role": "USER",
                            "is_active": True,
                        },
                    )

                    # 2. Insert LoanApplications and Predictions
                    for bundle in records_to_insert:
                        f = bundle["features"]
                        p = bundle["prediction"]

                        app = LoanApplication.objects.create(
                            user=demo_user,
                            loan_type=bundle["loan_type"],
                            full_name=bundle["identifier"],
                            age=f["person_age"],
                            annual_income=Decimal(str(f["person_income"])),
                            employment_length=f["person_emp_length"],
                            home_ownership=f["person_home_ownership"],
                            loan_grade=f["loan_grade"],
                            loan_amount=Decimal(str(f["loan_amnt"])),
                            interest_rate=f["loan_int_rate"],
                            previous_default=f["cb_person_default_on_file"],
                            credit_history_length=f["cb_person_cred_hist_length"],
                        )

                        Prediction.objects.create(
                            application=app,
                            default_probability=p["default_probability"],
                            credit_score=p["credit_score"],
                            risk_level=p["risk_level"],
                            predicted_status=p["prediction"],
                            model_name="Random Forest",
                        )
                        inserted_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n[SUCCESS] Successfully inserted {inserted_count} demo prediction records into MySQL!"
                    )
                )
                self.stdout.write(f"Total Loan Applications now: {LoanApplication.objects.count()}")
                self.stdout.write(f"Total Predictions now:       {Prediction.objects.count()}")

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"Transaction failed and was rolled back: {str(e)}")
                )
