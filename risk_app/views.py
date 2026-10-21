
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

from ml.predict import (
    LOW_RISK_MIN_SCORE,
    MEDIUM_RISK_MIN_SCORE,
    predict_credit_risk,
)

from .forms import EditProfileForm, RegisterForm, RiskCheckerForm
from .models import (
    ContactMessage,
    LoanApplication,
    LoanType,
    ModelInfo,
    Prediction,
)

User = get_user_model()


def home(request):
    model_info = ModelInfo.objects.filter(is_active=True).first()

    performance = []
    trained_on = ""

    if model_info:
        trained_on = f"{model_info.training_rows:,}"

        performance = [
            {
                "label": "ROC-AUC",
                "value": f"{model_info.roc_auc:.3f}",
                "icon": "bi-graph-up-arrow",
            },
            {
                "label": "Accuracy",
                "value": f"{model_info.accuracy * 100:.1f}%",
                "icon": "bi-bullseye",
            },
            {
                "label": "Precision",
                "value": f"{model_info.precision * 100:.1f}%",
                "icon": "bi-crosshair",
            },
            {
                "label": "Recall",
                "value": f"{model_info.recall * 100:.1f}%",
                "icon": "bi-search",
            },
        ]

    context = {
        "model_info": model_info,
        "performance": performance,
        "trained_on": trained_on,
        "low_min": LOW_RISK_MIN_SCORE,
        "medium_min": MEDIUM_RISK_MIN_SCORE,
        "medium_max": LOW_RISK_MIN_SCORE - 1,
        "high_max": MEDIUM_RISK_MIN_SCORE - 1,
    }

    return render(request, "home.html", context)


def about_view(request):
    model_info = ModelInfo.objects.filter(is_active=True).first()

    performance = []

    if model_info:
        performance = [
            {
                "label": "ROC-AUC",
                "value": f"{model_info.roc_auc:.3f}",
                "icon": "bi-graph-up-arrow",
            },
            {
                "label": "Accuracy",
                "value": f"{model_info.accuracy * 100:.1f}%",
                "icon": "bi-bullseye",
            },
            {
                "label": "Precision",
                "value": f"{model_info.precision * 100:.1f}%",
                "icon": "bi-crosshair",
            },
            {
                "label": "Recall",
                "value": f"{model_info.recall * 100:.1f}%",
                "icon": "bi-search",
            },
        ]

    context = {
        "model_info": model_info,
        "performance": performance,
        "trained_on": (
            f"{model_info.training_rows:,}" if model_info else None
        ),
    }

    return render(request, "about.html", context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegisterForm(request.POST)
    else:
        form = RegisterForm()

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)

        messages.success(
            request,
            f"Welcome, {user.full_name}! Your account is ready.",
        )

        return redirect("home")

    return render(request, "register.html", {"form": form})


@login_required
def history_view(request):
    applications = (
        LoanApplication.objects
        .filter(user=request.user)
        .select_related("loan_type", "prediction")
        .order_by("-created_at")
    )

    return render(
        request,
        "history.html",
        {"applications": applications},
    )


@login_required
def risk_checker_view(request):
    if request.method == "POST":
        form = RiskCheckerForm(request.POST)
    else:
        form = RiskCheckerForm()

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data.copy()

        data["person_income"] = float(data["person_income"])
        data["loan_amnt"] = float(data["loan_amnt"])

        try:
            # Generate ML prediction
            result = predict_credit_risk(data)

            loan_type = LoanType.objects.get(
                code=data["loan_intent"],
                is_active=True,
            )

            with transaction.atomic():
                application = LoanApplication.objects.create(
                    user=request.user,
                    loan_type=loan_type,
                    full_name=request.user.full_name,
                    age=data["person_age"],
                    annual_income=data["person_income"],
                    employment_length=data["person_emp_length"],
                    home_ownership=data["person_home_ownership"],
                    loan_grade=data["loan_grade"],
                    loan_amount=data["loan_amnt"],
                    interest_rate=data["loan_int_rate"],
                    previous_default=data[
                        "cb_person_default_on_file"
                    ],
                    credit_history_length=data[
                        "cb_person_cred_hist_length"
                    ],
                )

                Prediction.objects.create(
                    application=application,
                    default_probability=result[
                        "default_probability"
                    ],
                    credit_score=result["credit_score"],
                    risk_level=result["risk_level"],
                    predicted_status=result["prediction"],
                )

            messages.success(
                request,
                "Credit risk prediction completed and saved successfully!",
            )

            return redirect(
                "result",
                application_id=application.id,
            )

        except LoanType.DoesNotExist:
            messages.error(
                request,
                "Selected loan type is not configured. "
                "Please contact the administrator.",
            )

        except Exception as error:
            print("PREDICTION ERROR:", repr(error))
            messages.error(
                request,
                "Prediction failed. Please check the ML model files "
                "and try again.",
            )

    return render(
        request,
        "risk_checker.html",
        {"form": form},
    )


def contact_view(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()

        if not all([name, email, subject, message]):
            messages.error(
                request,
                "Please fill in all required fields.",
            )
            return render(request, "contact.html")

        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message,
        )

        messages.success(
            request,
            "Your message has been submitted successfully!",
        )

        return redirect("contact")

    return render(request, "contact.html")


@login_required
def profile_view(request):
    """Display account details; editing is handled on a separate page."""
    return render(request, "profile.html")


@login_required
def edit_profile_view(request):
    """Update the signed-in user's name and email without changing security settings."""
    form = EditProfileForm(
        request.POST or None,
        instance=request.user,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated successfully.")
        return redirect("profile")

    return render(request, "edit_profile.html", {"form": form})


@login_required
def result_view(request, application_id):
    application = get_object_or_404(
        LoanApplication.objects.select_related(
            "loan_type",
            "prediction",
        ),
        pk=application_id,
        user=request.user,
    )

    score_percentage = round(
        application.prediction.credit_score / 900 * 100
    )

    return render(
        request,
        "result.html",
        {
            "application": application,
            "score_percentage": score_percentage,
        },
    )


class RiskWisePasswordChangeView(PasswordChangeView):
    template_name = "password_change.html"
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        messages.success(
            self.request,
            "Your password has been changed successfully.",
        )
        return super().form_valid(form)
