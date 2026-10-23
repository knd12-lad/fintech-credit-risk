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
from decimal import Decimal
from django.core.management import call_command
from django.core import mail
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from risk_app.models import LoanType, LoanApplication, Prediction, ContactMessage
from ml.predict import predict_credit_risk

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
        2. Educational disclaimer appears in footer, risk checker, and results.
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

        # Disclaimer on homepage (footer include)
        res_home = self.client.get(reverse("home"))
        self.assertEqual(res_home.status_code, 200)
        self.assertContains(res_home, disclaimer_text)

        # Disclaimer on risk checker page
        self.client.force_login(self.user1)
        res_checker = self.client.get(reverse("risk_checker"))
        self.assertEqual(res_checker.status_code, 200)
        self.assertContains(res_checker, disclaimer_text)

        # Disclaimer on prediction result page
        res_result = self.client.get(reverse("result", kwargs={"application_id": self.app1.pk}))
        self.assertEqual(res_result.status_code, 200)
        self.assertContains(res_result, disclaimer_text)

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





