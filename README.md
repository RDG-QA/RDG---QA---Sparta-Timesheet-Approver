# Sparta Timecard Approvals — Automation Suite

Automated timecard approval/rejection workflow that cross-references **Sparta Global** timesheet submissions against **JIRA worklogs** using the JIRA REST API.

---

## Overview

This suite automates the PM timecard review process by:
1. Navigating to each pending timecard in the Sparta portal
2. Pulling the employee's JIRA worklogs for the timecard period via the JIRA REST API
3. Applying the agreed decision matrix (approve/reject logic)
4. Actioning the decision in Sparta
5. Generating a PDF audit report for every timecard processed

---

## Repository Structure

```
sparta-timecard-approvals/
├── README.md                        ← This file
├── config/
│   └── settings.py                  ← Configuration (credentials, URLs, constants)
├── scripts/
│   ├── 01_fetch_pending_timecards.py ← Step 1: List pending timecards from Sparta (browser)
│   ├── 02_pull_jira_worklogs.py      ← Step 2: Pull JIRA worklogs for a resource/period
│   ├── 03_apply_decision_matrix.py   ← Step 3: Apply approval/rejection logic
│   ├── 04_generate_audit_report.py   ← Step 4: Generate PDF audit report
│   └── 05_full_pipeline.py           ← Full end-to-end pipeline (runs steps 1–4)
├── docs/
│   └── USER_MANUAL.md               ← Full user manual
└── reports/                         ← Output folder for generated PDF reports
```

---

## Quick Start

1. Copy `config/settings.py` and fill in your credentials
2. Install dependencies: `pip install fpdf2 playwright`
3. Run the full pipeline: `python scripts/05_full_pipeline.py`

See `docs/USER_MANUAL.md` for the full guide.
