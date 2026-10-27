import logging
import math
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import connection, transaction
from django.http import Http404, HttpResponse, JsonResponse
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
    ActivityLog,
    ContactMessage,
    LoanApplication,
    LoanType,
    ModelInfo,
    Prediction,
)
from .reports import generate_risk_report_pdf
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

    whatif_limits = get_whatif_limits()
    whatif_config = get_whatif_config(application, whatif_limits)

    return render(
        request,
        "result.html",
        {
            "application": application,
            "score_percentage": score_percentage,
            "explanation": explanation,
            "whatif_limits": whatif_limits,
            "whatif_config": whatif_config,
        },
    )


def calculate_nice_step(min_val, max_val, default_step=1):
    diff = max_val - min_val
    if diff <= 0:
        return default_step
    target = diff / 100.0
    nice_steps = [1, 5, 10, 50, 100, 250, 500, 1000]
    return min(nice_steps, key=lambda s: abs(s - target))


def get_whatif_limits():
    """Read limits directly from RiskCheckerForm fields."""
    limits = {}
    form = RiskCheckerForm()
    for name, field in form.fields.items():
        limit_data = {}
        if hasattr(field, "min_value") and field.min_value is not None:
            limit_data["min"] = float(field.min_value)
        if hasattr(field, "max_value") and field.max_value is not None:
            limit_data["max"] = float(field.max_value)
        if hasattr(field, "choices") and field.choices:
            limit_data["choices"] = list(field.choices)
        limits[name] = limit_data
    return limits


def get_whatif_config(application, limits):
    """Compute initial slider ranges and nice steps for the application."""
    config = {}

    inc_val = float(application.annual_income)
    inc_min = int(max(limits["person_income"]["min"], math.floor(inc_val * 0.25)))
    inc_max = int(min(limits["person_income"]["max"], math.ceil(inc_val * 3)))
    config["person_income"] = {
        "val": inc_val,
        "slider_min": inc_min,
        "slider_max": inc_max,
        "step": calculate_nice_step(inc_min, inc_max),
    }

    loan_val = float(application.loan_amount)
    loan_min = int(max(limits["loan_amnt"]["min"], math.floor(loan_val * 0.25)))
    loan_max = int(min(limits["loan_amnt"]["max"], math.ceil(loan_val * 3)))
    config["loan_amnt"] = {
        "val": loan_val,
        "slider_min": loan_min,
        "slider_max": loan_max,
        "step": calculate_nice_step(loan_min, loan_max),
    }

    age_min = int(limits["person_age"]["min"])
    age_max = int(limits["person_age"]["max"])
    config["person_age"] = {
        "val": int(application.age),
        "slider_min": age_min,
        "slider_max": age_max,
        "step": 1,
    }

    emp_min = int(limits["person_emp_length"]["min"])
    emp_max = int(limits["person_emp_length"]["max"])
    config["person_emp_length"] = {
        "val": float(application.employment_length),
        "slider_min": emp_min,
        "slider_max": emp_max,
        "step": 1,
    }

    rate_min = float(limits["loan_int_rate"]["min"])
    rate_max = float(limits["loan_int_rate"]["max"])
    config["loan_int_rate"] = {
        "val": float(application.interest_rate),
        "slider_min": rate_min,
        "slider_max": rate_max,
        "step": 0.1,
    }

    cred_min = int(limits["cb_person_cred_hist_length"]["min"])
    cred_max = int(limits["cb_person_cred_hist_length"]["max"])
    config["cb_person_cred_hist_length"] = {
        "val": int(application.credit_history_length),
        "slider_min": cred_min,
        "slider_max": cred_max,
        "step": 1,
    }

    return config


