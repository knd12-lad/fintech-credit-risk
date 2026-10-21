# RW-D5
import csv

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    ActivityLog,
    ContactMessage,
    LoanApplication,
    LoanType,
    ModelInfo,
    Prediction,
    User,
)


def risk_badge(level):
    """Green / amber / red badge for Low / Medium / High."""
    return format_html('<span class="rw-badge rw-b-{}">{}</span>', level.lower(), level)


def csv_safe(value):
    """Stop Excel from running text like =1+1 as a formula."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@"):
        return "'" + text
    return text


# ---------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------
class UserApplicationInline(admin.TabularInline):
    """Loan applications of this user (read only)."""

    model = LoanApplication
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name_plural = "Loan applications of this user"
    fields = ("created_at", "loan_type", "loan_amount", "annual_income", "loan_grade")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ("-date_joined",)
    list_per_page = 20
    inlines = [UserApplicationInline]

    list_display = (
        "email", "full_name", "role_badge", "application_count",
        "status_badge", "last_login", "date_joined",
    )
    list_filter = ("role", "is_active", "date_joined")
    search_fields = ("email", "full_name")
    actions = ["activate_users", "deactivate_users"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("full_name", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "role", "password1", "password2"),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(application_count=Count("applications"))

    @admin.display(description="Applications", ordering="application_count")
    def application_count(self, obj):
        return obj.application_count

    @admin.display(description="Role", ordering="role")
    def role_badge(self, obj):
        css = "rw-b-admin" if obj.role == "ADMIN" else "rw-b-user"
        return format_html('<span class="rw-badge {}">{}</span>', css, obj.get_role_display())

    @admin.display(description="Status", ordering="is_active")
    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="rw-badge rw-b-yes">Active</span>')
        return format_html('<span class="rw-badge rw-b-no">Inactive</span>')

    def save_model(self, request, obj, form, change):
        # Role decides who can open the admin panel (superusers are not changed)
        if not obj.is_superuser:
            obj.is_staff = obj.role == "ADMIN"
        super().save_model(request, obj, form, change)

    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) activated.", messages.SUCCESS)

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        safe = queryset.exclude(pk=request.user.pk).exclude(is_superuser=True)
        skipped = queryset.count() - safe.count()
        updated = safe.update(is_active=False)
        self.message_user(request, f"{updated} user(s) deactivated.", messages.SUCCESS)
        if skipped:
            self.message_user(
                request,
                f"{skipped} user(s) skipped: you cannot deactivate yourself or a superuser.",
                messages.WARNING,
            )


# ---------------------------------------------------------------------
# Applicants (loan applications)
# ---------------------------------------------------------------------
class PredictionInline(admin.TabularInline):
    """The prediction made for this application (read only)."""

    model = Prediction
    extra = 0
    can_delete = False
    verbose_name_plural = "Prediction"
    fields = ("credit_score", "default_probability", "risk_level", "predicted_status", "created_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_per_page = 20
    list_select_related = ("user", "loan_type", "prediction")
    # date_hierarchy = "created_at"
    inlines = [PredictionInline]

    list_display = (
        "full_name", "user_email", "loan_type", "age", "income_display",
        "loan_display", "ratio_display", "loan_grade", "interest_rate",
        "previous_default", "score_display", "risk_display", "created_at",
    )
    list_filter = (
        "loan_type", "loan_grade", "home_ownership", "previous_default",
        "prediction__risk_level", "created_at",
    )
    search_fields = ("full_name", "user__email")

    fieldsets = (
        ("Applicant", {"fields": (
            "user", "full_name", "age", "employment_length",
            "home_ownership", "credit_history_length", "previous_default",
        )}),
        ("Loan", {"fields": (
            "loan_type", "annual_income", "loan_amount", "interest_rate",
            "loan_grade", "ratio_display",
        )}),
        ("Date", {"fields": ("created_at",)}),
    )
    readonly_fields = ("created_at", "ratio_display")

    # Applications are created from the website only
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="User", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Income", ordering="annual_income")
    def income_display(self, obj):
        return f"{obj.annual_income:,.0f}"

    @admin.display(description="Loan amount", ordering="loan_amount")
    def loan_display(self, obj):
        return f"{obj.loan_amount:,.0f}"

    @admin.display(description="Loan / Income")
    def ratio_display(self, obj):
        return f"{obj.loan_to_income:.2f}"

    @admin.display(description="Score", ordering="prediction__credit_score")
    def score_display(self, obj):
        return obj.prediction.credit_score if hasattr(obj, "prediction") else "-"

    @admin.display(description="Risk", ordering="prediction__risk_level")
    def risk_display(self, obj):
        return risk_badge(obj.prediction.risk_level) if hasattr(obj, "prediction") else "-"


# ---------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------
@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_per_page = 20
    list_select_related = ("application__user", "application__loan_type")
    # date_hierarchy = "created_at"
    actions = ["export_csv"]

    list_display = (
        "applicant", "user_email", "loan_type", "loan_amount", "credit_score",
        "probability_display", "risk_display", "result_display", "created_at",
    )
    list_filter = (
        "risk_level", "predicted_status", "application__loan_type",
        "application__loan_grade", "created_at",
    )
    search_fields = ("application__full_name", "application__user__email")

    fields = (
        "application", "credit_score", "probability_display", "risk_display",
        "result_display", "model_name", "created_at",
    )
    readonly_fields = fields

    # Predictions are created by the model only
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Applicant", ordering="application__full_name")
    def applicant(self, obj):
        return obj.application.full_name

    @admin.display(description="User", ordering="application__user__email")
    def user_email(self, obj):
        return obj.application.user.email

    @admin.display(description="Loan type", ordering="application__loan_type__name")
    def loan_type(self, obj):
        return obj.application.loan_type.name

    @admin.display(description="Loan amount", ordering="application__loan_amount")
    def loan_amount(self, obj):
        return f"{obj.application.loan_amount:,.0f}"

    @admin.display(description="Default probability", ordering="default_probability")
    def probability_display(self, obj):
        return f"{obj.default_probability * 100:.1f}%"

    @admin.display(description="Risk", ordering="risk_level")
    def risk_display(self, obj):
        return risk_badge(obj.risk_level)

    @admin.display(description="Result", ordering="predicted_status")
    def result_display(self, obj):
        return "Default" if obj.predicted_status == 1 else "No default"

    @admin.action(description="Export selected predictions to CSV")
    def export_csv(self, request, queryset):
        stamp = timezone.localtime().strftime("%Y%m%d_%H%M")
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="riskwise_predictions_{stamp}.csv"'
        response.write("\ufeff")          # lets Excel read the file as UTF-8

        writer = csv.writer(response)
        writer.writerow([
            "Prediction ID", "Date", "Applicant", "User email", "Loan type", "Age",
            "Annual income", "Employment length", "Home ownership", "Credit history length",
            "Previous default", "Loan amount", "Interest rate", "Loan grade",
            "Credit score", "Default probability %", "Risk level", "Result", "Model",
        ])

        rows = queryset.select_related("application__user", "application__loan_type")
        for p in rows:
            a = p.application
            writer.writerow([
                p.pk,
                timezone.localtime(p.created_at).strftime("%Y-%m-%d %H:%M"),
                csv_safe(a.full_name),
                csv_safe(a.user.email),
                csv_safe(a.loan_type.name),
                a.age,
                a.annual_income,
                a.employment_length,
                a.home_ownership,
                a.credit_history_length,
                a.previous_default,
                a.loan_amount,
                a.interest_rate,
                a.loan_grade,
                p.credit_score,
                round(p.default_probability * 100, 2),
                p.risk_level,
                "Default" if p.predicted_status == 1 else "No default",
                csv_safe(p.model_name),
            ])
        return response


# ---------------------------------------------------------------------
# Other models
# ---------------------------------------------------------------------
@admin.register(LoanType)
class LoanTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(ModelInfo)
class ModelInfoAdmin(admin.ModelAdmin):
    list_display = ("model_name", "accuracy", "recall", "roc_auc", "is_active", "created_at")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("name", "email", "subject")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "ip_address", "created_at")
    list_filter = ("action",)
    search_fields = ("action", "user__email")