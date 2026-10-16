from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    ActivityLog,
    ContactMessage,
    LoanApplication,
    LoanType,
    ModelInfo,
    Prediction,
    User,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ("email",)
    list_display = ("email", "full_name", "role", "is_staff", "is_active")
    search_fields = ("email", "full_name")

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


@admin.register(LoanType)
class LoanTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "loan_type", "loan_amount", "annual_income", "loan_grade", "created_at")
    list_filter = ("loan_type", "loan_grade", "home_ownership", "previous_default")
    search_fields = ("full_name", "user__email")
    date_hierarchy = "created_at"


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ("application", "credit_score", "risk_level", "default_probability", "created_at")
    list_filter = ("risk_level",)
    date_hierarchy = "created_at"


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