@login_required
def what_if_api(request, application_id):
    """
    Simulation endpoint: evaluates modified loan parameters without database writes.
    Login required, owner only (404 otherwise). Rate-limited to 120 requests/minute.
    """
    application = get_object_or_404(
        LoanApplication.objects.select_related("loan_type", "prediction"),
        pk=application_id,
        user=request.user,
    )

    # Per-user rate limit (120 requests per minute)
    cache_key = f"what_if_rl_{request.user.pk}"
    req_count = cache.get(cache_key, 0)
    if req_count >= 120:
        return JsonResponse(
            {"error": "Rate limit exceeded (120 requests per minute). Please wait."},
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

    all_params = [
        "person_age",
        "person_income",
        "person_emp_length",
        "person_home_ownership",
        "loan_intent",
        "loan_grade",
        "loan_amnt",
        "loan_int_rate",
        "cb_person_default_on_file",
        "cb_person_cred_hist_length",
    ]

    form = RiskCheckerForm()
    for param in all_params:
        if param in request.GET:
            raw_val = request.GET.get(param)
            if raw_val is not None and str(raw_val).strip() != "":
                field = form.fields.get(param)
                if field is not None:
                    try:
                        cleaned = field.clean(raw_val)
                    except forms.ValidationError as e:
                        msg = e.messages[0] if hasattr(e, "messages") and e.messages else str(e)
                        return JsonResponse({"error": f"{param}: {msg}", "field": param}, status=400)
                    except Exception as e:
                        return JsonResponse({"error": f"{param}: {str(e)}", "field": param}, status=400)

                    if param in ("person_income", "loan_amnt", "loan_int_rate", "person_emp_length"):
                        data[param] = float(cleaned)
                    elif param in ("person_age", "cb_person_cred_hist_length"):
                        data[param] = int(cleaned)
                    else:
                        data[param] = str(cleaned)

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


@login_required
def download_pdf_report(request, application_id):
    """
    Download a formatted PDF credit risk report for an application.
    Owner-only access; records an ActivityLog entry upon download.
    """
    application = get_object_or_404(
        LoanApplication.objects.select_related("loan_type", "prediction"),
        pk=application_id,
        user=request.user,
    )

    ActivityLog.objects.create(
        user=request.user,
        action="Report downloaded",
        details=f"Application #{application.id}",
        ip_address=request.META.get("REMOTE_ADDR"),
    )

    pdf_bytes = generate_risk_report_pdf(application)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="riskwise-report-{application.id}.pdf"'
    return response


class RiskWisePasswordChangeView(PasswordChangeView):
    template_name = "password_change.html"
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        messages.success(
            self.request,
            "Your password has been changed successfully.",
        )
        return super().form_valid(form)


def how_it_works_view(request):
    """Public guide explaining the credit risk assessment process, model metrics, and FAQ."""
    model_info = ModelInfo.objects.filter(is_active=True).first()
    return render(request, "how_it_works.html", {"model_info": model_info})


def privacy_view(request):
    """Public privacy policy describing data collection, usage, cookies, and deletion."""
    return render(request, "privacy.html")


def terms_view(request):
    """Public terms of service outlining educational scope, acceptable use, and disclaimers."""
    return render(request, "terms.html")


def robots_txt(request):
    """
    Search engine crawler rules allowing public indexation while disallowing
    internal tools, personal account views, administrative areas, and APIs.
    """
    site_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/")
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Disallow: /history/",
        "Disallow: /profile/",
        "Disallow: /result/",
        "Disallow: /risk-checker/",
        "Disallow: /view-as/",
        "Disallow: /demo-login/",
        "Allow: /",
        "",
        f"Sitemap: {site_url}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def healthz_view(request):
    """
    Public operations health check returning JSON status.
    Performs real DB probe and ML model load check.
    Returns 200 {"status": "ok", "database": "ok", "model": "ok"} on success.
    Returns 503 with status "error" when any dependency check fails.
    No authentication, no secrets, no caching.
    """
    db_ok = False
    model_ok = False

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_ok = True
    except Exception as exc:
        logger.exception("Health check database probe failed: %s", exc)
        db_ok = False

    try:
        import ml.predict
        ml.predict._load()
        model_ok = True
    except Exception as exc:
        logger.exception("Health check model probe failed: %s", exc)
        model_ok = False

    if db_ok and model_ok:
        response = JsonResponse(
            {
                "status": "ok",
                "database": "ok",
                "model": "ok",
            },
            status=200,
        )
    else:
        response = JsonResponse(
            {
                "status": "error",
                "database": "ok" if db_ok else "error",
                "model": "ok" if model_ok else "error",
            },
            status=503,
        )

    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

