# Sparta Timesheet Approver — User Manual

**Version:** 1.0
**Date:** June 2026
**Prepared for:** Rail Delivery Group — QA Team
**Owner:** Carl Solomon

---

## What Is This?

Every fortnight, employees submit their timesheets through the **Sparta Global portal**. As the approving manager, you need to verify that the hours each employee has claimed match what they actually logged in **JIRA** — the project tracking tool where employees record their daily work.

This tool automates that entire process. Instead of manually logging into both systems and comparing numbers, the agent does it for you:

- Logs into Sparta and retrieves each pending timecard
- Pulls the employee's JIRA work logs directly from the JIRA system
- Applies a set of rules to decide whether to approve or reject
- Actions the decision inside Sparta (clicks Approve or Reject on your behalf)
- Produces a PDF audit report for every timecard — so there is always a documented record of what was checked and why a decision was made

---

## Prerequisites

Before using this tool, the following must be in place:

### 1. Sparta Account
You must have a Sparta Global manager account with permission to approve timecards.

- **Login URL:** https://customerspartaglobal.my.site.com/Client/s/login/
- **Username format:** `yourname@company.com.sparta`

### 2. JIRA Access
You need a JIRA account at **raildeliverygroup.atlassian.net** with read access to employee worklogs.

- **JIRA email:** your normal work email (e.g. `carl.solomon@raildeliverygroup.com`)
- **JIRA API token:** a personal access token generated from your Atlassian account. To create one:
  1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
  2. Click **Create API token**
  3. Give it a name (e.g. `Sparta Approver`) and copy the token
  4. Store it securely — you only see it once

### 3. Employee JIRA Account IDs
Each employee has a unique internal JIRA identifier (called an Account ID). This is different from their name or email. The tool needs this to look up their work logs.

For known employees, these are pre-stored in the configuration. When processing a new employee for the first time, you will need to look up their Account ID (the agent can do this automatically using their name).

### 4. Python Environment (if running scripts locally)
If running the pipeline scripts on your own machine:

```
Python 3.9 or later
pip install fpdf2 playwright
playwright install chromium
```

---

## How It Works — Step by Step

Every timecard goes through exactly **10 steps**, in order, without exception.

---

### Step 1 — Open the Timecard in Sparta

The agent navigates to the Sparta portal, goes to the **Timecards** menu, and opens the individual timecard record for the employee being reviewed.

---

### Step 2 — Screenshot the Timecard

A screenshot of the open timecard is taken and saved. This captures:
- The employee name
- The start and end date of the period
- The total hours submitted
- The project name

This screenshot forms part of the audit report.

---

### Step 3 — Extract the Key Details

The following information is read from the timecard:

| Field | Example |
|-------|---------|
| Employee name | Olayemi Ojo |
| Period start | 11/05/2026 |
| Period end | 17/05/2026 |
| Hours submitted to Sparta | 40.00 |
| Project | 20250814 - Rail Settlement Plan LTD |

---

### Step 4 — Find the Employee in JIRA

Using the employee's name, the agent looks up their unique JIRA Account ID. This is used in the next step to fetch their work logs.

---

### Step 5 — Pull JIRA Work Logs

The agent calls the **JIRA REST API** directly (not the JIRA website) to retrieve every work log entry the employee has made during the timecard period.

Each log entry returned includes:
- The date the work was logged
- The JIRA issue key (e.g. QDM-4941)
- The name/summary of the task
- The number of hours logged

This data is stored and used for the decision in the next step.

---

### Step 6 — Apply the Decision Rules

This is the core logic. The agent compares:

- **Sparta hours** — what the employee submitted
- **JIRA total hours** — everything logged in JIRA for that period
- **Leave / Holiday hours** — hours logged in JIRA against any task whose name contains the word `leave` or `holiday` (e.g. "Bank Holiday", "Annual Leave")

The following rules are applied in order:

---

#### ✅ APPROVE — Hours match, no leave or holiday in JIRA

> The employee submitted 40 hours. JIRA shows 40 hours. None of those hours are against a leave or holiday task.

Everything checks out. The timecard is approved.

---

