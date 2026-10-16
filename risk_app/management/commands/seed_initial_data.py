import json

from django.core.management.base import BaseCommand

from ml.train_model import MODEL_DIR
from risk_app.models import LoanType, ModelInfo

# code = exact value the model was trained on (dataset: loan_intent)
LOAN_TYPES = [
    ("EDUCATION", "Education", "Study / course fees"),
    ("MEDICAL", "Medical", "Hospital and medical expenses"),
    ("VENTURE", "Venture", "Business or startup"),
    ("PERSONAL", "Personal", "General personal needs"),
    ("HOMEIMPROVEMENT", "Home Improvement", "Repair / renovation"),
    ("DEBTCONSOLIDATION", "Debt Consolidation", "Combine old loans into one"),
]


class Command(BaseCommand):
    help = "Add loan types and the trained model's performance to the database."

    def handle(self, *args, **options):
        for code, name, description in LOAN_TYPES:
            LoanType.objects.update_or_create(
                code=code, defaults={"name": name, "description": description}
            )
        self.stdout.write(self.style.SUCCESS(f"Loan types: {LoanType.objects.count()}"))

        with open(MODEL_DIR / "best_model_info.json") as f:
            info = json.load(f)
        m = info["metrics"]

        ModelInfo.objects.all().delete()          # keep only the latest model info
        ModelInfo.objects.create(
            model_name="Random Forest (tuned)",
            accuracy=m["Accuracy"],
            precision=m["Precision"],
            recall=m["Recall"],
            f1_score=m["F1"],
            roc_auc=m["ROC-AUC"],
            training_rows=25927,
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS("Model info saved: ROC-AUC " + str(m["ROC-AUC"])))