# FinTech Credit Risk Scoring & Loan Default Predictor

Web-based credit risk analysis and loan default prediction system.

## Tech Stack
- Frontend: HTML, CSS, JavaScript, Bootstrap
- Backend: Python, Django
- Data Analysis: Pandas, NumPy, Matplotlib, Seaborn
- Machine Learning: Scikit-learn
- Database: MySQL
- BI: Power BI

## Setup
1. `python -m venv venv` and activate it
2. `pip install -r requirements.txt`
3. Create a `.env` file (see `.env.example`)
4. `python manage.py migrate`
5. `python manage.py runserver`
6. `python manage.py createsuperuser`
7. `python manage.py seed_initial_data`


## Status
- Phase 1-7 complete: setup, dataset, EDA, features, model (Random Forest, ROC-AUC 0.935), prediction function, Django + MySQL
- Phase 8 complete: website (Home, About, Contact, Login, Register, Profile, Risk Checker, Result, History) and RiskWise admin (dashboard, users, applicants, predictions with CSV export, analytics)
- Phase 9 complete: Risk Checker is connected to the ML model and saves every prediction to MySQL
- Phase 10 next: Power BI dashboard, testing, final documentation