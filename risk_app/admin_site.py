# RW-D6
import csv
from datetime import timedelta
from functools import lru_cache

from django.contrib.admin import AdminSite
from django.db.models import Avg, Count, Q
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone

from ml.train_model import DATASET_DIR, MODEL_DIR

INTENT_NAMES = {
    "DEBTCONSOLIDATION": "Debt Consolidation",
    "MEDICAL": "Medical",
    "HOMEIMPROVEMENT": "Home Improvement",
    "PERSONAL": "Personal",
    "EDUCATION": "Education",
    "VENTURE": "Venture",
}


@lru_cache(maxsize=1)
def training_insights():
    """Default rate by category, from the cleaned training dataset (cached)."""
    csv_path = DATASET_DIR / "loan_data_cleaned.csv"
    if not csv_path.exists():
        return None

    import pandas as pd

    df = pd.read_csv(csv_path)

    def rate(column, order=None, names=None, sort_desc=False):
        s = (df.groupby(column)["loan_status"].mean() * 100).round(1)
        if order:
            s = s.reindex(order)
        if sort_desc:
            s = s.sort_values(ascending=False)
        labels = [(names or {}).get(str(i), str(i)) for i in s.index]
        return {"labels": labels, "values": [float(v) for v in s.values]}

    return {
        "rows": int(len(df)),
        "overall": round(float(df["loan_status"].mean() * 100), 1),
        "grade": rate("loan_grade", order=list("ABCDEFG")),
        "intent": rate("loan_intent", names=INTENT_NAMES, sort_desc=True),
        "home": rate("person_home_ownership", names={"RENT": "Rent", "OWN": "Own", "MORTGAGE": "Mortgage", "OTHER": "Other"}, sort_desc=True),
        "previous": rate("cb_person_default_on_file", names={"N": "No", "Y": "Yes"}),
    }


def model_comparison():
    """Rows of ml/saved_models/model_comparison.csv with the best ROC-AUC marked."""
    csv_path = MODEL_DIR / "model_comparison.csv"
    if not csv_path.exists():
        return []

    rows = []
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append({
                    "name": r.get("Model") or next(iter(r.values())),
                    "accuracy": float(r["Accuracy"]),
                    "precision": float(r["Precision"]),
                    "recall": float(r["Recall"]),
                    "f1": float(r["F1"]),
                    "roc_auc": float(r["ROC-AUC"]),
                    "best": False,
                })
    except (KeyError, ValueError):
        return []

    if rows:
        max(rows, key=lambda x: x["roc_auc"])["best"] = True
    return rows


