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
- **X-Axis**: `'RiskWise_Portfolio'[loan_grade]` (Grades A, B, C, D, E, G — Note: Grade F has 0 records in dataset)
- **Column Values (Left Y-Axis)**: `[Total Applications]`
  - Grade A: **68 apps** (33.2% of portfolio)
  - Grade B: **72 apps** (35.1% of portfolio)
  - Grade C: **29 apps** (14.1% of portfolio)
  - Grade D: **27 apps** (13.2% of portfolio)
  - Grade E: **8 apps** (3.9% of portfolio — small sample, not a reliable insight)
  - Grade G: **1 app** (0.5% of portfolio — small sample, not a reliable insight)
- **Line Values (Right Y-Axis)**: `[Average Default Probability Pct]` (0% to 100%)
  - Grade A: **7.40%**
  - Grade B: **13.38%**
  - Grade C: **20.30%**
  - Grade D: **74.59%**
  - Grade E: **46.85%** *(small sample, not a reliable insight)*
  - Grade G: **74.34%** *(small sample, not a reliable insight)*
- **Insight**: Grades A and B exhibit low predicted default probability (< 15%), whereas Grades D, E, and G show steep escalations in default probability (> 50% to ~75%), reflecting strong alignment with credit tier risk profiles.

### Visual 2: Default Risk across Loan Intent (Horizontal Bar Chart)
- **Title**: "Average Predicted Default Probability by Loan Purpose"
- **Y-Axis**: `'RiskWise_Portfolio'[loan_intent_name]`
- **X-Axis**: `[Average Default Probability Pct]`
  - Medical: **33.38%** (35 apps)
  - Debt Consolidation: **27.79%** (33 apps)
  - Home Improvement: **25.59%** (20 apps)
  - Personal: **19.70%** (35 apps)
  - Education: **17.15%** (43 apps)
  - Venture: **12.68%** (39 apps)
- **Data Labels**: Enabled (`0.0%`)
- **Color Saturation**: Conditional formatting (Gradient from Green at 10% to Red at 40%)

### Visual 3: Default Risk by Income Tiers (Stacked Column Chart)
- **Title**: "Risk Classification across Annual Income Brackets"
- **X-Axis**: `'RiskWise_Portfolio'[income_tier]`
  - Explicit Order: `< $25k`, `$25k - $50k`, `$50k - $75k`, `$75k - $100k`, `> $100k`
  - `< $25k`: 11 apps (**41.31%** avg default prob; 4 High-risk)
  - `$25k - $50k`: 65 apps (**27.31%** avg default prob; 13 High-risk)
  - `$50k - $75k`: 63 apps (**23.44%** avg default prob; 12 High-risk)
  - `$75k - $100k`: 21 apps (**16.86%** avg default prob; 3 High-risk)
  - `> $100k`: 45 apps (**10.17%** avg default prob; 2 High-risk)
- **Y-Axis**: `[Total Applications]`
- **Legend**: `'RiskWise_Portfolio'[risk_level]` (Green, Amber, Red)
- **Insight**: Confirms that default probability inversely correlates with income level, dropping from 41.3% for borrowers earning under $25k to 10.2% for those earning over $100k.

### Visual 4: Default Risk across Age Groups (100% Stacked Column Chart)
- **Title**: "Age Group Risk Proportion (18-25, 26-35, 36-50, 51+)"
- **X-Axis**: `'RiskWise_Portfolio'[age_group]`
  - Order: `18-25` (89 apps, 19.18% avg default prob), `26-35` (93 apps, 22.86%), `36-50` (22 apps, 31.06%), `51+` (1 app, 2.41%)
- **Y-Axis**: Percentage of Total Applications
- **Legend**: `'RiskWise_Portfolio'[risk_level]`

---

## 4. Analytical Slicers
- **Home Ownership**: Filter by `RENT` (101 apps), `MORTGAGE` (84 apps), `OWN` (18 apps), `OTHER` (2 apps).
- **Previous Default on Record**: Filter by `N` (175 apps, 18.25% default prob) vs `Y` (30 apps, 44.16% default prob).
