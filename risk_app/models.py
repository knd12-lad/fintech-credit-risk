from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator



class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "ADMIN")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Login with email + password (no username)."""

    ROLE_CHOICES = [("USER", "User"), ("ADMIN", "Admin")]

    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="USER")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    def __str__(self):
        return self.email

# ---------------------------------------------------------------------
# Choices (same values as the dataset / preprocess.py)
# ---------------------------------------------------------------------
GRADE_CHOICES = [(g, g) for g in "ABCDEFG"]
HOME_CHOICES = [
    ("RENT", "Rent"),
    ("OWN", "Own"),
    ("MORTGAGE", "Mortgage"),
    ("OTHER", "Other"),
]
YES_NO_CHOICES = [("N", "No"), ("Y", "Yes")]
RISK_CHOICES = [("Low", "Low"), ("Medium", "Medium"), ("High", "High")]


class LoanType(models.Model):
    """Loan purpose. `code` is the exact value the model was trained on."""

    code = models.CharField(max_length=30, unique=True)      # e.g. DEBTCONSOLIDATION
    name = models.CharField(max_length=60)                   # e.g. Debt Consolidation
    description = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class LoanApplication(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications"
    )
    loan_type = models.ForeignKey(
        LoanType, on_delete=models.PROTECT, related_name="applications"
    )

    full_name = models.CharField(max_length=100)
    age = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(18), MaxValueValidator(100)]
    )
    annual_income = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(1)]
    )
    employment_length = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(60)]
    )
    home_ownership = models.CharField(max_length=10, choices=HOME_CHOICES)
    loan_grade = models.CharField(max_length=1, choices=GRADE_CHOICES)
    loan_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(1)]
    )
    interest_rate = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(40)]
    )
    previous_default = models.CharField(max_length=1, choices=YES_NO_CHOICES, default="N")
    credit_history_length = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(60)]
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def loan_to_income(self):
        return round(float(self.loan_amount) / float(self.annual_income), 2)

    def __str__(self):
        return f"{self.full_name} - {self.loan_amount} ({self.created_at:%d-%m-%Y})"


class Prediction(models.Model):
    application = models.OneToOneField(
        LoanApplication, on_delete=models.CASCADE, related_name="prediction"
    )
    default_probability = models.FloatField()                # 0 to 1
    credit_score = models.PositiveSmallIntegerField()        # 300 to 900
    risk_level = models.CharField(max_length=6, choices=RISK_CHOICES)
    predicted_status = models.PositiveSmallIntegerField()    # 1 = Default, 0 = No Default
    model_name = models.CharField(max_length=60, default="Random Forest")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.risk_level} ({self.credit_score})"


class ModelInfo(models.Model):
    """Model performance, shown on the About / Model Info page."""

    model_name = models.CharField(max_length=60)
    accuracy = models.FloatField()
    precision = models.FloatField()
    recall = models.FloatField()
    f1_score = models.FloatField()
    roc_auc = models.FloatField()
    training_rows = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.model_name} (AUC {self.roc_auc:.3f})"


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} - {self.email}"


class ActivityLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
    )
    action = models.CharField(max_length=100)                # e.g. "Login", "New prediction"
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} - {self.created_at:%d-%m-%Y %H:%M}"