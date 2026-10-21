from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import LoanType
from .models import User


class BootstrapFormMixin:
    """Add Bootstrap classes to every field."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = css


class RegisterForm(BootstrapFormMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ("full_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["full_name"].label = "Full Name"
        self.fields["full_name"].widget.attrs.update(
            {"placeholder": "Enter your full name", "autofocus": True, "autocomplete": "name"}
        )

        self.fields["email"].label = "Email Address"
        self.fields["email"].widget.attrs.update(
            {"placeholder": "name@example.com", "autocomplete": "email"}
        )

        self.fields["password1"].label = "Password"
        self.fields["password1"].help_text = ""
        self.fields["password1"].widget.attrs.update(
            {"placeholder": "Create a strong password", "autocomplete": "new-password"}
        )

        self.fields["password2"].label = "Confirm Password"
        self.fields["password2"].help_text = ""
        self.fields["password2"].widget.attrs.update(
            {"placeholder": "Re-enter password", "autocomplete": "new-password"}
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class EmailLoginForm(BootstrapFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].label = "Email Address"
        self.fields["username"].widget = forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "name@example.com",
                "autocomplete": "email",
                "autofocus": True,
            }
        )

        self.fields["password"].widget.attrs.update(
            {"placeholder": "Enter your password", "autocomplete": "current-password"}
        )

class RiskCheckerForm(BootstrapFormMixin, forms.Form):
    person_age = forms.IntegerField(
        label="Age",
        min_value=18,
        max_value=100,
        widget=forms.NumberInput(attrs={"placeholder": "Enter your age"})
    )

    person_income = forms.DecimalField(
        label="Annual Income (₹)",
        min_value=1,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"placeholder": "e.g. 600000"})
    )

    person_emp_length = forms.FloatField(
        label="Employment Length (Years)",
        min_value=0,
        max_value=60,
        widget=forms.NumberInput(attrs={"placeholder": "e.g. 5"})
    )

    person_home_ownership = forms.ChoiceField(
        label="Home Ownership",
        choices=[
            ("RENT", "Rent"),
            ("OWN", "Own"),
            ("MORTGAGE", "Mortgage"),
            ("OTHER", "Other"),
        ]
    )

    loan_grade = forms.ChoiceField(
        label="Loan Grade",
        choices=[(grade, grade) for grade in "ABCDEFG"]
    )

    loan_amnt = forms.DecimalField(
        label="Loan Amount (₹)",
        min_value=1,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"placeholder": "e.g. 200000"})
    )

    loan_int_rate = forms.FloatField(
        label="Interest Rate (%)",
        min_value=0,
        max_value=40,
        widget=forms.NumberInput(attrs={
            "placeholder": "e.g. 12.5",
            "step": "0.01"
        })
    )

    cb_person_default_on_file = forms.ChoiceField(
        label="Previous Default on Record",
        choices=[("N", "No"), ("Y", "Yes")]
    )

    cb_person_cred_hist_length = forms.IntegerField(
        label="Credit History Length (Years)",
        min_value=0,
        max_value=60,
        widget=forms.NumberInput(attrs={"placeholder": "e.g. 5"})
    )

    loan_intent = forms.ChoiceField(
        label="Loan Purpose",
        choices=[
            ("DEBTCONSOLIDATION", "Debt Consolidation"),
            ("EDUCATION", "Education"),
            ("HOMEIMPROVEMENT", "Home Improvement"),
            ("MEDICAL", "Medical"),
            ("PERSONAL", "Personal"),
            ("VENTURE", "Venture"),
        ]
    )



class EditProfileForm(BootstrapFormMixin, forms.ModelForm):
    """Allow users to edit only their own name and email address."""

    class Meta:
        model = User
        fields = ("full_name", "email")
        widgets = {
            "full_name": forms.TextInput(attrs={
                "placeholder": "Enter your full name",
                "autocomplete": "name",
                "maxlength": "100",
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "name@example.com",
                "autocomplete": "email",
                "maxlength": "254",
            }),
        }
        labels = {
            "full_name": "Full Name",
            "email": "Email Address",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].help_text = "Use the name you want displayed on your account."
        self.fields["email"].help_text = "Your email address is used to sign in to RiskWise."

    def clean_full_name(self):
        full_name = self.cleaned_data["full_name"].strip()
        if not full_name:
            raise forms.ValidationError("Full name is required.")
        return full_name

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email
