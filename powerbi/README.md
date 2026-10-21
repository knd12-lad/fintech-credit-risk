# RiskWise — Power BI Analytics & Reporting

This directory contains the Power BI reporting architecture, export datasets, DAX measures, visual documentation, and assets for the **RiskWise — FinTech Credit Risk Scoring & Loan Default Predictor** project.

## Directory Structure

```
powerbi/
├── README.md                      # Power BI reporting architecture, data grain, and page specifications
├── RiskWise_Dashboard.pbix         # Power BI Desktop project file (saved once created & validated)
├── data/                          # Clean, anonymized export data for reporting and CSV fallback
├── dax/                           # Documented, validated DAX formulas and measure specifications
├── screenshots/                   # Genuine visual evidence and screenshots
│   ├── overview/                  # Page 1: Executive Overview & KPI visuals
│   ├── default_analysis/          # Page 2: Segmented Default Risk & Category Analysis visuals
│   └── applicants_model_insights/ # Page 3: Applicant Scoring & Model Feature Insights visuals
└── documentation/                 # Data model relationships, data dictionary, and connector guides
```

## Directory Purpose

- **`data/`**: Anonymized, compliance-safe CSV exports containing loan applications and prediction results for Power BI ingestion (either as primary data source or fallback if direct MySQL connector is unavailable). Contains no passwords, secrets, or sensitive PII.
- **`dax/`**: Master repository of all evaluated DAX business measures, including safe division logic (`DIVIDE`), count aggregations, risk category totals, and demo-isolation filters.
- **`screenshots/`**: High-resolution, authentic captures of the finalized three-page dashboard:
  - `overview/`: Executive KPI cards, portfolio risk distribution, and macro filters.
  - `default_analysis/`: Default probability and risk level by Loan Grade, Loan Intent, Income Brackets, and Age Groups.
  - `applicants_model_insights/`: Probability distributions, credit score profiles, applicant financials, and model output insights.
- **`documentation/`**: Step-by-step guides for database connection, data model star/snowflake schema definitions, relationship cardinalities, and manual recreation steps.

## Planned Dashboard Pages

### 1. Page 1 — Executive Overview
- **Objective**: High-level portfolio summary for credit committee and executive risk officers.
- **Key Visuals**:
  - Top KPI Cards: Total Applications, Predicted High-Risk %, Average Risk Score, High-Risk Count.
  - Risk Category Distribution (Donut / Pie Chart: Low, Medium, High Risk).
  - Loan Intent Breakdown (Bar Chart of volume across Personal, Education, Medical, Debt Consolidation, Venture, Home Improvement).
  - Data Type Slicer: Filter between Demo Records, Real Applications, or Consolidated View.

### 2. Page 2 — Default & Segmentation Analysis
- **Objective**: Deep-dive into risk drivers across borrower segments and loan characteristics.
- **Key Visuals**:
  - Default Probability & High-Risk Count by **Loan Grade** (A through G).
  - Risk Distribution across **Loan Intent / Loan Purpose**.
  - Risk Profiles segmented by **Annual Income Tiers** (<$25k, $25k-$50k, $50k-$75k, $75k-$100k, >$100k).
  - Default Risk across **Age Groups** (18-25, 26-35, 36-50, 50+).

### 3. Page 3 — Applicants & Model Insights
- **Objective**: Granular scoring analysis and machine learning model prediction dynamics.
- **Key Visuals**:
  - Risk Score Distribution (Histogram / Area chart of RiskWise scores 300 - 850).
  - Predicted Default Probability Curve (0.00 to 1.00).
  - Loan Amount vs. Income vs. Risk Grade scatter / matrix.
  - Secure Applicant Detail Table with non-sensitive fields (Loan ID, Grade, Intent, Income, Debt-to-Income, Risk Score, Risk Category, Demo Indicator).
