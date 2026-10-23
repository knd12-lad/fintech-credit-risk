"""
Django Management Command: export_powerbi_dataset
Exports the combined LoanApplication + Prediction dataset to
powerbi/data/riskwise_powerbi_dataset.csv for Power BI reporting.

Strict Data Privacy & Quality Guarantees:
- Never exposes real user PII (names, emails, phones, passwords).
- Anonymizes real users to 'User #<id>'.
- Properly encodes income tiers without shell parameter expansion.
- Outputs UTF-8 encoded CSV with exactly 24 columns in strict order.
"""

import csv
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from risk_app.models import LoanApplication, Prediction


def get_age_group(age: int) -> str:
    if age <= 25:
        return "18-25"
    elif age <= 35:
        return "26-35"
    elif age <= 50:
        return "36-50"
    return "51+"


def get_income_tier(income: float) -> str:
    if income < 25000:
        return "< $25k"
    elif income < 50000:
        return "$25k - $50k"
    elif income < 75000:
        return "$50k - $75k"
    elif income < 100000:
        return "$75k - $100k"
    return "> $100k"


class Command(BaseCommand):
    help = "Export combined LoanApplication + Prediction data to powerbi/data/riskwise_powerbi_dataset.csv"

    COLUMNS = [
        "application_id",
        "applicant_label",
        "is_demo",
        "age",
        "age_group",
        "annual_income",
        "income_tier",
        "employment_length",
        "home_ownership",
        "loan_grade",
        "loan_amount",
        "interest_rate",
        "previous_default",
        "credit_history_length",
        "loan_intent_code",
        "loan_intent_name",
        "loan_to_income",
        "interest_to_income",
        "default_probability",
        "default_probability_pct",
        "credit_score",
        "risk_level",
        "predicted_default",
        "created_at",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Optional path to output CSV file (default: powerbi/data/riskwise_powerbi_dataset.csv)",
        )

    def handle(self, *args, **options):
        output_arg = options.get("output")
        if output_arg:
            csv_path = Path(output_arg)
        else:
            csv_path = Path(settings.BASE_DIR) / "powerbi" / "data" / "riskwise_powerbi_dataset.csv"

        csv_path.parent.mkdir(parents=True, exist_ok=True)

        applications = (
            LoanApplication.objects.select_related("user", "loan_type", "prediction")
            .filter(prediction__isnull=False)
            .order_by("-id")
        )

        rows = []
        income_tier_counts = {}
        age_group_counts = {}
        risk_level_counts = {}
        is_demo_counts = {}
        total_loan_amount = Decimal("0")

        for app in applications:
            pred = app.prediction
            is_demo_val = "Demo" if app.full_name.startswith("Demo Applicant #") else "Real"
            applicant_label = app.full_name if is_demo_val == "Demo" else f"User #{app.user_id}"

            income_val = float(app.annual_income)
            loan_val = float(app.loan_amount)
            rate_val = float(app.interest_rate)

            age_grp = get_age_group(app.age)
            inc_tier = get_income_tier(income_val)
            r_level = pred.risk_level

            # Calculate financial ratios
            l_to_inc = round(loan_val / income_val, 4) if income_val > 0 else 0.0
            interest_amt = loan_val * (rate_val / 100.0)
            int_to_inc = round(interest_amt / income_val, 4) if income_val > 0 else 0.0

            # Convert created_at to local/aware string
            created_str = (
                timezone.localtime(app.created_at).strftime("%Y-%m-%d %H:%M:%S")
                if app.created_at
                else ""
            )

            row = [
                app.id,
                applicant_label,
                is_demo_val,
                app.age,
                age_grp,
                round(income_val, 1),
                inc_tier,
                round(float(app.employment_length), 1),
                app.home_ownership,
                app.loan_grade,
                round(loan_val, 1),
                round(rate_val, 2),
                app.previous_default,
                app.credit_history_length,
                app.loan_type.code,
                app.loan_type.name,
                l_to_inc,
                int_to_inc,
                round(pred.default_probability, 4),
                round(pred.default_probability * 100.0, 2),
                pred.credit_score,
                r_level,
                pred.predicted_status,
                created_str,
            ]
            rows.append(row)

            # Accumulate statistics
            income_tier_counts[inc_tier] = income_tier_counts.get(inc_tier, 0) + 1
            age_group_counts[age_grp] = age_group_counts.get(age_grp, 0) + 1
            risk_level_counts[r_level] = risk_level_counts.get(r_level, 0) + 1
            is_demo_counts[is_demo_val] = is_demo_counts.get(is_demo_val, 0) + 1
            total_loan_amount += app.loan_amount

        # Write CSV with UTF-8 encoding
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.COLUMNS)
            writer.writerows(rows)

        self.stdout.write(
            self.style.SUCCESS(f"Successfully exported {len(rows)} records to {csv_path}")
        )
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("POWER BI DATASET EXPORT SUMMARY")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total Rows Exported: {len(rows)}")
        self.stdout.write(f"Total Loan Volume:   ${total_loan_amount:,.2f}")

        self.stdout.write("\n--- income_tier ---")
        for tier in ["< $25k", "$25k - $50k", "$50k - $75k", "$75k - $100k", "> $100k"]:
            self.stdout.write(f"  {tier:<15}: {income_tier_counts.get(tier, 0)}")

        self.stdout.write("\n--- age_group ---")
        for grp in ["18-25", "26-35", "36-50", "51+"]:
            self.stdout.write(f"  {grp:<15}: {age_group_counts.get(grp, 0)}")

        self.stdout.write("\n--- risk_level ---")
        for r in ["Low", "Medium", "High"]:
            self.stdout.write(f"  {r:<15}: {risk_level_counts.get(r, 0)}")

        self.stdout.write("\n--- is_demo ---")
        for d in ["Demo", "Real"]:
            self.stdout.write(f"  {d:<15}: {is_demo_counts.get(d, 0)}")
        self.stdout.write("=" * 60 + "\n")
