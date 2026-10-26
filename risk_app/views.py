import logging
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

logger = logging.getLogger(__name__)

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
from .utils import needle_angle

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

    hero = {
        "is_sample": True,
        "score": 828,
        "probability_pct": 12,
        "risk_level_key": "low",
        "risk_label": "Low Risk",
        "needle_angle": needle_angle(828),
        "created_at": None,
        "application_id": None,
        "has_history": False,
    }
    has_history = False

    if request.user.is_authenticated:
        latest_pred = (
            Prediction.objects.filter(application__user=request.user)
            .select_related("application")
            .order_by("-created_at")
            .first()
        )
        if latest_pred:
            has_history = True
            risk_level_key = (latest_pred.risk_level or "low").lower()
            risk_labels = {
                "low": "Low Risk",
                "medium": "Medium Risk",
                "high": "High Risk",
            }
            hero = {
                "is_sample": False,
                "score": latest_pred.credit_score,
                "probability_pct": round(latest_pred.default_probability * 100),
                "risk_level_key": risk_level_key,
                "risk_label": risk_labels.get(risk_level_key, f"{latest_pred.risk_level} Risk"),
                "needle_angle": needle_angle(latest_pred.credit_score),
                "created_at": latest_pred.created_at,
                "application_id": latest_pred.application.id,
                "has_history": True,
            }

    context = {
        "model_info": model_info,
        "performance": performance,
        "trained_on": trained_on,
        "low_min": LOW_RISK_MIN_SCORE,
        "medium_min": MEDIUM_RISK_MIN_SCORE,
        "medium_max": LOW_RISK_MIN_SCORE - 1,
        "high_max": MEDIUM_RISK_MIN_SCORE - 1,
        "hero": hero,
        "has_history": has_history,
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

        try:
            email_subject = f"[RiskWise Contact] {subject}"
            email_body = (
                f"New contact inquiry submitted to RiskWise:\n\n"
                f"From: {name} <{email}>\n"
                f"Subject: {subject}\n\n"
                f"Message:\n{message}\n"
            )
            recipient = getattr(settings, "EMAIL_HOST_USER", "") or "admin@riskwise.local"
            send_mail(
                subject=email_subject,
                message=email_body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@riskwise.local"),
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception as e:
            logger.warning("Failed to send contact notification email: %s", e)

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

    explanation = None
    try:
        from ml.explain import explain_prediction

        app_data = {
            "person_age": application.age,
            "person_income": float(application.annual_income),
            "person_emp_length": float(application.employment_length),
            "loan_amnt": float(application.loan_amount),
            "loan_int_rate": float(application.interest_rate),
            "cb_person_cred_hist_length": application.credit_history_length,
            "loan_grade": application.loan_grade,
            "cb_person_default_on_file": application.previous_default,
            "person_home_ownership": application.home_ownership,
            "loan_intent": application.loan_type.code,
        }
        explanation = explain_prediction(app_data)
    except Exception as e:
        logger.exception("Failed to generate prediction explanation: %s", e)

    return render(
        request,
        "result.html",
        {
            "application": application,
            "score_percentage": score_percentage,
            "explanation": explanation,
        },
    )


@login_required
def what_if_api(request, application_id):
    """
    Simulation endpoint: evaluates modified loan parameters without database writes.
    Login required, owner only (404 otherwise). Rate-limited to 60 requests/minute.
    """
    application = get_object_or_404(
        LoanApplication.objects.select_related("loan_type", "prediction"),
        pk=application_id,
        user=request.user,
    )

    # Per-user rate limit (60 requests per minute)
    cache_key = f"what_if_rl_{request.user.pk}"
    req_count = cache.get(cache_key, 0)
    if req_count >= 60:
        return JsonResponse(
            {"error": "Rate limit exceeded (60 requests per minute). Please wait."},
            status=429,
        )
    cache.set(cache_key, req_count + 1, timeout=60)

    # Base application data
    data = {
        "person_age": int(application.age),
        "person_income": float(application.annual_income),
        "person_emp_length": float(application.employment_length),
        "person_home_ownership": application.home_ownership,
        "loan_intent": application.loan_type.code,
        "loan_grade": application.loan_grade,
        "loan_amnt": float(application.loan_amount),
        "loan_int_rate": float(application.interest_rate),
        "cb_person_default_on_file": application.previous_default,
        "cb_person_cred_hist_length": int(application.credit_history_length),
    }

    allowed_params = [
        "person_income",
        "loan_amnt",
        "loan_int_rate",
        "person_emp_length",
        "cb_person_cred_hist_length",
    ]

    for param in allowed_params:
        if param in request.GET:
            raw_val = request.GET.get(param)
            if raw_val is not None and str(raw_val).strip() != "":
                field = RiskCheckerForm.base_fields.get(param)
                if field is not None:
                    try:
                        cleaned = field.clean(raw_val)
                    except forms.ValidationError as e:
                        msg = e.messages[0] if hasattr(e, "messages") and e.messages else str(e)
                        return JsonResponse({"error": f"{param}: {msg}"}, status=400)
                    except Exception as e:
                        return JsonResponse({"error": f"{param}: {str(e)}"}, status=400)

                    if param in ("person_income", "loan_amnt", "loan_int_rate", "person_emp_length"):
                        data[param] = float(cleaned)
                    elif param == "cb_person_cred_hist_length":
                        data[param] = int(cleaned)

    try:
        pred_res = predict_credit_risk(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    score = pred_res["credit_score"]
    prob = pred_res["default_probability"]
    prob_pct = round(prob * 100, 1)
    risk_level = pred_res["risk_level"]
    risk_label = f"{risk_level} Risk"
    angle = needle_angle(score)

    saved_pred = application.prediction
    saved_score = saved_pred.credit_score
    saved_prob_pct = round(saved_pred.default_probability * 100, 1)

    delta_score = score - saved_score
    delta_prob_pct = round(prob_pct - saved_prob_pct, 1)

    return JsonResponse({
        "score": score,
        "probability_pct": prob_pct,
        "risk_level": risk_level,
        "risk_label": risk_label,
        "needle_angle": angle,
        "delta_score": delta_score,
        "delta_probability_pct": delta_prob_pct,
    })


class RiskWisePasswordChangeView(PasswordChangeView):
    template_name = "password_change.html"
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        messages.success(
            self.request,
            "Your password has been changed successfully.",
        )
        return super().form_valid(form)
