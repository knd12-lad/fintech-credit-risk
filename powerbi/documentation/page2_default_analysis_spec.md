# Power BI Page 2 Specification — Default & Segmentation Analysis

## 1. Objective & Critical Guidelines
Page 2 investigates the multidimensional drivers of credit risk across demographic and financial dimensions.

> [!NOTE]
> **Interpretation Standard**: All default metrics on this page represent **Model-Predicted Default Probability** (`default_probability`) and **Predicted High-Risk Share**, derived from borrower features using the trained Random Forest classifier.

---

## 2. Page Canvas & Layout
- **Page Name**: `Default Analysis`
- **Header**: "RiskWise — Borrower Segmentation & Default Risk Analysis"

---

## 3. Four Core Analytical Visuals

### Visual 1: Default Risk by Loan Grade (Clustered Column + Line Chart)
- **Title**: "Predicted Default Risk & Application Volume by Loan Grade"
- **X-Axis**: `'RiskWise_Portfolio'[loan_grade]` (Sorted A, B, C, D, E, F, G)
- **Column Values (Left Y-Axis)**: `[Total Applications]`
- **Line Values (Right Y-Axis)**: `[Average Default Probability Pct]` (0% to 100%)
- **Insight**: Grades A and B exhibit significantly lower predicted default probability (typically < 25%), while Grades E, F, and G spike above 80%, demonstrating model alignment with credit risk fundamentals.

### Visual 2: Default Risk across Loan Intent (Horizontal Bar Chart)
- **Title**: "Average Predicted Default Probability by Loan Purpose"
- **Y-Axis**: `'RiskWise_Portfolio'[loan_intent_name]`
- **X-Axis**: `[Average Default Probability Pct]`
- **Data Labels**: Enabled (`0.0%`)
- **Color Saturation**: Conditional formatting (Gradient from Green at 10% to Red at 90%)

### Visual 3: Default Risk by Income Tiers (Stacked Column Chart)
- **Title**: "Risk Classification across Annual Income Brackets"
- **X-Axis**: `'RiskWise_Portfolio'[income_tier]`
  - Explicit Order: `< $25k`, `$25k - $50k`, `$50k - $75k`, `$75k - $100k`, `> $100k`
- **Y-Axis**: `[Total Applications]`
- **Legend**: `'RiskWise_Portfolio'[risk_level]` (Green, Amber, Red)
- **Insight**: Highlights the concentration of High-Risk applicants in the lower income tiers (< $25k and $25k-$50k) vs. affluent applicants.

### Visual 4: Default Risk across Age Groups (100% Stacked Column Chart)
- **Title**: "Age Group Risk Proportion (18-25, 26-35, 36-50, 51+)"
- **X-Axis**: `'RiskWise_Portfolio'[age_group]`
  - Order: `18-25`, `26-35`, `36-50`, `51+`
- **Y-Axis**: Percentage of Total Applications
- **Legend**: `'RiskWise_Portfolio'[risk_level]`

---

## 4. Analytical Slicers
- **Home Ownership**: Filter by `RENT`, `OWN`, `MORTGAGE`.
- **Previous Default on Record**: Filter by `N` vs `Y`.
