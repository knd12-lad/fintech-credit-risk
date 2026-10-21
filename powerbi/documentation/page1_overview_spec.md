# Power BI Page 1 Specification — Executive Overview

## 1. Visual Layout & Canvas Setup
- **Page Name**: `Overview`
- **Canvas Size**: 16:9 Standard (1280 x 720 or 1920 x 1080)
- **Background**: Hex `#F8FAFC` (Slate Tint) or Pure White with subtle shadow borders
- **Header Banner**: Navy `#0B132B` background with Teal `#14B8A6` accent
  - **Title**: "RiskWise Credit Risk Portfolio Overview"
  - **Subtitle**: "Executive Lending Analytics & ML Default Risk Assessment"

---

## 2. Top Executive KPI Cards (Row 1)
Positioned horizontally across the top (`Y: 90px`, `Height: 110px`):

| KPI Card | Measure | Display Format | Expected Initial Value | Visual Style |
| :--- | :--- | :--- | :--- | :--- |
| **Card 1** | `[Total Applications]` | Whole Number (`#,##0`) | **202** | Dark Blue Callout |
| **Card 2** | `[Predicted High-Risk Percentage]` | Percentage (`0.0%`) | **59.9%** | Red Callout (`#EF4444`) |
| **Card 3** | `[Average Credit Score]` | Whole Number (`###`) | **536** | Teal Callout (`#14B8A6`) |
| **Card 4** | `[High-Risk Count]` | Whole Number (`#,##0`) | **121** | Amber/Red Callout |
| **Card 5** | `[Total Loan Volume]` | Currency (`$#,##0`) | **$2,165,850** | Slate Callout |

---

## 3. Core Visuals (Row 2 & Row 3)

### Visual 1: Portfolio Risk Distribution (Donut Chart)
- **Location**: Top-Left quadrant (`Width: 380px`, `Height: 340px`)
- **Title**: "Portfolio Distribution by Risk Level"
- **Legend / Slices**: `'RiskWise_Portfolio'[risk_level]`
- **Values**: `[Total Applications]`
- **Color Palette**:
  - `Low`: Green (`#16A34A` / `#10B981`) -> **75 records (37.1%)**
  - `Medium`: Amber (`#F59E0B`) -> **6 records (3.0%)**
  - `High`: Red (`#EF4444`) -> **121 records (59.9%)**
- **Data Labels**: Category + Percentage of Total

### Visual 2: Loan Purpose Breakdown (Clustered Column Chart)
- **Location**: Top-Right quadrant (`Width: 620px`, `Height: 340px`)
- **Title**: "Loan Assessment Volume by Loan Purpose"
- **X-Axis**: `'RiskWise_Portfolio'[loan_intent_name]` (Education, Medical, Venture, Personal, Home Improvement, Debt Consolidation)
- **Y-Axis**: `[Total Applications]`
- **Data Callouts**: Show Value on Data Labels
- **Bar Color**: RiskWise Navy/Teal (`#0E7490`)

### Visual 3: Risk Level by Home Ownership (Stacked Bar Chart)
- **Location**: Bottom-Left quadrant (`Width: 480px`, `Height: 250px`)
- **Title**: "Risk Composition by Home Ownership"
- **Y-Axis**: `'RiskWise_Portfolio'[home_ownership]` (RENT, OWN, MORTGAGE, OTHER)
- **X-Axis**: `[Total Applications]`
- **Legend**: `'RiskWise_Portfolio'[risk_level]`

---

## 4. Interactive Slicers / Filters
Positioned in a designated filter rail or top bar:
1. **Data Type Slicer**:
   - Field: `'RiskWise_Portfolio'[is_demo]`
   - Options: `All`, `Demo` (200 records), `Real` (2 records)
   - Behavior: Allows auditing synthetic demo benchmarks vs. real live portal submissions.
2. **Loan Grade Slicer**:
   - Field: `'RiskWise_Portfolio'[loan_grade]` (Buttons A through G)
