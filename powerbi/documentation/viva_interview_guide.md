# RiskWise — Viva & Technical Interview Comprehensive Guide

This guide contains beginner-friendly, precise, and truthful answers for academic viva examinations and technical job interviews.

---

## 1. Project Overview

### Q1: What is RiskWise?
**Answer:** RiskWise is an automated credit risk evaluation and loan default prediction platform. It evaluates borrower financial profiles, calculates the probability that a loan will default, assigns a custom credit risk score from 300 to 900, classifies the loan into a risk tier (Low, Medium, High), and provides interactive web dashboards and Power BI reporting for portfolio risk monitoring.

### Q2: Why did you choose this project?
**Answer:** In traditional banking and FinTech lending, manual credit appraisal is slow, labor-intensive, and prone to human inconsistency. By leveraging machine learning with a full-stack Django web application and a production MySQL database, RiskWise demonstrates how technology can automate credit decisions, improve risk transparency, and enforce objective lending standards.

### Q3: What problem does RiskWise address?
**Answer:** It addresses the challenge of credit default risk in consumer lending. Financial institutions need to accurately distinguish creditworthy applicants from high-risk borrowers before disbursing funds, preventing bad debt while ensuring fair access to credit.

### Q4: What is the end-to-end application workflow?
**Answer:**
1. A borrower creates an account and logs into the RiskWise portal.
2. The user navigates to the Credit Risk Checker form and enters financial details (income, loan amount, employment length, interest rate, loan grade, loan purpose, etc.).
3. The Django backend validates the inputs and passes them to the ML preprocessing pipeline.
4. Numerical features are scaled and categories are encoded.
5. The trained Random Forest model predicts default probability and calculates a calibrated risk score (300-900).
6. In an atomic transaction, Django persists the application and prediction results in MySQL.
7. The user is redirected to an interactive result screen displaying their risk score gauge and assessment breakdown.
8. The borrower can review their personal past applications in their Prediction History.
9. Administrators can monitor portfolio-level metrics in the RiskWise Admin Portal or export data to Power BI.

### Q5: What components did you implement yourself?
**Answer:**
- Custom email-based Django authentication and role-based access control.
- Machine learning feature engineering and model training pipeline in Scikit-learn.
- Database models with ForeignKey and OneToOne relationships in MySQL.
- Web forms with validation, error handling, and responsive Bootstrap styling.
- Administrative analytics dashboard with Chart.js visualizations.
- Comprehensive 18-test automated Django test suite.
- Power BI reporting model and DAX measures.

---

## 2. Django & Frontend Architecture

### Q1: What is Django and how does its architecture work?
**Answer:** Django is a high-level, open-source Python web framework following the **Model-Template-View (MTV)** architecture:
- **Model**: Defines the database schema, field types, and ORM business rules.
- **Template**: The presentation layer (HTML, CSS, Django Template Language) that renders data to the user.
- **View**: The business logic layer that handles incoming HTTP requests, interacts with models or the ML pipeline, and returns HTTP responses or rendered templates.

### Q2: How does authentication and route protection work?
**Answer:** RiskWise uses a custom `User` model inheriting from `AbstractUser` where `email` replaces `username` as the primary identifier. Protected routes (like `/risk-checker/`, `/history/`, `/profile/`) are secured using the `@login_required` decorator, which automatically redirects unauthenticated users to `/login/?next=...`. Administrative views require `is_staff=True` and `role="ADMIN"`.

### Q3: How does the frontend communicate with the backend?
**Answer:** The frontend sends standard HTTP POST requests with form-encoded data and a security CSRF token (`{% csrf_token %}`). The backend processes the request and either re-renders the template with validation errors or redirects with flash messages using Django's messages framework.

---

## 3. Database & MySQL Persistence

### Q1: Why did you choose MySQL over SQLite?
**Answer:** SQLite is an in-process file-based database ideal for small local experiments. MySQL is a robust client-server relational database management system (RDBMS) that supports concurrency, high-performance indexing, strict data integrity constraints, atomic transactions, and direct ODBC/connector integration with enterprise BI tools like Power BI.

### Q2: What are the primary models and their relationships?
**Answer:**
- `User` (1) to `LoanApplication` (Many) via `ForeignKey(User, on_delete=CASCADE)`.
- `LoanType` (1) to `LoanApplication` (Many) via `ForeignKey(LoanType, on_delete=PROTECT)`.
- `LoanApplication` (1) to `Prediction` (1) via `OneToOneField(LoanApplication, on_delete=CASCADE)`.
- `ModelInfo`: Stores ML model metadata and accuracy metrics.
- `ContactMessage`: Captures user contact inquiries.

### Q3: How is a prediction stored atomically?
**Answer:** In `risk_checker_view`, `LoanApplication.objects.create(...)` and `Prediction.objects.create(...)` are wrapped inside a `with transaction.atomic():` block. If either database write fails, the entire transaction is rolled back, preventing orphaned records.

### Q4: How is prediction history isolated to the correct user?
**Answer:** In `history_view`, the query explicitly filters by the signed-in user: `LoanApplication.objects.filter(user=request.user)`. In `result_view`, `get_object_or_404(LoanApplication, pk=application_id, user=request.user)` ensures that a user can never access another user's loan assessment, returning a 404 response.

