# RiskWise — Power BI Analytics & Reporting

This directory contains the Power BI reporting architecture, export datasets, DAX measures, visual documentation, and assets for the **RiskWise — FinTech Credit Risk Scoring & Loan Default Predictor** project.

> [!NOTE]
> **Dashboard File & Screenshot Notice**: `RiskWise_Dashboard.pbix` and the visual screenshots are **still to be created manually in Power BI Desktop** following the step-by-step instructions in the documentation section below. They are not pre-packaged or committed as binary assets in this repository.

---

## Directory Structure

```
powerbi/
├── README.md                      # Power BI reporting architecture, data grain, and page specifications
├── RiskWise_Dashboard.pbix        # Power BI Desktop project file (to be created manually via Power BI Desktop)
├── RiskWise_Theme.json            # Official RiskWise visual styling theme
├── data/                          # Clean, anonymized export data (riskwise_powerbi_dataset.csv)
├── dax/                           # Documented, validated DAX formulas and measure specifications
├── screenshots/                   # Destination folder for manual captures from Power BI Desktop
│   ├── overview/                  # Page 1: Executive Overview & KPI visuals
│   ├── default_analysis/          # Page 2: Segmented Default Risk & Category Analysis visuals
│   └── applicants_model_insights/ # Page 3: Applicant Scoring & Model Feature Insights visuals
└── documentation/                 # Step-by-step page specifications, data model schema, and guides
```

## Directory Purpose

- **`data/`**: Anonymized, compliance-safe CSV export (`riskwise_powerbi_dataset.csv`) generated via `python manage.py export_powerbi_dataset`. Contains 205 records (200 reproducible demo records + 5 live user records). Contains zero passwords, emails, or personal PII.
- **`dax/`**: Master repository of all evaluated DAX business measures (`measures.dax`), including safe division logic (`DIVIDE`), count aggregations, risk category totals, portfolio volume, and calculated columns (`Income Tier Sorted`).
- **`RiskWise_Theme.json`**: Official Power BI custom theme JSON configured with RiskWise brand palette (`#0E7490`, `#14B8A6`, `#F59E0B`, `#EF4444`), white card styling, `#E2E8F0` border, and 8px corner radius.
- **`screenshots/`**: Directory reserved for authentic screenshots exported after building the report in Power BI Desktop.
- **`documentation/`**: Step-by-step build recipes, visual coordinate specifications, schema definitions, and connector documentation.

---

## Portfolio Baseline Metrics (Computed from Live Dataset)

- **Total Applications**: **205** (200 Demo [97.6%], 5 Real [2.4%])
- **Total Portfolio Loan Volume**: **$2,863,275.00**
- **Average Loan Amount**: **$13,967.20**
- **Average Credit Score**: **767.8** (Scale 300 - 900)
- **Average Model Default Probability**: **22.04%**
- **Risk Level Distribution**:
  - **Low Risk**: **153 (74.6%)**
  - **Medium Risk**: **18 (8.8%)**
  - **High Risk**: **34 (16.6%)**

---

## Planned Dashboard Pages

### 1. Page 1 — Executive Overview
- **Objective**: High-level portfolio summary for credit committee and executive risk officers.
- **Key Visuals**:
  - Top KPI Cards: Total Applications (**205**), Predicted High-Risk % (**16.6%**), Average Risk Score (**768**), High-Risk Count (**34**), Total Loan Volume (**$2,863,275**).
  - Risk Category Distribution (Donut Chart): Low (153, 74.6%), Medium (18, 8.8%), High (34, 16.6%).
  - Loan Purpose Breakdown (Column Chart): Education (43), Venture (39), Medical (35), Personal (35), Debt Consolidation (33), Home Improvement (20).
  - Data Type Slicer: Filter between Demo Records (200), Real Applications (5), or All.

### 2. Page 2 — Default & Segmentation Analysis
- **Objective**: Deep-dive into risk drivers across borrower segments and loan characteristics.
- **Key Visuals**:
  - Default Probability & Volume by **Loan Grade**: Grades A through E and G (Grade F has 0 records in dataset). Grade A (7.4%, 68 apps), Grade B (13.4%, 72 apps), Grade C (20.3%, 29 apps), Grade D (74.6%, 27 apps), Grade E (46.9%, 8 apps — small sample, not a reliable insight), Grade G (74.3%, 1 app — small sample, not a reliable insight).
  - Risk Distribution across **Loan Purpose**: Medical (33.4% avg default prob), Debt Consolidation (27.8%), Home Improvement (25.6%), Personal (19.7%), Education (17.2%), Venture (12.7%).
  - Risk Profiles segmented by **Annual Income Tiers**: `< $25k` (11 apps, 41.3% avg default prob), `$25k - $50k` (65 apps, 27.3%), `$50k - $75k` (63 apps, 23.4%), `$75k - $100k` (21 apps, 16.9%), `> $100k` (45 apps, 10.2%).
  - Default Risk across **Age Groups**: 18-25 (89 apps, 19.2% avg default prob), 26-35 (93 apps, 22.9%), 36-50 (22 apps, 31.1%), 51+ (1 app, 2.4%).

### 3. Page 3 — Applicants & Model Insights
- **Objective**: Granular scoring analysis and machine learning model prediction dynamics.
- **Key Visuals**:
  - Risk Score Distribution (Histogram / Column chart across buckets: 300-399 [31], 400-499 [2], 500-599 [1], 600-699 [6], 700-799 [16], 800-900 [149]).
  - Predicted Default Probability Curve vs. Debt-to-Income ratio.
  - Loan Amount vs. Income vs. Risk Grade scatter / matrix.
  - Anonymized Applicant Detail Audit Table (Application ID, Applicant Label, Grade, Purpose, Income, Loan Amount, Interest Rate, Credit Score, Risk Level, Default Prob).
