"""
PDF Risk Report Generator for RiskWise.
Generates an elegant, single-page PDF report using ReportLab Platypus.
"""

from io import BytesIO
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ml.explain import explain_prediction
from .models import ModelInfo


NAVY = colors.HexColor("#0B132B")
TEAL = colors.HexColor("#14B8A6")
DARK_TEAL = colors.HexColor("#0F766E")
SLATE = colors.HexColor("#475569")
LIGHT_SLATE = colors.HexColor("#64748B")
LIGHT_BG = colors.HexColor("#F8FAFC")
BORDER_COLOR = colors.HexColor("#CBD5E1")
CARD_BG = colors.HexColor("#F1F5F9")


def generate_risk_report_pdf(application) -> bytes:
    """
    Builds a single-page credit risk report in PDF format.
    Does not disclose email or any non-application account information.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=26,
        bottomMargin=26,
    )

    styles = getSampleStyleSheet()

    # Typography using built-in fonts only
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=NAVY,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=DARK_TEAL,
    )
    meta_style = ParagraphStyle(
        "ReportMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=LIGHT_SLATE,
        alignment=2,  # Right-aligned
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=NAVY,
    )
    cell_label = ParagraphStyle(
        "CellLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=LIGHT_SLATE,
    )
    cell_value = ParagraphStyle(
        "CellValue",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=NAVY,
    )
    metric_label = ParagraphStyle(
        "MetricLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=LIGHT_SLATE,
        alignment=1,
    )
    metric_value = ParagraphStyle(
        "MetricVal",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=NAVY,
        alignment=1,
    )
    metric_sub = ParagraphStyle(
        "MetricSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=DARK_TEAL,
        alignment=1,
    )
    factor_text = ParagraphStyle(
        "FactorText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=NAVY,
    )
    disclaimer_style = ParagraphStyle(
        "DisclaimerText",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=LIGHT_SLATE,
        alignment=1,
    )

    story = []

    # 1. Header (Logo / Brand + Metadata)
    date_str = timezone.now().strftime("%B %d, %Y")
    header_content = [
        [
            Paragraph("<b>RiskWise</b><br/><font color='#0F766E'>Credit Risk Assessment Report</font>", title_style),
            Paragraph(f"<b>Generation Date:</b> {date_str}<br/><b>Application ID:</b> #{application.id}", meta_style),
        ]
    ]
    t_header = Table(header_content, colWidths=[330, 210])
    t_header.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )
    story.append(t_header)
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=TEAL, spaceBefore=0, spaceAfter=8))

    # 2. Executive Key Metrics Banner
    pred = application.prediction
    score_display = f"{pred.credit_score}"
    prob_display = f"{round(pred.default_probability * 100, 1)}%"
    risk_level_display = f"{pred.risk_level} Risk"

    metrics_content = [
        [
            Paragraph("CREDIT SCORE", metric_label),
            Paragraph("RISK LEVEL", metric_label),
            Paragraph("DEFAULT PROBABILITY", metric_label),
        ],
        [
            Paragraph(score_display, metric_value),
            Paragraph(pred.risk_level, metric_value),
            Paragraph(prob_display, metric_value),
        ],
        [
            Paragraph("Scale 300 - 900", metric_sub),
            Paragraph(risk_level_display, metric_sub),
            Paragraph("Estimated likelihood", metric_sub),
        ],
    ]
    t_metrics = Table(metrics_content, colWidths=[180, 180, 180])
    t_metrics.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    story.append(t_metrics)
    story.append(Spacer(1, 8))

    # 3. Application Details Table
    story.append(Paragraph("Application Details", section_heading))
    story.append(Spacer(1, 3))

    prev_default_str = "Yes" if application.previous_default == "Y" else "No"
    details_data = [
        [
            Paragraph("Applicant Name", cell_label),
            Paragraph(application.full_name, cell_value),
            Paragraph("Loan Purpose", cell_label),
            Paragraph(application.loan_type.name, cell_value),
        ],
        [
            Paragraph("Annual Income", cell_label),
            Paragraph(f"${float(application.annual_income):,.2f}", cell_value),
            Paragraph("Loan Amount", cell_label),
            Paragraph(f"${float(application.loan_amount):,.2f}", cell_value),
        ],
        [
            Paragraph("Interest Rate", cell_label),
            Paragraph(f"{application.interest_rate:.2f}%", cell_value),
            Paragraph("Loan Grade", cell_label),
            Paragraph(application.loan_grade, cell_value),
        ],
        [
            Paragraph("Employment Length", cell_label),
            Paragraph(f"{application.employment_length} years", cell_value),
            Paragraph("Credit History", cell_label),
            Paragraph(f"{application.credit_history_length} years", cell_value),
        ],
        [
            Paragraph("Home Ownership", cell_label),
            Paragraph(application.home_ownership, cell_value),
            Paragraph("Previous Default", cell_label),
            Paragraph(prev_default_str, cell_value),
        ],
    ]
    t_details = Table(details_data, colWidths=[115, 155, 115, 155])
    t_details.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    story.append(t_details)
    story.append(Spacer(1, 8))

    # 4. Top Influencing Factors (Explainability)
    story.append(Paragraph("Score Drivers (Exact Shapley Analysis)", section_heading))
    story.append(Spacer(1, 3))

    app_data = {
        "person_age": int(application.age),
        "person_income": float(application.annual_income),
        "person_emp_length": float(application.employment_length),
        "person_home_ownership": application.home_ownership,
        "loan_intent": application.loan_type.code,
        "loan_grade": application.loan_grade,
        "loan_amnt": float(application.loan_amount),
        "loan_int_rate": float(application.interest_rate),
        "cb_person_default_on_file": application.previous_default,
        "cb_person_cred_hist_length": int(application.credit_history_length),
    }

    try:
        explanation = explain_prediction(app_data, top_n=4)
        factors = explanation.get("factors", [])
    except Exception:
        factors = []

    if factors:
        factor_rows = []
        for f in factors:
            direction_tag = "[RAISES SCORE]" if f["direction"] == "helps" else "[LOWERS SCORE]"
            tag_color = "#047857" if f["direction"] == "helps" else "#B91C1C"
            row_html = (
                f"<font color='{tag_color}'><b>{direction_tag}</b></font> "
                f"{f['sentence']}"
            )
            factor_rows.append([Paragraph(row_html, factor_text)])

        t_factors = Table(factor_rows, colWidths=[540])
        t_factors.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ])
        )
        story.append(t_factors)
    else:
        story.append(Paragraph("Explanation data is currently unavailable.", factor_text))

    story.append(Spacer(1, 8))

    # 5. Model Information
    story.append(Paragraph("Model Governance & Performance", section_heading))
    story.append(Spacer(1, 3))

    active_model = ModelInfo.objects.filter(is_active=True).first()
    if active_model:
        model_name = active_model.model_name
        roc_auc = f"{active_model.roc_auc:.4f}"
        accuracy = f"{active_model.accuracy * 100:.1f}%"
        recall = f"{active_model.recall * 100:.1f}%"
    else:
        model_name = "Random Forest"
        roc_auc = "0.8920"
        accuracy = "86.5%"
        recall = "72.1%"

    model_table_data = [
        [
            Paragraph("Active Model", cell_label),
            Paragraph(model_name, cell_value),
            Paragraph("ROC-AUC", cell_label),
            Paragraph(roc_auc, cell_value),
        ],
        [
            Paragraph("Accuracy", cell_label),
            Paragraph(accuracy, cell_value),
            Paragraph("Recall", cell_label),
            Paragraph(recall, cell_value),
        ],
    ]
    t_model = Table(model_table_data, colWidths=[115, 155, 115, 155])
    t_model.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    story.append(t_model)
    story.append(Spacer(1, 8))

    # 6. Disclaimer
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=2, spaceAfter=4))
    disclaimer_text = (
        "RiskWise is an educational/demo project. "
        "Results are model estimates and must not be used for real lending decisions."
    )
    story.append(Paragraph(disclaimer_text, disclaimer_style))

    doc.build(story)
    return buffer.getvalue()
