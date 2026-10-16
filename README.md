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
- Phase 1 complete: project setup (Django + MySQL)
- Phase 2 complete: dataset understanding
- Phase 3 complete: data cleaning and EDA
- Phase 4 complete: feature engineering and preprocessing
- Phase 5 complete: model training and comparison (Random Forest, ROC-AUC 0.935)
- Phase 6 complete: model saving, credit score (300-900) and risk level
- Phase 7 complete: Django + MySQL (email login, 7 models)
- Phase 8 next: website pages