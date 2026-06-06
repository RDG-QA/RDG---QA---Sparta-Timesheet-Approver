# Sparta Timecard Approvals — User Manual

**Version:** 1.0  
**Date:** June 2026  
**Prepared by:** Sparta Timesheet Approvals Agent  
**Prepared for:** Carl Solomon, Rail Delivery Group

---

## Table of Contents

1. [Overview](#1-overview)
2. [How It Works — The 10-Step Process](#2-how-it-works)
3. [Decision Matrix](#3-decision-matrix)
4. [Repository Structure](#4-repository-structure)
5. [Prerequisites & Installation](#5-prerequisites--installation)
6. [Configuration](#6-configuration)
7. [Running the Pipeline](#7-running-the-pipeline)
8. [Understanding the Audit Report](#8-understanding-the-audit-report)
9. [Adding New Resources](#9-adding-new-resources)
10. [Troubleshooting](#10-troubleshooting)
11. [Security Notes](#11-security-notes)
12. [Glossary](#12-glossary)

---

## 1. Overview

This automation suite handles the end-to-end PM timecard review process for **Sparta Global** timesheets. Instead of manually comparing Sparta submissions against JIRA worklogs, the pipeline:

- Automatically logs into the Sparta portal
- Pulls the employee's JIRA worklogs directly via the JIRA REST API
- Applies a defined decision matrix to approve or reject each timecard
- Actions the decision inside Sparta (clicks Approve or Reject)
- Produces a PDF audit report for every timecard processed

**Key principle:** The JIRA REST API is always used for worklog data — never the JIRA browser interface. This ensures accuracy and a complete audit trail.

---

## 2. How It Works — The 10-Step Process

Every timecard follows exactly these 10 steps. No steps are skipped, no timecards are batched.

| Step | Action | Tool Used |
|------|--------|-----------|
| 1 | Navigate: Home → Timecards menu → Open timecard record | Sparta portal (browser) |
| 2 | Screenshot the open timecard | Browser automation |
| 3 | Extract timecard details (resource, period, hours, project) | Browser automation |
| 4 | Resolve the employee's JIRA account ID | JIRA REST API |
| 5 | Pull all JIRA worklogs for the timecard period | JIRA REST API |
| 6 | Apply the decision matrix (Approve or Reject logic) | Decision script |
| 7 | Action the decision in Sparta (click Approve or Reject + confirm) | Sparta portal (browser) |
| 8 | Screenshot the confirmation screen | Browser automation |
| 9 | Generate a PDF audit report | Report generator |
| 10 | Report back the outcome and provide the audit report link | Agent / output |

---

## 3. Decision Matrix

The following matrix is applied to every timecard. It compares:
- **Sparta hours** — the hours submitted by the employee in Sparta
- **JIRA total hours** — all hours logged in JIRA for that employee and period
- **JIRA leave/holiday hours** — hours logged against tasks containing the words `leave` or `holiday` in their name

| Scenario | Decision |
|----------|----------|
| JIRA total = Sparta AND no leave/holiday tasks in JIRA | ✅ **APPROVE** |
| JIRA total = Sparta BUT leave/holiday task exists in JIRA | ❌ **REJECT** |
| JIRA total ≠ Sparta AND the difference = leave/holiday hours | ✅ **APPROVE** (leave explains the gap) |
| JIRA total ≠ Sparta AND the difference ≠ leave/holiday hours | ❌ **REJECT** |

### Why reject when hours match but leave exists?

If an employee has logged 40 hours in JIRA including 8 hours of bank holiday, they should only submit 32 hours in Sparta (the non-leave hours). Submitting 40 hours means they are double-counting their leave time as billable hours.

### Example — APPROVE

| Item | Hours |
|------|-------|
| JIRA total | 40h |
| JIRA bank holiday (QDM-2848) | 8h |
| JIRA project hours | 32h |
| Sparta submitted | 32h |
| Gap | 8h |
| Gap = leave hours? | **YES → APPROVE** |

### Example — REJECT

| Item | Hours |
|------|-------|
| JIRA total | 40h |
| JIRA bank holiday | 8h |
| Sparta submitted | 40h ← includes leave |
| Gap | 0h |
| Leave/holiday exists? | **YES → REJECT** |

---

## 4. Repository Structure

```
sparta-timecard-approvals/
│
├── README.md                           ← Quick start guide
│
├── config/
│   └── settings.py                     ← All credentials and configuration
│
├── scripts/
│   ├── 01_fetch_pending_timecards.py   ← Login + list pending timecards
│   ├── 02_pull_jira_worklogs.py        ← JIRA REST API worklog fetch
│   ├── 03_apply_decision_matrix.py     ← Approval/rejection logic
│   ├── 04_generate_audit_report.py     ← PDF report generator
│   └── 05_full_pipeline.py             ← Full end-to-end orchestrator
│
├── docs/
│   └── USER_MANUAL.md                  ← This document
│
└── reports/                            ← Generated PDFs and screenshots
    ├── audit_TCH-05-22-2026-337288.pdf
    ├── TCH-05-22-2026-337288_open.png
    └── TCH-05-22-2026-337288_confirmed.png
```

---

## 5. Prerequisites & Installation

### Python

Requires Python 3.9 or later.

```bash
python --version
```

### Install dependencies

```bash
pip install fpdf2 playwright
playwright install chromium
```

| Package | Purpose |
|---------|---------|
| `fpdf2` | PDF audit report generation |
| `playwright` | Browser automation for the Sparta portal |

---

## 6. Configuration

Open `config/settings.py` and fill in your details:

```python
# Sparta credentials
SPARTA_USERNAME = "your.name@company.com.sparta"
SPARTA_PASSWORD = "your_password"

# JIRA credentials
JIRA_EMAIL     = "your.name@company.com"
JIRA_API_TOKEN = "your_jira_api_token"   # Generate at: id.atlassian.com/manage-profile/security/api-tokens
```

### Using environment variables (recommended for production)

Instead of hardcoding credentials, set them as environment variables:

```bash
export SPARTA_USERNAME="your.name@company.com.sparta"
export SPARTA_PASSWORD="your_password"
export JIRA_EMAIL="your.name@company.com"
export JIRA_API_TOKEN="your_jira_api_token"
```

The `settings.py` file is already configured to read these automatically via `os.environ.get(...)`.

### How to generate a JIRA API token

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **Create API token**
3. Give it a label (e.g. `sparta-timecard-automation`)
4. Copy the token and add it to your settings

---

## 7. Running the Pipeline

### Run the full pipeline (all pending timecards)

```bash
python scripts/05_full_pipeline.py
```

This will:
1. Log into Sparta and scrape all pending timecard IDs
2. Process each one end-to-end following the 10-step process
3. Print a summary table at the end
4. Save PDF reports to the `reports/` folder

### Process a single specific timecard

```bash
python scripts/05_full_pipeline.py --timecard_id TCH-05-22-2026-337288
```

### Dry run (no Sparta actions taken)

Useful for testing — all steps run but Approve/Reject is NOT clicked in Sparta.

```bash
python scripts/05_full_pipeline.py --dry_run
```

### Run individual steps

Each script can also be run standalone:

```bash
# Pull JIRA worklogs only
python scripts/02_pull_jira_worklogs.py \
  --account_id "712020:2be049ef-xxxx" \
  --start "2026-05-18" \
  --end "2026-05-24"

# Test the decision matrix
python scripts/03_apply_decision_matrix.py \
  --jira_total 40 --sparta_hours 32 --leave_hours 8

# Generate a test PDF report
python scripts/04_generate_audit_report.py
```

---

## 8. Understanding the Audit Report

Each processed timecard produces a PDF in the `reports/` folder, named:

```
audit_TCH-05-22-2026-337288.pdf
```

The report contains four sections:

### Section 1 — Timecard Details
Key metadata: timecard ID, resource name, period, Sparta hours, project, decision, approver, and processing date.

### Section 2 — JIRA Worklog Table
Every worklog entry found in JIRA for the employee and period, showing:
- Date logged
- JIRA issue key (e.g. QDM-4941)
- Task summary
- Hours logged
- Leave/holiday entries are highlighted in **pink**

### Section 3 — Hour Calculation
A clear breakdown showing:
- Total JIRA hours
- Leave/Holiday hours
- Project hours (JIRA total minus leave/holiday)
- Sparta submitted hours
- Gap between JIRA total and Sparta
- Whether the gap is explained by leave/holiday

### Section 4 — Decision
States the exact rule applied and the final decision in large green (APPROVED) or red (REJECTED) text.

---

## 9. Adding New Resources

When processing a new employee for the first time, their JIRA account ID must be resolved. There are two ways:

### Option A — Pre-populate the lookup table

Open `scripts/05_full_pipeline.py` and add the employee to `KNOWN_ACCOUNT_IDS`:

```python
KNOWN_ACCOUNT_IDS = {
    "Olayemi Ojo":    "712020:2be049ef-fda2-4ad2-b0ef-79c20b203732",
    "Francis Adewale": "712020:b2cd1c38-c5b3-4ee2-9e9d-64fbd5e0c03c",
    "Raihan Kamal":   "712020:a7e14e54-8d5e-4c3a-b5f1-d2e8a0c9f123",
    "New Employee":   "712020:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  # ← Add here
}
```

### Option B — Auto-resolve via JIRA API

If the name is not in the lookup table, the pipeline will automatically search for the employee by name in JIRA. This works as long as their display name in Sparta exactly matches their JIRA display name.

### Finding a JIRA account ID manually

```bash
curl -u "your.email@company.com:YOUR_API_TOKEN" \
  "https://raildeliverygroup.atlassian.net/rest/api/3/user/search?query=Employee+Name"
```

Look for the `accountId` field in the response.

---

## 10. Troubleshooting

### "Login timed out" / Sparta page not loading
- Check that `SPARTA_USERNAME` and `SPARTA_PASSWORD` are correct
- Try setting `BROWSER_HEADLESS = False` in `settings.py` to watch the browser
- Increase `BROWSER_SLOW_MO` (e.g. to `1000`) if the page is slow to load

### "Cannot resolve JIRA account ID"
- Manually find the account ID (see Section 9) and add it to `KNOWN_ACCOUNT_IDS`
- Check that the employee's name in Sparta exactly matches their JIRA display name

### "HTTP 401" from JIRA API
- Your JIRA API token has expired or is incorrect
- Regenerate at: https://id.atlassian.com/manage-profile/security/api-tokens

### "HTTP 403 — Insufficient scopes" on email send
- The Gmail/Outlook connector needs to be reconnected with send permissions

### No timecards found
- Make sure you are logged in as the correct approver user in Sparta
- Timecards are only shown if they are assigned to your approval queue

### PDF not generated
- Ensure `fpdf2` is installed: `pip install fpdf2`
- Check the `reports/` directory exists (it is created automatically)

---

## 11. Security Notes

- **Never commit credentials** to version control. Use environment variables.
- The `config/settings.py` file is included in `.gitignore` by default.
- JIRA API tokens should be rotated periodically (recommended: every 90 days).
- Sparta passwords should follow your organisation's password policy.
- Audit report PDFs may contain employee work data — store them securely and in line with your data retention policy.

---

## 12. Glossary

| Term | Definition |
|------|-----------|
| **Sparta** | The Sparta Global client portal used for timecard submission and approval |
| **JIRA** | The project management tool where employees log their daily work hours |
| **Worklog** | A JIRA time entry logged by an employee against a specific JIRA issue |
| **Timecard** | A weekly submission in Sparta recording total hours worked |
| **Account ID** | The unique JIRA identifier for a user (format: `712020:xxxxxxxx-...`) |
| **Leave/Holiday hours** | Hours logged in JIRA against tasks containing the word `leave` or `holiday` |
| **Gap** | The difference between JIRA total hours and Sparta submitted hours |
| **Audit Report** | A PDF document recording the full verification process and decision for a timecard |
| **TCH-** | Prefix for all Sparta timecard IDs |
| **QDM-** | Common JIRA issue key prefix used by the Rail Delivery Group project |
| **PM Approves Timecard** | The Sparta workflow step where the PM (Carl Solomon) reviews and actions the submission |

---

*End of User Manual*

*For questions or issues, contact the system owner: carl.solomon@raildeliverygroup.com*