---

## 4. Machine Learning & Credit Scoring

### Q1: Which ML algorithm was selected and why?
**Answer:** A tuned **Random Forest Classifier** was selected. During comparative model evaluations (Logistic Regression, Decision Trees, Random Forest), Random Forest demonstrated the highest discrimination power with an **ROC-AUC of 0.9350** and **93.47% accuracy**. Its ensemble of decision trees effectively captures non-linear interactions between income, loan amounts, and credit history while resisting overfitting.

### Q2: What features does the model require?
**Answer:** 10 core features:
- Numerical: `person_age`, `person_income`, `person_emp_length`, `loan_amnt`, `loan_int_rate`, `cb_person_cred_hist_length`.
- Engineered Numerical: `loan_to_income`, `interest_to_income`.
- Categorical Ordinal: `loan_grade` (A to G), `cb_person_default_on_file` (N, Y).
- Categorical Nominal: `person_home_ownership` (RENT, OWN, MORTGAGE, OTHER), `loan_intent` (EDUCATION, MEDICAL, etc.).

### Q3: What is the difference between predicted default risk and actual loan default?
**Answer:**
- **Predicted Default Probability**: A continuous statistical estimate (0.0 to 1.0) produced by the model estimating the likelihood of future non-payment based on current applicant traits.
- **Actual Loan Default**: A historical, binary fact (0 = Repaid, 1 = Defaulted) indicating whether a borrower in a past dataset actually failed to fulfill loan obligations. They should never be conflated.

### Q4: How is the RiskWise Credit Score calculated?
**Answer:** It scales the model's default probability linearly to an intuitive 300 to 900 scale:
$$\text{Score} = \text{round}(900 - (\text{Probability} \times 600))$$
A 0% probability yields 900 (maximum creditworthiness); a 100% probability yields 300. Scores $\ge 780$ are Low Risk; $600 - 779$ are Medium Risk; $< 600$ are High Risk.

---

## 5. Power BI & Business Intelligence

### Q1: How does Power BI connect to RiskWise data?
**Answer:** Power BI connects either directly via the **MySQL Database Connector** (importing tables with an SQL query) or via the **CSV Fallback** using `powerbi/data/riskwise_powerbi_dataset.csv`, which contains 202 clean, non-sensitive records.

### Q2: What are DAX measures?
**Answer:** DAX (Data Analysis Expressions) formulas create dynamic aggregations and calculations evaluated at query time based on user filter contexts (e.g., slicers). RiskWise uses measures like `[Total Applications]`, `[High-Risk Count]`, `[Average Credit Score]`, and `[Predicted High-Risk Percentage]` using `DIVIDE` to avoid division-by-zero errors.

### Q3: How are synthetic demo records handled in Power BI?
**Answer:** Each record has an `is_demo` column (`"Demo"` vs `"Real"`). Power BI includes a dedicated data slicer allowing stakeholders to inspect the 200 synthetic demo records, real user submissions, or the combined portfolio.

---

## 6. Testing, Security & Quality Assurance

### Q1: How were automated tests conducted?
**Answer:** A comprehensive 18-test suite was implemented using Django's built-in `TestCase` and test client (`risk_app/tests.py`). When executed via `python manage.py test risk_app`, Django creates an isolated test database in MySQL, runs all test assertions across routing, authentication, validations, and database writes, and tears down the database cleanly without altering production data.

### Q2: What security controls are implemented?
**Answer:**
- Password hashing with PBKDF2/SHA-256.
- CSRF token validation on all POST requests.
- SQL injection prevention via Django ORM parameterized queries.
- XSS escaping in Django templates.
- Strict user authorization preventing cross-user data access.
- Secure environment separation: `.env` excluded from version control.

---

## 7. Short 2–3 Minute Presentation Script

> "Good morning, respected professors/interviewers.
>
> Today, I am presenting **RiskWise — FinTech Credit Risk Scoring & Loan Default Predictor**.
>
> In consumer lending, assessing borrower creditworthiness quickly and accurately is critical to minimizing loan defaults and avoiding financial loss. Traditional underwriting often relies on slow manual checks or rigid heuristic rules.
>
> To solve this, I developed **RiskWise**, an end-to-end web platform and credit risk analytics engine.
>
> The project has three core pillars:
>
> **First, the Machine Learning Engine:** Using a dataset of over 32,000 historical loan records, I engineered key financial ratios like Loan-to-Income and Interest-to-Income. I evaluated several classifiers and trained a tuned Random Forest model that achieved an **ROC-AUC of 0.935** and **93.5% accuracy**. The model outputs a default probability and calibrates a custom credit score between 300 and 900.
>
> **Second, the Django Web Application & MySQL Database:** I built a full-stack platform featuring custom email-based authentication, borrower self-service, real-time credit checks, and an admin portal with live portfolio analytics. Every loan application and its prediction are stored atomically in a normalized MySQL database with strict user isolation.
>
> **Third, Business Intelligence & Quality Assurance:** I prepared a 3-page Power BI reporting model with validated DAX measures to analyze risk distributions across loan grades, income tiers, and age groups. To ensure high code quality, I authored an automated 18-test suite that verifies authentication, form validation, ML outputs, and security access with a 100% pass rate.
>
> Thank you, and I am now happy to answer any questions."