#### ❌ REJECT — Hours match, but leave or holiday IS in JIRA

> The employee submitted 40 hours. JIRA shows 40 hours — but 8 of those hours are logged against "Bank Holiday".

This means the employee has included their bank holiday as billable hours. Leave time should not be submitted in Sparta. The timecard is rejected.

---

#### ✅ APPROVE — Hours don't match, but the gap is explained by leave

> The employee submitted 32 hours. JIRA shows 40 hours total — 8 of which are on a "Bank Holiday" task. The gap between JIRA and Sparta is exactly 8 hours.

The employee correctly excluded their leave from the Sparta submission. The gap is fully explained. The timecard is approved.

---

#### ❌ REJECT — Hours don't match and leave doesn't explain the gap

> The employee submitted 35 hours. JIRA shows 40 hours total — 8 are on "Annual Leave". The gap is 5 hours, but leave accounts for 8 hours.

The numbers don't add up. Something is inconsistent. The timecard is rejected.

---

### Decision Summary Table

| Sparta vs JIRA | Leave/Holiday in JIRA? | Gap = Leave Hours? | Decision |
|----------------|------------------------|-------------------|----------|
| Hours match | No | — | ✅ APPROVE |
| Hours match | Yes | — | ❌ REJECT |
| Hours differ | Yes | Yes | ✅ APPROVE |
| Hours differ | Yes | No | ❌ REJECT |

---

### Step 7 — Action the Decision in Sparta

Based on the outcome of Step 6, the agent clicks either the **Approve** or **Reject** button on the Sparta timecard page and confirms the action in the dialog that appears.

No manual intervention is needed. The decision is actioned automatically.

---

### Step 8 — Screenshot the Confirmation

Once the action is confirmed, a screenshot of the updated timecard page is taken. This captures the new status (Approved or Rejected) and serves as proof that the action was completed.

---

### Step 9 — Generate the Audit Report

A PDF audit report is automatically generated for every timecard processed. The report is named after the timecard ID, for example:

```
audit_TCH-05-14-2026-335964.pdf
```

The report contains four sections:

**Section 1 — Timecard Details**
A summary of the timecard: employee name, period, hours submitted, project, decision reached, and the date it was processed.

**Section 2 — JIRA Work Log Table**
Every JIRA log entry found for the employee and period, showing the date, issue key, task name, and hours. Any leave or holiday entries are highlighted.

**Section 3 — Hour Calculation**
A clear breakdown showing:
- Total hours logged in JIRA
- Hours logged against leave or holiday tasks
- Net project hours (JIRA total minus leave/holiday)
- Hours submitted in Sparta
- The gap between JIRA and Sparta
- Whether the gap is explained by leave

**Section 4 — Decision**
States the exact rule that was applied and the final decision, displayed prominently in green (APPROVED) or red (REJECTED).

The report is uploaded and a link is provided so it can be stored, shared, or reviewed at any time.

---

### Step 10 — Report Back

Once the audit report is generated and uploaded, the agent reports the outcome:
- The timecard ID
- The employee name and period
- The decision (APPROVED or REJECTED)
- A link to the PDF audit report

The agent then moves on to the next timecard and repeats all 10 steps. No timecards are batched or skipped.

---

## The Audit Log

In addition to the individual PDF reports, a running **Audit Log** is maintained in the GitHub repository (`AUDIT_LOG.md`). This is updated automatically every time a timecard is processed and contains a full history of every decision made, including:

- Date processed
- Timecard ID
- Employee name
- Period covered
- Sparta hours vs JIRA hours
- Leave/holiday hours identified
- Decision and rule applied

This provides a complete, searchable record for compliance or review purposes.

---

## Fortnightly Schedule

The tool is set to run on a **fortnightly cycle**:

- A **WhatsApp reminder** is sent to the manager every 14 days at 9am, prompting them to initiate the timecard processing run
- The **GitHub repository** (containing all scripts and this manual) is automatically synced every 14 days to ensure it stays up to date

---

## Who to Contact

For questions about this process or the tool itself:

**Carl Solomon**
carl.solomon@raildeliverygroup.com
Rail Delivery Group — QA Team

---

*End of User Manual*
