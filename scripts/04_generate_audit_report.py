"""
Step 4 — Generate PDF Audit Report
=====================================
Produces a formatted PDF audit report for a processed timecard.
Includes: timecard details, JIRA worklog table, hour calculations, and decision.

Usage (standalone):
    python scripts/04_generate_audit_report.py --help

Dependencies:
    pip install fpdf2
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import REPORTS_OUTPUT_DIR

try:
    from fpdf import FPDF
except ImportError:
    print("ERROR: fpdf2 not installed. Run: pip install fpdf2")
    sys.exit(1)


def _section_header(pdf: FPDF, title: str):
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(44, 62, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7, title, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)


def _kv_row(pdf: FPDF, label: str, value: str):
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(65, 6, label + ":")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")


def generate_report(
    timecard_id: str,
    resource: str,
    period_start: str,
    period_end: str,
    sparta_hours: float,
    project: str,
    decision: str,
    rule: str,
    jira_logs: list,
    jira_total: float,
    leave_holiday_hours: float,
    project_hours: float,
    gap: float,
    approver: str = "Carl Solomon",
    output_dir: str = None,
) -> str:
    """
    Generate a PDF audit report.

    Args:
        timecard_id:        e.g. "TCH-05-22-2026-337288"
        resource:           Employee name
        period_start:       "18/05/2026"
        period_end:         "24/05/2026"
        sparta_hours:       Hours from the Sparta timecard
        project:            Project name/code
        decision:           "APPROVE" or "REJECT"
        rule:               Decision rule explanation string
        jira_logs:          List of dicts from pull_worklogs()
        jira_total:         Total JIRA hours
        leave_holiday_hours: Hours on leave/holiday tasks
        project_hours:      JIRA project hours (excl. leave/holiday)
        gap:                jira_total - sparta_hours
        approver:           Name of the approver
        output_dir:         Directory to write the PDF (defaults to settings.REPORTS_OUTPUT_DIR)

    Returns:
        Path to the generated PDF file.
    """
    if output_dir is None:
        output_dir = REPORTS_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)

    # ── Header banner ──
    pdf.set_fill_color(192, 57, 43)
    pdf.rect(0, 0, 210, 25, "F")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(8)
    pdf.cell(0, 10, f"Audit Report — {timecard_id}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    # ── Timecard Details ──
    _section_header(pdf, "Timecard Details")
    _kv_row(pdf, "Timecard ID", timecard_id)
    _kv_row(pdf, "Resource", resource)
    _kv_row(pdf, "Period", f"{period_start} – {period_end}")
    _kv_row(pdf, "Total Hours (Sparta)", str(sparta_hours))
    _kv_row(pdf, "Project", project[:80])
    _kv_row(pdf, "Decision", decision)
    _kv_row(pdf, "Actual Approver", approver)
    _kv_row(pdf, "Date Processed", datetime.now().strftime("%Y-%m-%d"))
    pdf.ln(4)

    # ── JIRA Worklog Table ──
    _section_header(pdf, f"JIRA Worklog Data ({period_start} – {period_end})")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(180, 180, 180)
    pdf.cell(28, 6, "Date", border=1, fill=True)
    pdf.cell(25, 6, "Issue", border=1, fill=True)
    pdf.cell(110, 6, "Summary", border=1, fill=True)
    pdf.cell(17, 6, "Hours", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)
    for i, log in enumerate(jira_logs):
        is_lh = log.get("is_leave_holiday", False)
        if is_lh:
            pdf.set_fill_color(255, 235, 235)
        else:
            pdf.set_fill_color(249, 249, 249) if i % 2 == 0 else pdf.set_fill_color(255, 255, 255)
        pdf.cell(28, 5, log["date"], border=1, fill=True)
        pdf.cell(25, 5, log["issue"], border=1, fill=True)
        pdf.cell(110, 5, log["summary"][:58], border=1, fill=True)
        pdf.cell(17, 5, str(log["hours"]), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    # Totals row
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(28, 6, "TOTAL", border=1, fill=True)
    pdf.cell(25, 6, "", border=1, fill=True)
    pdf.cell(110, 6, "", border=1, fill=True)
    pdf.cell(17, 6, str(jira_total), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    if leave_holiday_hours > 0:
        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(150, 0, 0)
        pdf.cell(0, 5, "* Pink rows = Leave/Holiday tasks", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    # ── Hour Calculation ──
    _section_header(pdf, "Hour Calculation")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(180, 180, 180)
    pdf.cell(135, 6, "Metric", border=1, fill=True)
    pdf.cell(45, 6, "Hours", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    calcs = [
        ("Total JIRA Hours", str(jira_total)),
        ("Leave / Holiday Hours", str(leave_holiday_hours)),
        ("JIRA Project Hours (excl. Leave/Holiday)", str(project_hours)),
        ("Sparta Hours", str(sparta_hours)),
        ("Gap (JIRA total – Sparta)", str(gap)),
        ("Gap explained by Leave/Holiday?", "YES" if abs(abs(gap) - leave_holiday_hours) < 0.01 or abs(gap) < 0.01 else "NO"),
    ]
    pdf.set_font("Helvetica", "", 8)
    for i, (metric, value) in enumerate(calcs):
        pdf.set_fill_color(249, 249, 249) if i % 2 == 0 else pdf.set_fill_color(255, 255, 255)
        pdf.cell(135, 5, metric, border=1, fill=True)
        pdf.cell(45, 5, value, border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Decision ──
    _section_header(pdf, "Decision")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 6, f"Rule Applied: {rule}")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 14)
    colour = (0, 128, 0) if decision == "APPROVE" else (192, 57, 43)
    pdf.set_text_color(*colour)
    pdf.cell(0, 10, f"DECISION: {decision}D", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)

    # ── Output ──
    filename = f"audit_{timecard_id}.pdf"
    output_path = os.path.join(output_dir, filename)
    pdf.output(output_path)
    print(f"\n[REPORT] Saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    # Quick smoke test with sample data
    sample_logs = [
        {"date": "18/05/2026", "issue": "QDM-4941", "summary": "Darwin - Final UAT", "hours": 8.0, "is_leave_holiday": False},
        {"date": "19/05/2026", "issue": "QDM-4941", "summary": "Darwin - Final UAT", "hours": 8.0, "is_leave_holiday": False},
    ]
    path = generate_report(
        timecard_id="TCH-TEST-000000",
        resource="Test User",
        period_start="18/05/2026",
        period_end="24/05/2026",
        sparta_hours=16.0,
        project="Test Project",
        decision="APPROVE",
        rule="JIRA total (16h) equals Sparta (16h) and no leave/holiday tasks found.",
        jira_logs=sample_logs,
        jira_total=16.0,
        leave_holiday_hours=0.0,
        project_hours=16.0,
        gap=0.0,
        output_dir="/tmp/reports_test",
    )
    print(f"Test report: {path}")
