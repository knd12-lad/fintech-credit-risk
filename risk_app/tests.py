"""
Automated Test Suite for RiskWise Credit Risk Prediction Platform.
Implements the 18 verified test specifications covering authentication,
profile management, form validation, ML prediction pipeline, database persistence,
access authorization, and error handling.
"""

import csv
from io import StringIO
import os
from pathlib import Path
import re
import tempfile
from unittest.mock import patch
from datetime import timedelta
from decimal import Decimal
from django.core.cache import cache
from django.core.management import call_command
from django.core import mail, signing
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from risk_app.models import LoanType, LoanApplication, Prediction, ContactMessage, ActivityLog
from risk_app.utils import needle_angle
from ml.predict import predict_credit_risk
from ml.explain import explain_prediction

User = get_user_model()



class RiskWiseMasterTestSuite(TestCase):
    """18-Test Verification Suite for RiskWise Project."""

    @classmethod
    def setUpTestData(cls):
        # 1. Create standard LoanTypes
        cls.loan_types_data = [
            ("EDUCATION", "Education", "Study fees"),
            ("MEDICAL", "Medical", "Medical expenses"),
            ("VENTURE", "Venture", "Business startup"),
            ("PERSONAL", "Personal", "General personal"),
            ("HOMEIMPROVEMENT", "Home Improvement", "Renovation"),
            ("DEBTCONSOLIDATION", "Debt Consolidation", "Consolidate debt"),
        ]
        cls.loan_types = {}
        for code, name, desc in cls.loan_types_data:
            cls.loan_types[code] = LoanType.objects.create(
                code=code, name=name, description=desc, is_active=True
            )

        # 2. Primary test user (Borrower)
        cls.user1 = User.objects.create_user(
            email="borrower1@example.com",
            password="StrongPassword123!",
            full_name="Alice Borrower",
            role="USER",
        )

        # 3. Secondary test user (Borrower 2 for isolation testing)
        cls.user2 = User.objects.create_user(
            email="borrower2@example.com",
            password="StrongPassword123!",
            full_name="Bob Borrower",
            role="USER",
        )

        # 4. Administrator user
        cls.admin_user = User.objects.create_superuser(
            email="admin@riskwise.test",
            password="AdminPassword123!",
            full_name="RiskWise Admin",
        )

        # 5. Seed an existing loan application & prediction for User 1
        cls.app1 = LoanApplication.objects.create(
            user=cls.user1,
            loan_type=cls.loan_types["EDUCATION"],
            full_name=cls.user1.full_name,
            age=26,
            annual_income=Decimal("75000.00"),
            employment_length=4.5,
            home_ownership="RENT",
            loan_grade="B",
            loan_amount=Decimal("15000.00"),
            interest_rate=11.5,
            previous_default="N",
            credit_history_length=4,
        )
        cls.pred1 = Prediction.objects.create(
            application=cls.app1,
            default_probability=0.1520,
            credit_score=809,
            risk_level="Low",
            predicted_status=0,
            model_name="Random Forest",
        )

    def setUp(self):
        self.client = Client()

    # -------------------------------------------------------------------------
    # TEST 1: Public pages return expected response
    # -------------------------------------------------------------------------
    def test_01_public_pages_return_expected_response(self):
        endpoints = [
            reverse("home"),
            reverse("about"),
            reverse("contact"),
            reverse("login"),
            reverse("register"),
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code,
                200,
                f"Expected status 200 for public URL {url}, got {response.status_code}",
            )

    # -------------------------------------------------------------------------
    # TEST 2: Registration works with valid data
    # -------------------------------------------------------------------------
    def test_02_registration_works_with_valid_data(self):
        payload = {
            "full_name": "Charlie Fresh",
            "email": "charlie@example.com",
            "password1": "SecurePass789#",
            "password2": "SecurePass789#",
        }
        response = self.client.post(reverse("register"), data=payload, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email="charlie@example.com").exists())
        user = User.objects.get(email="charlie@example.com")
        self.assertEqual(user.full_name, "Charlie Fresh")
        self.assertEqual(user.role, "USER")

    # -------------------------------------------------------------------------
    # TEST 3: Registration rejects invalid or duplicate data
    # -------------------------------------------------------------------------
    def test_03_registration_rejects_invalid_or_duplicate_data(self):
        # Duplicate email
        payload_dup = {
            "full_name": "Duplicate Alice",
            "email": "borrower1@example.com",
            "password1": "Password123#",
            "password2": "Password123#",
        }
        res_dup = self.client.post(reverse("register"), data=payload_dup)
        self.assertEqual(res_dup.status_code, 200)
        self.assertFormError(
            res_dup.context["form"], "email", "An account with this email already exists."
        )

        # Mismatched passwords
        payload_mismatch = {
            "full_name": "Mismatch Tester",
            "email": "mismatch@example.com",
            "password1": "Password123#",
            "password2": "DifferentPassword456#",
        }
        res_mis = self.client.post(reverse("register"), data=payload_mismatch)
        self.assertEqual(res_mis.status_code, 200)
        self.assertFalse(User.objects.filter(email="mismatch@example.com").exists())

    # -------------------------------------------------------------------------
    # TEST 4: Login accepts valid and rejects invalid credentials
    # -------------------------------------------------------------------------
    def test_04_login_accepts_valid_and_rejects_invalid(self):
        # Invalid credentials
        res_invalid = self.client.post(
            reverse("login"),
            {"username": "borrower1@example.com", "password": "WrongPassword!"},
        )
        self.assertEqual(res_invalid.status_code, 200)
        self.assertFalse(res_invalid.context["user"].is_authenticated)

        # Valid credentials
        res_valid = self.client.post(
            reverse("login"),
            {"username": "borrower1@example.com", "password": "StrongPassword123!"},
            follow=True,
        )
        self.assertEqual(res_valid.status_code, 200)
        self.assertTrue(res_valid.context["user"].is_authenticated)

    # -------------------------------------------------------------------------
    # TEST 5: Logout works
    # -------------------------------------------------------------------------
    def test_05_logout_works(self):
        self.client.force_login(self.user1)
        res_logout = self.client.post(reverse("logout"), follow=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertFalse(res_logout.context["user"].is_authenticated)

    # -------------------------------------------------------------------------
    # TEST 6: Protected pages require authentication
    # -------------------------------------------------------------------------
    def test_06_protected_pages_require_authentication(self):
        protected_urls = [
            reverse("risk_checker"),
            reverse("history"),
            reverse("profile"),
            reverse("edit_profile"),
            reverse("password_change"),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code,
                302,
                f"Expected redirect 302 for protected URL {url}",
            )
            self.assertIn(reverse("login"), response.url)

    # -------------------------------------------------------------------------
    # TEST 7: Profile functionality works
    # -------------------------------------------------------------------------
    def test_07_profile_functionality_works(self):
        self.client.force_login(self.user1)
        # View profile
        res_view = self.client.get(reverse("profile"))
        self.assertEqual(res_view.status_code, 200)

        # Edit profile
        res_edit = self.client.post(
            reverse("edit_profile"),
            {"full_name": "Alice Updated", "email": "alice_new@example.com"},
            follow=True,
        )
        self.assertEqual(res_edit.status_code, 200)
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.full_name, "Alice Updated")
        self.assertEqual(self.user1.email, "alice_new@example.com")

    # -------------------------------------------------------------------------
    # TEST 8: Password changes work correctly
    # -------------------------------------------------------------------------
    def test_08_password_changes_work_correctly(self):
        self.client.force_login(self.user2)
        payload = {
            "old_password": "StrongPassword123!",
            "new_password1": "NewStrongPass456#",
            "new_password2": "NewStrongPass456#",
        }
        res_change = self.client.post(reverse("password_change"), payload, follow=True)
        self.assertEqual(res_change.status_code, 200)
        # Verify can login with new password
        self.client.logout()
        res_login = self.client.post(
            reverse("login"),
            {"username": "borrower2@example.com", "password": "NewStrongPass456#"},
        )
        self.assertEqual(res_login.status_code, 302)

    # -------------------------------------------------------------------------
    # TEST 9: Contact form validation works
    # -------------------------------------------------------------------------
    def test_09_contact_form_validation(self):
        # Incomplete submission
        res_invalid = self.client.post(
            reverse("contact"),
            {"name": "Tester", "email": "tester@example.com", "subject": ""},
        )
        self.assertEqual(res_invalid.status_code, 200)
        self.assertFalse(ContactMessage.objects.filter(name="Tester").exists())

        # Valid submission
        res_valid = self.client.post(
            reverse("contact"),
            {
                "name": "Jane Query",
                "email": "jane@example.com",
                "subject": "Platform inquiry",
                "message": "Hello, how does the credit scoring model work?",
            },
            follow=True,
        )
        self.assertEqual(res_valid.status_code, 200)
        self.assertTrue(
            ContactMessage.objects.filter(email="jane@example.com").exists()
        )

    # -------------------------------------------------------------------------
    # TEST 10: Credit Risk Checker validates required fields
    # -------------------------------------------------------------------------
    def test_10_credit_risk_checker_validates_required_fields(self):
        self.client.force_login(self.user1)
        res_empty = self.client.post(reverse("risk_checker"), data={})
        self.assertEqual(res_empty.status_code, 200)
        self.assertFormError(
            res_empty.context["form"], "person_age", "This field is required."
        )
        self.assertFormError(
            res_empty.context["form"], "person_income", "This field is required."
        )

    # -------------------------------------------------------------------------
    # TEST 11: Invalid numeric and categorical inputs handled safely
    # -------------------------------------------------------------------------
    def test_11_invalid_numeric_and_categorical_inputs(self):
        self.client.force_login(self.user1)
        bad_payload = {
            "person_age": 15,  # Min 18
            "person_income": -5000,  # Min 1
            "person_emp_length": 80,  # Max 60
            "person_home_ownership": "MANSION",  # Invalid choice
            "loan_grade": "Z",  # Invalid choice
            "loan_amnt": 0,  # Min 1
            "loan_int_rate": 55,  # Max 40
            "cb_person_default_on_file": "MAYBE",  # Invalid choice
            "cb_person_cred_hist_length": -2,
            "loan_intent": "GAMBLING",  # Invalid choice
        }
        res = self.client.post(reverse("risk_checker"), data=bad_payload)
        self.assertEqual(res.status_code, 200)
        # Ensure form caught the violations
        form = res.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("person_age", form.errors)
        self.assertIn("person_income", form.errors)

    # -------------------------------------------------------------------------
    # TEST 12: Prediction results returned in expected structure
    # -------------------------------------------------------------------------
    def test_12_prediction_results_structure(self):
        valid_input = {
            "person_age": 28,
            "person_income": 65000,
            "person_emp_length": 5.0,
            "loan_amnt": 12000,
            "loan_int_rate": 10.5,
            "cb_person_cred_hist_length": 6,
            "loan_grade": "B",
            "cb_person_default_on_file": "N",
            "person_home_ownership": "MORTGAGE",
            "loan_intent": "PERSONAL",
        }
        res = predict_credit_risk(valid_input)
        self.assertIsInstance(res, dict)
        self.assertIn("prediction", res)
        self.assertIn("default_probability", res)
        self.assertIn("credit_score", res)
        self.assertIn("risk_level", res)

        self.assertIn(res["prediction"], [0, 1])
        self.assertTrue(0.0 <= res["default_probability"] <= 1.0)
        self.assertTrue(300 <= res["credit_score"] <= 900)
        self.assertIn(res["risk_level"], ["Low", "Medium", "High"])

    # -------------------------------------------------------------------------
    # TEST 13: Predictions saved correctly in database
    # -------------------------------------------------------------------------
    def test_13_predictions_saved_correctly(self):
        self.client.force_login(self.user1)
        valid_post = {
            "person_age": 30,
            "person_income": "85000",
            "person_emp_length": 6,
            "person_home_ownership": "OWN",
            "loan_grade": "A",
            "loan_amnt": "10000",
            "loan_int_rate": 8.5,
            "cb_person_default_on_file": "N",
            "cb_person_cred_hist_length": 7,
            "loan_intent": "VENTURE",
        }
        initial_apps = LoanApplication.objects.count()
        initial_preds = Prediction.objects.count()

        res = self.client.post(reverse("risk_checker"), data=valid_post)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(LoanApplication.objects.count(), initial_apps + 1)
        self.assertEqual(Prediction.objects.count(), initial_preds + 1)

        latest_app = LoanApplication.objects.first()
        self.assertEqual(latest_app.user, self.user1)
        self.assertEqual(latest_app.loan_grade, "A")
        self.assertIsNotNone(latest_app.prediction)

    # -------------------------------------------------------------------------
    # TEST 14: Prediction history displays correct records
    # -------------------------------------------------------------------------
    def test_14_prediction_history_displays_correct_records(self):
        self.client.force_login(self.user1)
        res = self.client.get(reverse("history"))
        self.assertEqual(res.status_code, 200)
        self.assertIn(self.app1, res.context["applications"])

    # -------------------------------------------------------------------------
    # TEST 15: Users cannot access other users' private predictions
    # -------------------------------------------------------------------------
    def test_15_users_cannot_access_other_users_private_predictions(self):
        # User 2 tries to view User 1's application result
        self.client.force_login(self.user2)
        res = self.client.get(reverse("result", kwargs={"application_id": self.app1.id}))
        self.assertEqual(
            res.status_code,
            404,
            "User 2 must receive 404 when accessing User 1's private prediction",
        )

    # -------------------------------------------------------------------------
    # TEST 16: Admin-only functionality is properly restricted
    # -------------------------------------------------------------------------
    def test_16_admin_only_functionality_restricted(self):
        # Regular user cannot access Django admin
        self.client.force_login(self.user1)
        self.client.cookies["rw_admin_sessionid"] = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        res_regular = self.client.get(reverse("admin:index"))
        self.assertIn(
            res_regular.status_code,
            [302, 403],
            "Non-staff user must be redirected or rejected from admin area",
        )

        # Admin user can access Django admin
        self.client.force_login(self.admin_user)
        self.client.cookies["rw_admin_sessionid"] = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        res_admin = self.client.get(reverse("admin:index"))
        self.assertEqual(res_admin.status_code, 200)

    # -------------------------------------------------------------------------
    # TEST 17: Invalid result IDs are handled safely
    # -------------------------------------------------------------------------
    def test_17_invalid_result_ids_handled_safely(self):
        self.client.force_login(self.user1)
        non_existent_id = 999999
        res = self.client.get(
            reverse("result", kwargs={"application_id": non_existent_id})
        )
        self.assertEqual(res.status_code, 404)

    # -------------------------------------------------------------------------
    # TEST 18: Model-loading or prediction errors handled appropriately
    # -------------------------------------------------------------------------
    def test_18_model_loading_or_prediction_errors_handled(self):
        self.client.force_login(self.user1)
        valid_post = {
            "person_age": 32,
            "person_income": "60000",
            "person_emp_length": 5,
            "person_home_ownership": "RENT",
            "loan_grade": "B",
            "loan_amnt": "10000",
            "loan_int_rate": 11.0,
            "cb_person_default_on_file": "N",
            "cb_person_cred_hist_length": 5,
            "loan_intent": "PERSONAL",
        }
        with patch(
            "risk_app.views.predict_credit_risk",
            side_effect=RuntimeError("Simulated Model Failure"),
        ):
            res = self.client.post(reverse("risk_checker"), data=valid_post)
            # Must render the risk_checker page gracefully with an error message, not 500
            self.assertEqual(res.status_code, 200)
            self.assertTemplateUsed(res, "risk_checker.html")

    # -------------------------------------------------------------------------
    # TEST 19: Demo prediction generation creates representative, unbiased sample
    # -------------------------------------------------------------------------
    def test_19_generate_demo_predictions_distribution(self):
        """
        Verify that generating 200 demo rows gives more than 2 distinct age
        groups and High-risk share below 35%.
        """
        out = StringIO()
        call_command(
            "generate_demo_predictions",
            limit=200,
            execute=True,
            reset_demo=True,
            stdout=out,
        )

        demo_apps = LoanApplication.objects.filter(
            full_name__startswith="Demo Applicant #"
        )
        self.assertEqual(demo_apps.count(), 200)

        def categorize_age(age):
            if age <= 25:
                return "18-25"
            elif age <= 35:
                return "26-35"
            elif age <= 50:
                return "36-50"
            return "51+"

        age_groups = {categorize_age(app.age) for app in demo_apps}
        self.assertGreater(
            len(age_groups),
            2,
            f"Expected more than 2 distinct age groups, got {len(age_groups)}: {age_groups}",
        )

        demo_preds = Prediction.objects.filter(application__in=demo_apps)
        high_risk_count = demo_preds.filter(risk_level="High").count()
        high_risk_pct = (high_risk_count / demo_preds.count()) * 100
        self.assertLess(
            high_risk_pct,
            35.0,
            f"Expected High-risk share below 35%, got {high_risk_pct:.1f}%",
        )

    # -------------------------------------------------------------------------
    # TEST 20: Power BI export data quality and privacy validation
    # -------------------------------------------------------------------------
    def test_20_export_powerbi_dataset_sanitization_and_tiers(self):
        """
        Verify that exported Power BI dataset has no empty income_tier values,
        all income_tier values contain a '$', and no email-like strings exist in the CSV.
        """
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv") as tmp:
            tmp_path = tmp.name

        try:
            out = StringIO()
            call_command("export_powerbi_dataset", output=tmp_path, stdout=out)

            with open(tmp_path, mode="r", encoding="utf-8") as f:
                content = f.read()

            # 1. No email-like string exists in the entire CSV
            email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
            emails_found = email_pattern.findall(content)
            self.assertEqual(
                emails_found,
                [],
                f"Privacy violation: Found email addresses in exported CSV: {emails_found}",
            )

            # 2. Verify income_tier values
            valid_income_tiers = {
                "< $25k",
                "$25k - $50k",
                "$50k - $75k",
                "$75k - $100k",
                "> $100k",
            }
            reader = csv.DictReader(content.splitlines())
            rows = list(reader)
            self.assertGreater(len(rows), 0, "Exported dataset should contain rows")

            for idx, row in enumerate(rows, start=1):
                income_tier = row.get("income_tier", "").strip()
                self.assertTrue(
                    income_tier,
                    f"Row {idx} (ID {row.get('application_id')}) has an empty income_tier",
                )
                self.assertIn(
                    "$",
                    income_tier,
                    f"Row {idx} income_tier '{income_tier}' lacks a '$'",
                )
                self.assertIn(
                    income_tier,
                    valid_income_tiers,
                    f"Row {idx} income_tier '{income_tier}' is not in valid tiers",
                )

            # Also check the repository artifact file if it exists
            repo_csv = Path(settings.BASE_DIR) / "powerbi" / "data" / "riskwise_powerbi_dataset.csv"
            if repo_csv.exists():
                with open(repo_csv, mode="r", encoding="utf-8") as rf:
                    repo_content = rf.read()
                self.assertEqual(email_pattern.findall(repo_content), [])
                for row in csv.DictReader(repo_content.splitlines()):
                    tier = row.get("income_tier", "").strip()
                    self.assertTrue(tier)
                    self.assertIn("$", tier)
                    self.assertIn(tier, valid_income_tiers)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # -------------------------------------------------------------------------
    # TEST 21: Staff user can access /admin/risk_app/ app index
    # -------------------------------------------------------------------------
    def test_21_admin_app_index_page(self):
        """
        Verify that a staff user GET /admin/risk_app/ returns 200
        and the content contains 'Loan applications'.
        """
        self.client.force_login(self.admin_user)
        self.client.cookies["rw_admin_sessionid"] = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        res = self.client.get("/admin/risk_app/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Loan applications")

    # -------------------------------------------------------------------------
    # TEST 22: Error pages and educational disclaimer
    # -------------------------------------------------------------------------
    def test_22_error_pages_and_educational_disclaimer(self):
        """
        Verify that:
        1. 404 response renders custom 404.html template.
        2. Educational disclaimer does not appear in footer, risk checker, or results.
        """
        disclaimer_text = (
            "RiskWise is an educational/demo project. Results are model estimates "
            "and must not be used for real lending decisions."
        )

        # 404 test
        res_404 = self.client.get("/nonexistent-page-404-not-found/")
        self.assertEqual(res_404.status_code, 404)
        self.assertTemplateUsed(res_404, "404.html")
        self.assertContains(res_404, "Page Not Found", status_code=404)
        self.assertContains(res_404, "Back to Home", status_code=404)

        # Disclaimer not on homepage (footer include)
        res_home = self.client.get(reverse("home"))
        self.assertEqual(res_home.status_code, 200)
        self.assertNotContains(res_home, disclaimer_text)

        # Disclaimer not on risk checker page
        self.client.force_login(self.user1)
        res_checker = self.client.get(reverse("risk_checker"))
        self.assertEqual(res_checker.status_code, 200)
        self.assertNotContains(res_checker, disclaimer_text)

        # Disclaimer not on prediction result page
        res_result = self.client.get(reverse("result", kwargs={"application_id": self.app1.pk}))
        self.assertEqual(res_result.status_code, 200)
        self.assertNotContains(res_result, disclaimer_text)

    # -------------------------------------------------------------------------
    # TEST 23: Contact form sends email with graceful fallback
    # -------------------------------------------------------------------------
    def test_23_contact_form_email_dispatch_and_fallback(self):
        """
        Verify that valid contact submission triggers an email notification,
        and that email failure does not prevent DB persistence or break the form.
        """
        mail.outbox.clear()
        res = self.client.post(
            reverse("contact"),
            {
                "name": "Alex Sender",
                "email": "alex@example.com",
                "subject": "Inquiry about RiskWise",
                "message": "Testing the automated notification email system.",
            },
            follow=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(ContactMessage.objects.filter(email="alex@example.com").exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("[RiskWise Contact] Inquiry about RiskWise", mail.outbox[0].subject)
        self.assertIn("Alex Sender", mail.outbox[0].body)

        # Test failure fallback when send_mail raises an Exception
        with patch("risk_app.views.send_mail", side_effect=RuntimeError("SMTP connection timed out")):
            res_fail = self.client.post(
                reverse("contact"),
                {
                    "name": "Fallback User",
                    "email": "fallback@example.com",
                    "subject": "Testing Failure Resilience",
                    "message": "Even if mail server fails, DB must save.",
                },
                follow=True,
            )
            self.assertEqual(res_fail.status_code, 200)
            self.assertTrue(ContactMessage.objects.filter(email="fallback@example.com").exists())
            self.assertContains(res_fail, "Your message has been submitted successfully!")

    # -------------------------------------------------------------------------
    # TEST 24: Staff login on admin does not authenticate public website
    # -------------------------------------------------------------------------
    def test_24_staff_login_admin_does_not_authenticate_website(self):
        """
        4.4a: Staff login through the admin login URL, then GET '/' ->
        context user is NOT authenticated on the public website.
        """
        client = Client()
        login_res = client.post(
            "/admin/login/",
            {"username": self.admin_user.email, "password": "AdminPassword123!"},
        )
        self.assertEqual(login_res.status_code, 302)
        self.assertIn("rw_admin_sessionid", client.cookies)

        res_home = client.get(reverse("home"))
        self.assertEqual(res_home.status_code, 200)
        self.assertFalse(res_home.context["user"].is_authenticated)

    # -------------------------------------------------------------------------
    # TEST 25: Dual portal sessions coexist simultaneously in same client
    # -------------------------------------------------------------------------
    def test_25_dual_portal_sessions_coexist_in_same_client(self):
        """
        4.4b: Normal user logged in on website and staff logged in on admin
        in the same client -> both stay logged in on their own side.
        """
        client = Client()
        # Normal user logs in on website
        user_login = client.post(
            reverse("login"),
            {"username": self.user1.email, "password": "StrongPassword123!"},
        )
        self.assertEqual(user_login.status_code, 302)
        self.assertIn(settings.SESSION_COOKIE_NAME, client.cookies)

        # Staff logs in on admin
        admin_login = client.post(
            "/admin/login/",
            {"username": self.admin_user.email, "password": "AdminPassword123!"},
        )
        self.assertEqual(admin_login.status_code, 302)
        self.assertIn("rw_admin_sessionid", client.cookies)

        # Website request -> user1 is authenticated
        res_home = client.get(reverse("home"))
        self.assertEqual(res_home.status_code, 200)
        self.assertTrue(res_home.context["user"].is_authenticated)
        self.assertEqual(res_home.context["user"].email, self.user1.email)

        # Admin request -> admin_user is authenticated
        res_admin = client.get("/admin/")
        self.assertEqual(res_admin.status_code, 200)
        self.assertTrue(res_admin.context["user"].is_authenticated)
        self.assertEqual(res_admin.context["user"].email, self.admin_user.email)

    # -------------------------------------------------------------------------
    # TEST 26: Logout on one side does not log out the other side
    # -------------------------------------------------------------------------
    def test_26_logout_isolation_between_admin_and_website(self):
        """
        4.4c: Logout on one side does not log out the other side.
        """
        client = Client()
        client.post(
            reverse("login"),
            {"username": self.user1.email, "password": "StrongPassword123!"},
        )
        client.post(
            "/admin/login/",
            {"username": self.admin_user.email, "password": "AdminPassword123!"},
        )

        # Logout from website
        logout_site = client.post(reverse("logout"))
        self.assertIn(logout_site.status_code, (200, 302))

        # Website should now be logged out
        res_home = client.get(reverse("home"))
        self.assertFalse(res_home.context["user"].is_authenticated)

        # Admin must STILL be logged in!
        res_admin = client.get("/admin/")
        self.assertEqual(res_admin.status_code, 200)
        self.assertTrue(res_admin.context["user"].is_authenticated)
        self.assertEqual(res_admin.context["user"].email, self.admin_user.email)

        # Now log user back in, and logout from admin
        client.post(
            reverse("login"),
            {"username": self.user1.email, "password": "StrongPassword123!"},
        )
        logout_admin = client.post("/admin/logout/")
        self.assertIn(logout_admin.status_code, (200, 302))

        # Admin should now redirect to login or be logged out
        res_admin_after = client.get("/admin/")
        self.assertIn(res_admin_after.status_code, (200, 302))
        if res_admin_after.status_code == 200 and "user" in res_admin_after.context:
            self.assertFalse(res_admin_after.context["user"].is_authenticated)

        # Website user must STILL be logged in!
        res_home_after = client.get(reverse("home"))
        self.assertTrue(res_home_after.context["user"].is_authenticated)
        self.assertEqual(res_home_after.context["user"].email, self.user1.email)

    # -------------------------------------------------------------------------
    # TEST 27: Session cookie names isolation
    # -------------------------------------------------------------------------
    def test_27_session_cookie_names_isolation(self):
        """
        4.4d: The admin response sets 'rw_admin_sessionid'; the website response
        sets the normal session cookie, never the other way around.
        """
        admin_client = Client()
        admin_res = admin_client.post(
            "/admin/login/",
            {"username": self.admin_user.email, "password": "AdminPassword123!"},
        )
        self.assertEqual(admin_res.status_code, 302)
        self.assertIn("rw_admin_sessionid", admin_res.cookies)
        self.assertNotIn(settings.SESSION_COOKIE_NAME, admin_res.cookies)

        user_client = Client()
        user_res = user_client.post(
            reverse("login"),
            {"username": self.user1.email, "password": "StrongPassword123!"},
        )
        self.assertEqual(user_res.status_code, 302)
        self.assertIn(settings.SESSION_COOKIE_NAME, user_res.cookies)
        self.assertNotIn("rw_admin_sessionid", user_res.cookies)

    # -------------------------------------------------------------------------
    # TEST 28: needle_angle formula and clamping
    # -------------------------------------------------------------------------
    def test_28_needle_angle_math_and_clamping(self):
        """
        1.5: needle_angle(300)=0, (600)=90, (900)=180, values outside 300..900 are clamped.
        """
        self.assertEqual(needle_angle(300), 0)
        self.assertEqual(needle_angle(600), 90)
        self.assertEqual(needle_angle(900), 180)
        self.assertEqual(needle_angle(200), 0)
        self.assertEqual(needle_angle(1200), 180)
        self.assertEqual(needle_angle(828), 158.4)

    # -------------------------------------------------------------------------
    # TEST 29: Anonymous user sees sample hero card
    # -------------------------------------------------------------------------
    def test_29_anonymous_home_shows_sample(self):
        """
        1.5: Anonymous home shows "Sample", sample score 828, and sample disclaimer.
        """
        res = self.client.get(reverse("home"))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context["hero"]["is_sample"])
        self.assertEqual(res.context["hero"]["score"], 828)
        self.assertFalse(res.context["has_history"])
        self.assertContains(res, "Sample")
        self.assertContains(res, "828")
        self.assertContains(res, "Sample result for illustration only.")
        self.assertNotContains(res, "Your latest result")

    # -------------------------------------------------------------------------
    # TEST 30: Authenticated user without predictions sees sample and first check link
    # -------------------------------------------------------------------------
    def test_30_user_without_prediction_sees_sample_and_first_check_link(self):
        """
        1.5: A user with no prediction sees the sample plus the "first check" link.
        """
        # User 2 has no prediction
        self.client.force_login(self.user2)
        res = self.client.get(reverse("home"))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context["hero"]["is_sample"])
        self.assertFalse(res.context["has_history"])
        self.assertContains(res, "Sample")
        self.assertContains(res, "Run your first check to see your own score here.")
        self.assertContains(res, reverse("risk_checker"))
        self.assertNotContains(res, "Your latest result")

    # -------------------------------------------------------------------------
    # TEST 31: Authenticated user with predictions sees most recent score
    # -------------------------------------------------------------------------
    def test_31_user_with_predictions_sees_most_recent_score_and_latest_result(self):
        """
        1.5: A user with predictions sees their MOST RECENT score and "Your latest result".
        """
        # User 1 already has self.pred1 (score 809). Add a newer prediction.
        app2 = LoanApplication.objects.create(
            user=self.user1,
            loan_type=self.loan_types["MEDICAL"],
            full_name=self.user1.full_name,
            age=28,
            annual_income=Decimal("85000.00"),
            employment_length=6.0,
            home_ownership="OWN",
            loan_grade="A",
            loan_amount=Decimal("12000.00"),
            interest_rate=7.5,
            previous_default="N",
            credit_history_length=6,
        )
        pred2 = Prediction.objects.create(
            application=app2,
            default_probability=0.07,
            credit_score=865,
            risk_level="Low",
            predicted_status=0,
            model_name="Random Forest",
        )

        self.client.force_login(self.user1)
        res = self.client.get(reverse("home"))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.context["hero"]["is_sample"])
        self.assertTrue(res.context["has_history"])
        self.assertEqual(res.context["hero"]["score"], 865)
        self.assertEqual(res.context["hero"]["application_id"], app2.id)
        self.assertEqual(res.context["hero"]["needle_angle"], needle_angle(865))
        self.assertContains(res, "Your latest result")
        self.assertContains(res, "865")
        self.assertContains(res, "Based on your assessment on")
        self.assertContains(res, "View full result")
        self.assertContains(res, reverse("result", args=[app2.id]))
        self.assertContains(res, f"--needle-angle: {needle_angle(865)}deg")

    # -------------------------------------------------------------------------
    # TEST 32: User isolation - User A never sees User B's score
    # -------------------------------------------------------------------------
    def test_32_user_a_never_sees_user_b_score(self):
        """
        1.5: User A never sees User B's score.
        """
        # Create a specific prediction for User 2
        app_b = LoanApplication.objects.create(
            user=self.user2,
            loan_type=self.loan_types["VENTURE"],
            full_name=self.user2.full_name,
            age=40,
            annual_income=Decimal("50000.00"),
            employment_length=3.0,
            home_ownership="RENT",
            loan_grade="E",
            loan_amount=Decimal("30000.00"),
            interest_rate=21.0,
            previous_default="Y",
            credit_history_length=3,
        )
        pred_b = Prediction.objects.create(
            application=app_b,
            default_probability=0.72,
            credit_score=420,
            risk_level="High",
            predicted_status=1,
            model_name="Random Forest",
        )

        # Login User 2: sees 420
        self.client.force_login(self.user2)
        res_user2 = self.client.get(reverse("home"))
        self.assertEqual(res_user2.context["hero"]["score"], 420)
        self.assertEqual(res_user2.context["hero"]["risk_level_key"], "high")
        self.assertEqual(res_user2.context["hero"]["risk_label"], "High Risk")

        # Login User 1: sees User 1's score (809 from setUpTestData), NOT User 2's (420)
        self.client.force_login(self.user1)
        res_user1 = self.client.get(reverse("home"))
        self.assertEqual(res_user1.context["hero"]["score"], 809)
        self.assertNotEqual(res_user1.context["hero"]["score"], 420)

    # -------------------------------------------------------------------------
    # TEST 33: Admin view-as picker page permissions (2.8 a)
    # -------------------------------------------------------------------------
    def test_33_admin_view_as_picker_permissions(self):
        """
        2.8 a: A superuser opens the picker (200); a normal user gets 403 or a redirect.
        """
        # Superuser opens picker
        client_admin = Client()
        client_admin.post(
            "/admin/login/",
            {"username": self.admin_user.email, "password": "AdminPassword123!"},
        )
        res_admin = client_admin.get("/admin/view-as/")
        self.assertEqual(res_admin.status_code, 200)
        self.assertContains(res_admin, "View Website as User")
        self.assertIn("page_obj", res_admin.context)
        self.assertContains(res_admin, self.user1.email)

        # Normal user gets 403 or redirect
        client_user = Client()
        client_user.post(
            reverse("login"),
            {"username": self.user1.email, "password": "StrongPassword123!"},
        )
        res_user = client_user.get("/admin/view-as/")
        self.assertIn(res_user.status_code, (403, 302))

        # Anonymous visitor gets redirect or 403
        res_anon = Client().get("/admin/view-as/")
        self.assertIn(res_anon.status_code, (403, 302))

    # -------------------------------------------------------------------------
    # TEST 34: Full view-as flow (2.8 b)
    # -------------------------------------------------------------------------
    def test_34_view_as_full_flow(self):
        """
        2.8 b: Full flow: admin start -> enter -> home shows the banner and
        the TARGET's latest score; the admin session cookie is untouched.
        """
        client = Client()
        client.post(
            "/admin/login/",
            {"username": self.admin_user.email, "password": "AdminPassword123!"},
        )
        self.assertIn("rw_admin_sessionid", client.cookies)
        admin_cookie_val = client.cookies["rw_admin_sessionid"].value

        # Admin start
        res_start = client.post(f"/admin/view-as/{self.user1.pk}/start/")
        self.assertEqual(res_start.status_code, 303)
        redirect_url = res_start["Location"]
        self.assertIn("/view-as/enter/?t=", redirect_url)

        # Enter view-as (non-admin route)
        res_enter = client.get(redirect_url)
        self.assertEqual(res_enter.status_code, 302)
        self.assertEqual(res_enter["Location"], reverse("home"))

        # Admin session cookie must be completely untouched
        self.assertEqual(client.cookies["rw_admin_sessionid"].value, admin_cookie_val)

        # GET Home page: banner and TARGET's latest score must display
        res_home = client.get(reverse("home"))
        self.assertEqual(res_home.status_code, 200)
        self.assertContains(res_home, "Admin view: you are seeing RiskWise as")
        self.assertContains(res_home, self.user1.email)
        self.assertContains(res_home, "This session is read-only.")
        self.assertContains(res_home, "Exit and return to admin")
        self.assertFalse(res_home.context["hero"]["is_sample"])
        self.assertEqual(res_home.context["hero"]["score"], self.pred1.credit_score)

    # -------------------------------------------------------------------------
    # TEST 35: View-as read-only middleware blocks mutations (2.8 c)
    # -------------------------------------------------------------------------
    def test_35_view_as_read_only_blocks_mutations(self):
        """
        2.8 c: During view-as, POST to the risk checker creates NO LoanApplication,
        and the profile edit, contact form, and normal logout POSTs are blocked.
        """
        client = Client()
        client.post(
            "/admin/login/",
            {"username": self.admin_user.email, "password": "AdminPassword123!"},
        )
        res_start = client.post(f"/admin/view-as/{self.user1.pk}/start/")
        client.get(res_start["Location"])

        # 1. POST to risk checker
        app_count_before = LoanApplication.objects.count()
        res_risk = client.post(reverse("risk_checker"), {
            "loan_type": self.loan_types["EDUCATION"].pk,
            "full_name": "Blocked Assessment",
            "age": 30,
            "annual_income": "90000.00",
            "employment_length": 6.0,
            "home_ownership": "OWN",
            "loan_grade": "A",
            "loan_amount": "20000.00",
            "interest_rate": 7.0,
            "previous_default": "N",
            "credit_history_length": 6,
        })
        self.assertEqual(res_risk.status_code, 302)
        self.assertEqual(LoanApplication.objects.count(), app_count_before)

        # 2. POST to edit profile
        name_before = self.user1.full_name
        res_profile = client.post(reverse("edit_profile"), {"full_name": "Tampered Name"})
        self.assertEqual(res_profile.status_code, 302)
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.full_name, name_before)

        # 3. POST to contact form
        contact_count_before = ContactMessage.objects.count()
        res_contact = client.post(reverse("contact"), {
            "name": "Target",
            "email": "target@example.com",
            "subject": "Blocked Message",
            "message": "This message should never be saved.",
        })
        self.assertEqual(res_contact.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), contact_count_before)

        # 4. Normal /logout/ is also blocked
        res_logout = client.post(reverse("logout"))
        self.assertEqual(res_logout.status_code, 302)
        res_check = client.get(reverse("home"))
        self.assertTrue(res_check.context["user"].is_authenticated)

    # -------------------------------------------------------------------------
    # TEST 36: View-as exit flow and activity log (2.8 d)
    # -------------------------------------------------------------------------
    def test_36_view_as_exit_flow(self):
        """
        2.8 d: Exit: website session logged out, admin session still logged in,
        ActivityLog has both started and ended entries.
        """
        client = Client()
        client.post(
            "/admin/login/",
            {"username": self.admin_user.email, "password": "AdminPassword123!"},
        )
        res_start = client.post(f"/admin/view-as/{self.user1.pk}/start/")
        client.get(res_start["Location"])

        # Exit view-as
        res_exit = client.post(reverse("view_as_exit"))
        self.assertEqual(res_exit.status_code, 302)
        self.assertEqual(res_exit["Location"], "/admin/")

        # Website session must be logged out
        res_home = client.get(reverse("home"))
        self.assertFalse(res_home.context["user"].is_authenticated)

        # Admin session must still be logged in
        res_admin = client.get("/admin/")
        self.assertEqual(res_admin.status_code, 200)
        self.assertTrue(res_admin.context["user"].is_authenticated)
        self.assertEqual(res_admin.context["user"].email, self.admin_user.email)

        # ActivityLog has both started and ended entries
        self.assertTrue(
            ActivityLog.objects.filter(action="Admin view-as started", user=self.admin_user).exists()
        )
        self.assertTrue(
            ActivityLog.objects.filter(action="Admin view-as ended", user=self.admin_user).exists()
        )

    # -------------------------------------------------------------------------
    # TEST 37: Target rules - admin, staff, inactive, self rejected (2.8 e)
    # -------------------------------------------------------------------------
    def test_37_view_as_target_rules_rejected(self):
        """
        2.8 e: Target rules: admin, staff, inactive and self targets are rejected.
        """
        client = Client()
        client.post(
            "/admin/login/",
            {"username": self.admin_user.email, "password": "AdminPassword123!"},
        )

        staff_user = User.objects.create_user(
            email="staff_test@example.com",
            password="StaffPassword123!",
            role="USER",
            is_staff=True,
        )
        inactive_user = User.objects.create_user(
            email="inactive_test@example.com",
            password="InactivePassword123!",
            role="USER",
            is_active=False,
        )
        other_admin = User.objects.create_user(
            email="other_admin_test@example.com",
            password="OtherAdmin123!",
            role="ADMIN",
            is_staff=True,
        )

        for invalid_target in [self.admin_user, staff_user, inactive_user, other_admin]:
            res_start = client.post(f"/admin/view-as/{invalid_target.pk}/start/")
            self.assertEqual(res_start.status_code, 302)
            self.assertEqual(res_start["Location"], reverse("admin:view_as"))

            # Direct token entry rejection
            tok = signing.dumps(
                {"admin": self.admin_user.pk, "target": invalid_target.pk},
                salt="rw-view-as",
            )
            res_enter = client.get(f"/view-as/enter/?t={tok}")
            self.assertEqual(res_enter.status_code, 403)

    # -------------------------------------------------------------------------
    # TEST 38: Token security and validation (2.8 f)
    # -------------------------------------------------------------------------
    def test_38_view_as_token_validation_tests(self):
        """
        2.8 f: Token tests: expired token, tampered token, token without the admin
        cookie, and token with a different admin's cookie are all rejected.
        """
        client = Client()
        client.post(
            "/admin/login/",
            {"username": self.admin_user.email, "password": "AdminPassword123!"},
        )

        valid_tok = signing.dumps(
            {"admin": self.admin_user.pk, "target": self.user1.pk},
            salt="rw-view-as",
        )

        # 1. Tampered token
        res_tampered = client.get("/view-as/enter/?t=tampered:token:signature")
        self.assertEqual(res_tampered.status_code, 403)

        # 2. Expired token
        with patch("django.core.signing.loads", side_effect=signing.SignatureExpired("Expired")):
            res_expired = client.get(f"/view-as/enter/?t={valid_tok}")
            self.assertEqual(res_expired.status_code, 403)

        # 3. Token without admin cookie
        client_no_cookie = Client()
        res_no_cookie = client_no_cookie.get(f"/view-as/enter/?t={valid_tok}")
        self.assertEqual(res_no_cookie.status_code, 403)

        # 4. Token with a different admin's cookie
        other_admin = User.objects.create_superuser(
            email="admin2_tok@riskwise.test",
            password="AdminPassword123!",
            full_name="Admin Two",
        )
        client_diff_admin = Client()
        client_diff_admin.post(
            "/admin/login/",
            {"username": other_admin.email, "password": "AdminPassword123!"},
        )
        res_diff_admin = client_diff_admin.get(f"/view-as/enter/?t={valid_tok}")
        self.assertEqual(res_diff_admin.status_code, 403)

    # -------------------------------------------------------------------------
    # TEST 39: Target last_login and ActivityLog preserved (2.8 g)
    # -------------------------------------------------------------------------
    def test_39_view_as_target_last_login_and_activity_log_preserved(self):
        """
        2.8 g: The target's last_login is unchanged after the flow and no
        "Login" ActivityLog row was created for the target.
        """
        fixed_time = timezone.now() - timedelta(days=5)
        self.user1.last_login = fixed_time
        self.user1.save(update_fields=["last_login"])

        client = Client()
        client.post(
            "/admin/login/",
            {"username": self.admin_user.email, "password": "AdminPassword123!"},
        )
        res_start = client.post(f"/admin/view-as/{self.user1.pk}/start/")
        res_enter = client.get(res_start["Location"])
        self.assertEqual(res_enter.status_code, 302)

        self.user1.refresh_from_db()
        self.assertEqual(self.user1.last_login, fixed_time)

        # No "Login" ActivityLog created for the target
        target_login_logs = ActivityLog.objects.filter(
            user=self.user1, action__icontains="Login"
        )
        self.assertEqual(target_login_logs.count(), 0)

    # -------------------------------------------------------------------------
    # TEST 40: Shapley explainability suite (additivity, determinism, risk, page)
    # -------------------------------------------------------------------------
    def test_40_shapley_explainability_suite(self):
        """
        Phase 11 Task 1.5:
        - Additivity: sum of the 10 phi values equals applicant_prob - baseline_prob within 1e-6
        - Determinism: two calls give identical output
        - High-risk sample: person_income or loan_grade in top 2 factors, both "hurt"
        - Strong profile: net helpful impact
        - Result page: returns 200 and contains 'Why this score?'
        """
        high_risk_data = {
            "person_age": 23,
            "person_income": 18000,
            "person_emp_length": 0,
            "person_home_ownership": "RENT",
            "loan_intent": "MEDICAL",
            "loan_grade": "D",
            "loan_amnt": 15000,
            "loan_int_rate": 16.5,
            "cb_person_default_on_file": "Y",
            "cb_person_cred_hist_length": 2,
        }

        # 1. Determinism
        res1 = explain_prediction(high_risk_data)
        res2 = explain_prediction(high_risk_data)
        self.assertEqual(res1, res2)

        # 2. Additivity: sum of 10 phi values equals applicant_prob - baseline_prob within 1e-6
        phis = res1["shapley_values"]
        self.assertEqual(len(phis), 10)
        phi_sum = sum(phis.values())
        prob_diff = res1["applicant_probability"] - res1["baseline_probability"]
        self.assertAlmostEqual(phi_sum, prob_diff, places=6)

        # 3. High-risk sample: person_income or loan_grade in top 2 factors and both hurt
        top_2_fields = [f["field"] for f in res1["factors"][:2]]
        self.assertTrue(
            "person_income" in top_2_fields or "loan_grade" in top_2_fields,
            f"Expected person_income or loan_grade in top 2, got {top_2_fields}",
        )
        # Check that both person_income and loan_grade hurt (negative impact points)
        self.assertLess(round(-phis["person_income"] * 600), 0)
        self.assertLess(round(-phis["loan_grade"] * 600), 0)
        # Check factors direction in top factors
        factor_directions = {f["field"]: f["direction"] for f in res1["factors"]}
        self.assertEqual(factor_directions["person_income"], "hurts")
        self.assertEqual(factor_directions["loan_grade"], "hurts")

        # 4. Strong profile has net helpful impact
        strong_data = {
            "person_age": 45,
            "person_income": 150000,
            "person_emp_length": 15,
            "person_home_ownership": "MORTGAGE",
            "loan_intent": "VENTURE",
            "loan_grade": "A",
            "loan_amnt": 5000,
            "loan_int_rate": 5.5,
            "cb_person_default_on_file": "N",
            "cb_person_cred_hist_length": 15,
        }
        res_strong = explain_prediction(strong_data)
        total_strong_impact = sum(f["impact_points"] for f in res_strong["factors"]) + res_strong["other_points"]
        self.assertGreater(total_strong_impact, 0)
        self.assertGreater(res_strong["applicant_score"], res_strong["baseline_score"])
        self.assertLess(res_strong["applicant_probability"], res_strong["baseline_probability"])

        # 5. Result page returns 200 and contains "Why this score?"
        self.client.force_login(self.user1)
        res_page = self.client.get(reverse("result", kwargs={"application_id": self.app1.id}))
        self.assertEqual(res_page.status_code, 200)
        content = res_page.content.decode()
        self.assertIn("Why this score?", content)
        self.assertIn("Approximate influence of each input compared with the average applicant", content)

    # -------------------------------------------------------------------------
    # TEST 41: What-If Simulator API suite (permissions, validation, rate limit)
    # -------------------------------------------------------------------------
    def test_41_what_if_simulator_suite(self):
        """
        Phase 11 Task 2.3:
        - Owner gets 200 and numbers equal predict_credit_risk on modified data
        - Another user gets 404
        - Anonymous is redirected to login
        - Invalid values give 400 with {"error": "..."}
        - Missing parameters fall back to saved values
        - No LoanApplication or Prediction row is created
        - 61st request in a minute gets 429
        """
        url = reverse("what_if_api", kwargs={"application_id": self.app1.id})

        # 1. Anonymous is redirected to login
        anon_client = Client()
        res_anon = anon_client.get(url)
        self.assertEqual(res_anon.status_code, 302)
        self.assertTrue(res_anon["Location"].startswith(reverse("login")))

        # 2. Another user gets 404
        client_user2 = Client()
        client_user2.force_login(self.user2)
        res_other = client_user2.get(url)
        self.assertEqual(res_other.status_code, 404)

        # 3. Owner gets 200 and numbers equal predict_credit_risk on modified data
        self.client.force_login(self.user1)
        app_count_before = LoanApplication.objects.count()
        pred_count_before = Prediction.objects.count()

        params = {
            "person_income": "90000",
            "loan_amnt": "12000",
            "loan_int_rate": "9.5",
            "person_emp_length": "6",
        }
        res_mod = self.client.get(url, params)
        self.assertEqual(res_mod.status_code, 200)
        data = res_mod.json()

        expected_input = {
            "person_age": int(self.app1.age),
            "person_income": 90000.0,
            "person_emp_length": 6.0,
            "person_home_ownership": self.app1.home_ownership,
            "loan_intent": self.app1.loan_type.code,
            "loan_grade": self.app1.loan_grade,
            "loan_amnt": 12000.0,
            "loan_int_rate": 9.5,
            "cb_person_default_on_file": self.app1.previous_default,
            "cb_person_cred_hist_length": int(self.app1.credit_history_length),
        }
        expected_pred = predict_credit_risk(expected_input)

        self.assertEqual(data["score"], expected_pred["credit_score"])
        self.assertEqual(data["probability_pct"], round(expected_pred["default_probability"] * 100, 1))
        self.assertEqual(data["risk_level"], expected_pred["risk_level"])
        self.assertEqual(data["risk_label"], f"{expected_pred['risk_level']} Risk")
        self.assertEqual(data["needle_angle"], needle_angle(expected_pred["credit_score"]))
        self.assertEqual(data["delta_score"], expected_pred["credit_score"] - self.pred1.credit_score)
        self.assertEqual(
            data["delta_probability_pct"],
            round(round(expected_pred["default_probability"] * 100, 1) - round(self.pred1.default_probability * 100, 1), 1),
        )

        # 4. Missing parameters fall back to saved values
        res_fallback = self.client.get(url)
        self.assertEqual(res_fallback.status_code, 200)
        data_fb = res_fallback.json()
        expected_saved_pred = predict_credit_risk({
            "person_age": int(self.app1.age),
            "person_income": float(self.app1.annual_income),
            "person_emp_length": float(self.app1.employment_length),
            "person_home_ownership": self.app1.home_ownership,
            "loan_intent": self.app1.loan_type.code,
            "loan_grade": self.app1.loan_grade,
            "loan_amnt": float(self.app1.loan_amount),
            "loan_int_rate": float(self.app1.interest_rate),
            "cb_person_default_on_file": self.app1.previous_default,
            "cb_person_cred_hist_length": int(self.app1.credit_history_length),
        })
        self.assertEqual(data_fb["score"], expected_saved_pred["credit_score"])
        self.assertEqual(data_fb["delta_score"], expected_saved_pred["credit_score"] - self.pred1.credit_score)

        # 5. No LoanApplication or Prediction row is created
        self.assertEqual(LoanApplication.objects.count(), app_count_before)
        self.assertEqual(Prediction.objects.count(), pred_count_before)

        # 6. Invalid values return 400 JSON {"error": "..."}
        res_inv_income = self.client.get(url, {"person_income": "-100"})
        self.assertEqual(res_inv_income.status_code, 400)
        self.assertIn("error", res_inv_income.json())

        res_inv_rate = self.client.get(url, {"loan_int_rate": "85.0"})
        self.assertEqual(res_inv_rate.status_code, 400)
        self.assertIn("error", res_inv_rate.json())

        # 7. Rate limit: 61st request in a minute gets 429
        cache.clear()
        for i in range(60):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, f"Request {i+1} should be 200")
        r_61 = self.client.get(url)
        self.assertEqual(r_61.status_code, 429)
        self.assertIn("error", r_61.json())
        cache.clear()

    # -------------------------------------------------------------------------
    # TEST 42: PDF Risk Report Download suite (permissions, content, ActivityLog)
    # -------------------------------------------------------------------------
    def test_42_pdf_risk_report_download_suite(self):
        """
        Phase 11 Task 3.4:
        - Anonymous is redirected to login
        - Another user gets 404
        - Owner gets 200, Content-Type is application/pdf, starts with b"%PDF", > 1 KB
        - ActivityLog entry "Report downloaded" with application id is created
        """
        url = reverse("download_pdf_report", kwargs={"application_id": self.app1.id})

        # 1. Anonymous redirected to login
        anon_client = Client()
        res_anon = anon_client.get(url)
        self.assertEqual(res_anon.status_code, 302)
        self.assertTrue(res_anon["Location"].startswith(reverse("login")))

        # 2. Another user gets 404
        client_user2 = Client()
        client_user2.force_login(self.user2)
        res_other = client_user2.get(url)
        self.assertEqual(res_other.status_code, 404)

        # 3. Owner gets 200, PDF content, and ActivityLog is created
        self.client.force_login(self.user1)
        log_count_before = ActivityLog.objects.filter(
            action="Report downloaded", user=self.user1
        ).count()

        res_owner = self.client.get(url)
        self.assertEqual(res_owner.status_code, 200)
        self.assertEqual(res_owner["Content-Type"], "application/pdf")
        self.assertIn("attachment;", res_owner["Content-Disposition"])
        self.assertIn(f"riskwise-report-{self.app1.id}.pdf", res_owner["Content-Disposition"])
        self.assertTrue(res_owner.content.startswith(b"%PDF"))
        self.assertGreater(len(res_owner.content), 1024)  # larger than 1 KB

        # 4. ActivityLog entry created with application id
        log_count_after = ActivityLog.objects.filter(
            action="Report downloaded", user=self.user1
        ).count()
        self.assertEqual(log_count_after, log_count_before + 1)
        latest_log = ActivityLog.objects.filter(
            action="Report downloaded", user=self.user1
        ).first()
        self.assertIn(str(self.app1.id), latest_log.details)

    # -------------------------------------------------------------------------
    # TEST 43: Trust pages suite (how-it-works, privacy, terms)
    # -------------------------------------------------------------------------
    def test_43_trust_pages_suite(self):
        """
        Phase 12 Task 2.5:
        - /how-it-works/, /privacy/, and /terms/ return 200 for anonymous users
        - Each contains its main heading
        - Each page is linked from the footer
        """
        anon_client = Client()
        trust_pages = [
            ("how_it_works", "How RiskWise Works"),
            ("privacy", "Privacy Policy"),
            ("terms", "Terms of Service"),
        ]

        # Verify each trust page returns 200 and has heading
        for url_name, heading in trust_pages:
            url = reverse(url_name)
            response = anon_client.get(url)
            self.assertEqual(
                response.status_code,
                200,
                f"Expected 200 for {url_name}, got {response.status_code}",
            )
            content = response.content.decode()
            self.assertIn(heading, content)

        # Verify links in the footer of public pages (e.g. home page)
        home_res = anon_client.get(reverse("home"))
        home_content = home_res.content.decode()
        self.assertIn(reverse("how_it_works"), home_content)
        self.assertIn(reverse("privacy"), home_content)
        self.assertIn(reverse("terms"), home_content)

        # Verify Model Limitations section exists on how-it-works
        how_res = anon_client.get(reverse("how_it_works"))
        self.assertIn("Model Limitations", how_res.content.decode())

    # -------------------------------------------------------------------------
    # TEST 44: SEO and sharing suite (robots, sitemap, meta, OG, noindex)
    # -------------------------------------------------------------------------
    def test_44_seo_and_sharing_suite(self):
        """
        Phase 12 Task 3.6:
        - robots.txt and sitemap.xml return 200 with the right content type
        - sitemap lists the public pages and none of the private ones
        - home page contains og:title, canonical and the description
        - result page contains noindex
        """
        anon_client = Client()

        # 1. robots.txt returns 200 with text/plain content type
        robots_res = anon_client.get("/robots.txt")
        self.assertEqual(robots_res.status_code, 200)
        self.assertIn("text/plain", robots_res["Content-Type"])
        robots_txt = robots_res.content.decode()
        self.assertIn("User-agent: *", robots_txt)
        self.assertIn("Disallow: /admin/", robots_txt)
        self.assertIn("Disallow: /history/", robots_txt)
        self.assertIn("Disallow: /profile/", robots_txt)
        self.assertIn("Disallow: /result/", robots_txt)
        self.assertIn("Disallow: /risk-checker/", robots_txt)
        self.assertIn("Disallow: /view-as/", robots_txt)
        self.assertIn("Disallow: /demo-login/", robots_txt)
        self.assertIn("Allow: /", robots_txt)
        self.assertIn("Sitemap:", robots_txt)

        # 2. sitemap.xml returns 200 with XML content type
        sitemap_res = anon_client.get("/sitemap.xml")
        self.assertEqual(sitemap_res.status_code, 200)
        self.assertIn("xml", sitemap_res["Content-Type"])
        sitemap_content = sitemap_res.content.decode()

        # Check public pages are in sitemap
        for public_route in [
            reverse("home"),
            reverse("about"),
            reverse("how_it_works"),
            reverse("contact"),
            reverse("login"),
            reverse("register"),
            reverse("privacy"),
            reverse("terms"),
        ]:
            self.assertIn(f"<loc>http://testserver{public_route}</loc>", sitemap_content)

        # Check private pages are NOT in sitemap
        for private_path in [
            "/admin/",
            "/history/",
            "/profile/",
            "/result/",
            "/risk-checker/",
            "/view-as/",
            "/api/",
        ]:
            self.assertNotIn(private_path, sitemap_content)

        # 3. Home page contains og:title, canonical, and description
        home_res = anon_client.get(reverse("home"))
        self.assertEqual(home_res.status_code, 200)
        home_html = home_res.content.decode()
        self.assertIn('property="og:title"', home_html)
        self.assertIn('rel="canonical"', home_html)
        self.assertIn('name="description"', home_html)

        # 4. Result page contains noindex
        self.client.force_login(self.user1)
        res_page = self.client.get(
            reverse("result", kwargs={"application_id": self.app1.id})
        )
        self.assertEqual(res_page.status_code, 200)
        self.assertIn('<meta name="robots" content="noindex">', res_page.content.decode())

    # -------------------------------------------------------------------------
    # TEST 45: Operations health check and optional analytics
    # -------------------------------------------------------------------------
    def test_45_operations_healthz_and_analytics(self):
        """
        Phase 12 Task 4.4:
        - /healthz/ returns 200 JSON ok
        - simulate a model-load failure (mock) and expect 503
        - analytics script appears only when PLAUSIBLE_DOMAIN is set on public pages
        """
        anon_client = Client()

        # 1. Health check returns 200 OK with expected JSON
        health_res = anon_client.get("/healthz/")
        self.assertEqual(health_res.status_code, 200)
        self.assertEqual(
            health_res.json(),
            {"status": "ok", "database": "ok", "model": "ok"},
        )
        self.assertIn("no-cache", health_res["Cache-Control"])

        # 2. Simulate model load failure -> returns 503
        with patch("ml.predict._load", side_effect=RuntimeError("Simulated Model Failure")):
            fail_res = anon_client.get("/healthz/")
            self.assertEqual(fail_res.status_code, 503)
            data = fail_res.json()
            self.assertEqual(data.get("status"), "error")
            self.assertEqual(data.get("model"), "error")

        # 3. Analytics appears only when PLAUSIBLE_DOMAIN is set on public pages
        with self.settings(PLAUSIBLE_DOMAIN="riskwise.test"):
            # Public page (home)
            pub_res = anon_client.get(reverse("home"))
            self.assertEqual(pub_res.status_code, 200)
            self.assertIn('data-domain="riskwise.test"', pub_res.content.decode())
            self.assertIn("https://plausible.io/js/script.js", pub_res.content.decode())

            # Private page (result) - should NOT contain analytics script
            self.client.force_login(self.user1)
            priv_res = self.client.get(
                reverse("result", kwargs={"application_id": self.app1.id})
            )
            self.assertEqual(priv_res.status_code, 200)
            self.assertNotIn('data-domain="riskwise.test"', priv_res.content.decode())
            self.assertNotIn("https://plausible.io/js/script.js", priv_res.content.decode())

        # 4. Analytics does NOT appear when PLAUSIBLE_DOMAIN is unset / empty
        with self.settings(PLAUSIBLE_DOMAIN=""):
            pub_res_empty = anon_client.get(reverse("home"))
            self.assertEqual(pub_res_empty.status_code, 200)
            self.assertNotIn("https://plausible.io/js/script.js", pub_res_empty.content.decode())
            self.assertNotIn("data-domain=", pub_res_empty.content.decode())