class RiskWiseAdminSite(AdminSite):
    site_header = "RiskWise Admin"
    site_title = "RiskWise Admin"
    index_title = "Dashboard"
    index_template = "admin/dashboard.html"

    # ------------------------------------------------------------------
    # URLs & Authentication
    # ------------------------------------------------------------------
    def get_urls(self):
        custom = [
            path("analytics/", self.admin_view(self.analytics_view), name="analytics"),
            path("profile/", self.admin_view(self.profile_view), name="profile"),
            path("profile/edit/", self.admin_view(self.profile_edit_view), name="profile_edit"),
        ]
        return custom + super().get_urls()

    def profile_view(self, request):
        """Administrative Profile view styled exactly like the main website profile page."""
        context = {
            **self.each_context(request),
            "title": "My Profile",
        }
        return TemplateResponse(request, "admin/profile.html", context)

    def profile_edit_view(self, request):
        """Administrative Profile Edit view styled exactly like the main website edit profile page."""
        from django.contrib import messages
        from django.shortcuts import redirect
        from .forms import AdminProfileForm

        if request.method == "POST":
            form = AdminProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, "Your profile has been updated successfully.")
                return redirect("admin:profile")
            else:
                messages.error(request, "Please correct the errors below.")
        else:
            form = AdminProfileForm(instance=request.user)

        context = {
            **self.each_context(request),
            "title": "Edit Profile",
            "form": form,
        }
        return TemplateResponse(request, "admin/edit_profile.html", context)

    def logout(self, request, extra_context=None):
        """Render dedicated RiskWise admin logged out page for both GET and POST requests."""
        from django.contrib.auth import logout
        from django.template.response import TemplateResponse

        logout(request)
        context = {
            **self.each_context(request),
            "title": "Logged Out",
            "has_permission": False,
            **(extra_context or {}),
        }
        return TemplateResponse(request, self.logout_template or "admin/logged_out.html", context)

    # ------------------------------------------------------------------
    # Dashboard (Step 2)
    # ------------------------------------------------------------------
    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(self._dashboard_context())
        return super().index(request, extra_context=extra_context)

    def _dashboard_context(self):
        # imported here so the admin site loads before the models at startup
        from .models import LoanApplication, Prediction, User

        predictions = Prediction.objects.all()
        total_predictions = predictions.count()
        predicted_defaults = predictions.filter(predicted_status=1).count()

        default_pct = round(predicted_defaults / total_predictions * 100, 1) if total_predictions else 0
        avg_score = predictions.aggregate(a=Avg("credit_score"))["a"]
        avg_score = round(avg_score) if avg_score else 0

        risk_counts = [
            predictions.filter(risk_level=level).count()
            for level in ("Low", "Medium", "High")
        ]

        # Applications per day, last 14 days (counted in Python, no MySQL timezone tables needed)
        today = timezone.localdate()
        start = today - timedelta(days=13)
        per_day = {start + timedelta(days=i): 0 for i in range(14)}
        since = timezone.now() - timedelta(days=15)
        for created in LoanApplication.objects.filter(created_at__gte=since).values_list("created_at", flat=True):
            day = timezone.localtime(created).date()
            if day in per_day:
                per_day[day] += 1

        recent = []
        recent_qs = Prediction.objects.select_related("application").order_by("-created_at")[:5]
        for p in recent_qs:
            recent.append({
                "id": p.pk,
                "name": p.application.full_name,
                "amount": p.application.loan_amount,
                "score": p.credit_score,
                "prob": round(p.default_probability * 100, 1),
                "risk": p.risk_level,
                "created": p.created_at,
            })

        return {
            "has_data": total_predictions > 0,
            "kpi": {
                "applications": LoanApplication.objects.count(),
                "users": User.objects.count(),
                "default_pct": default_pct,
                "avg_score": avg_score,
            },
            "chart_data": {
                "risk": risk_counts,
                "days": [d.strftime("%d %b") for d in per_day],
                "per_day": list(per_day.values()),
            },
            "recent": recent,
        }

    # ------------------------------------------------------------------
    # Analytics (Step 6)
    # ------------------------------------------------------------------
    def analytics_view(self, request):
        from .models import LoanType, Prediction

        insights = training_insights()
        models = model_comparison()
        best = next((m for m in models if m["best"]), None)

        total_live = Prediction.objects.count()

        grade_rows = (
            Prediction.objects.values("application__loan_grade")
            .annotate(avg=Avg("credit_score"))
            .order_by("application__loan_grade")
        )
        live_grade = {
            "labels": [r["application__loan_grade"] for r in grade_rows],
            "values": [round(r["avg"]) for r in grade_rows],
        }

        type_rows = LoanType.objects.annotate(
            low=Count("applications__prediction", filter=Q(applications__prediction__risk_level="Low")),
            medium=Count("applications__prediction", filter=Q(applications__prediction__risk_level="Medium")),
            high=Count("applications__prediction", filter=Q(applications__prediction__risk_level="High")),
        ).order_by("name")
        live_type = {
            "labels": [t.name for t in type_rows],
            "low": [t.low for t in type_rows],
            "medium": [t.medium for t in type_rows],
            "high": [t.high for t in type_rows],
        }

        context = {
            **self.each_context(request),
            "title": "Analytics",
            "insights": insights,
            "models": models,
            "best": best,
            "total_live": total_live,
            "chart_payload": {
                "insights": insights,
                "live_grade": live_grade,
                "live_type": live_type,
                "has_live": total_live > 0,
            },
        }
        return TemplateResponse(request, "admin/analytics.html", context)
