# Power BI Page 3 Specification — Applicants & Model Insights

## 1. Objective & Compliance Standards
Page 3 provides granular scoring analysis, feature interaction visualizations, and an anonymized compliance-grade audit table.

> [!CAUTION]
> **Data Privacy Guarantee**: In strict compliance with Non-Negotiable Rule 5 & 6, this dashboard view displays **NO personal email addresses, passwords, phone numbers, or actual applicant PII**. Identifiers use synthetic labels (`Demo Applicant #XXX` or `User #X`).

---

## 2. Page Canvas & Layout
- **Page Name**: `Applicants & Model Insights`
- **Header**: "RiskWise — Model Scoring Distribution & Applicant Audit"

---

## 3. Core Visuals

### Visual 1: Custom Credit Score Distribution (Histogram / Clustered Column)
- **Title**: "Credit Risk Score Distribution (Scale 300 - 900)"
- **X-Axis**: Grouped Score Bins (`300-399`, `400-499`, `500-599`, `600-699`, `700-799`, `800-900`)
- **Y-Axis**: `[Total Applications]`
- **Color Accent**: Teal `#14B8A6`

### Visual 2: Predicted Default Probability Distribution (Scatter or Area)
- **Title**: "Default Probability vs. Debt-to-Income Ratio"
- **X-Axis**: `'RiskWise_Portfolio'[loan_to_income]`
- **Y-Axis**: `'RiskWise_Portfolio'[default_probability]`
- **Legend / Color**: `'RiskWise_Portfolio'[risk_level]`
- **Trendline**: Linear fit illustrating increasing default probability as loan-to-income exceeds 0.30.

### Visual 3: Verified ML Model Evaluation Summary Card
- **Model**: `Random Forest (Tuned)`
- **ROC-AUC**: `0.935` (93.5% discrimination capability)
- **Accuracy**: `93.47%`
- **Precision**: `97.43%`
- **Recall**: `72.07%`
- **Training Samples**: `25,927` historical loans

### Visual 4: Applicant Detail & Audit Table
- **Columns Included**:
  1. `applicant_label`: (e.g., `Demo Applicant #042`)
  2. `is_demo`: (`Demo` / `Real`)
  3. `loan_grade`: (e.g., `B`)
  4. `loan_intent_name`: (e.g., `Medical`)
  5. `annual_income`: Currency formatted
  6. `loan_amount`: Currency formatted
  7. `interest_rate`: Percentage (`11.5%`)
  8. `credit_score`: Whole number (`809`)
  9. `risk_level`: Formatted pill tag (`Low`, `Medium`, `High`)
  10. `default_probability_pct`: (`15.2%`)

---

## 4. Manual Recreation Recipe in Power BI Desktop
1. Open **Power BI Desktop** (`PBIDesktopStore.exe`).
2. Click **Get Data** -> **Text/CSV** -> Select `c:\fintech-credit-risk\powerbi\data\riskwise_powerbi_dataset.csv`.
3. In Power Query editor, verify data types (Decimals for currency, Integers for scores/age). Click **Close & Apply**.
4. In the Modeling tab, create a **New Measure** and paste the expressions from `powerbi/dax/measures.dax`.
5. Recreate the 3 visual pages following Page 1, Page 2, and Page 3 specs.
6. Click **File -> Save As** -> Save to `c:\fintech-credit-risk\powerbi\RiskWise_Dashboard.pbix`.
7. Export / capture screenshots of each page and save into:
   - `powerbi/screenshots/overview/page1_overview.png`
   - `powerbi/screenshots/default_analysis/page2_default_analysis.png`
   - `powerbi/screenshots/applicants_model_insights/page3_applicants_model_insights.png`
