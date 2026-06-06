"""
Step 5 — Full End-to-End Pipeline
===================================
Orchestrates the complete timecard approval workflow:

  1. Login to Sparta and fetch pending timecards
  2. For each timecard:
     a. Open the timecard record + screenshot
     b. Resolve the employee's JIRA account ID
     c. Pull JIRA worklogs for the timecard period
     d. Apply the decision matrix
     e. Action the decision in Sparta (Approve / Reject)
     f. Take confirmation screenshot
     g. Generate PDF audit report

Dependencies:
    pip install fpdf2 playwright
    playwright install chromium

Usage:
    python scripts/05_full_pipeline.py

    # Process a specific timecard only:
    python scripts/05_full_pipeline.py --timecard_id TCH-05-22-2026-337288

    # Dry run (no Sparta actions taken):
    python scripts/05_full_pipeline.py --dry_run
"""

import sys
import os
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import (
    SPARTA_LOGIN_URL, SPARTA_HOME_URL,
    SPARTA_USERNAME, SPARTA_PASSWORD,
    JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN,
    BROWSER_HEADLESS, BROWSER_SLOW_MO, REPORTS_OUTPUT_DIR
)
from scripts._02_pull_jira_worklogs import pull_worklogs, get_issues_for_account
from scripts._03_apply_decision_matrix import apply_matrix
from scripts._04_generate_audit_report import generate_report

# Re-import under expected module names
import importlib
pw = None  # Playwright instance, set at runtime

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

import base64
import urllib.request
import urllib.error


# ─── JIRA helpers ───────────────────────────────────────────────────────────

def jira_get(path: str) -> dict:
    creds = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    url = f"{JIRA_BASE_URL}{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Basic {creds}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"[JIRA] HTTP {e.code}: {e.read().decode()[:200]}")
        return {}


def resolve_jira_account_id(display_name: str) -> str:
    """Search JIRA for a user by display name and return their accountId."""
    data = jira_get(f"/rest/api/3/user/search?query={urllib.parse.quote(display_name)}&maxResults=5")
    if isinstance(data, list) and data:
        account_id = data[0]["accountId"]
        print(f"[JIRA] Resolved '{display_name}' → {account_id}")
        return account_id
    print(f"[JIRA] WARNING: Could not resolve account ID for '{display_name}'")
    return ""


# ─── Sparta browser actions ──────────────────────────────────────────────────

def login(page):
    print(f"[SPARTA] Logging in...")
    page.goto(SPARTA_LOGIN_URL)
    page.wait_for_load_state("networkidle")
    page.fill("input[type='email'], input[name*='user']", SPARTA_USERNAME)
    page.fill("input[type='password']", SPARTA_PASSWORD)
    page.click("button[type='submit'], input[type='submit']")
    page.wait_for_load_state("networkidle")
    print("[SPARTA] Logged in")


def go_home_then_timecards(page):
    page.goto(SPARTA_HOME_URL)
    page.wait_for_load_state("networkidle")
    page.locator("text=Timecards").first.click()
    page.wait_for_load_state("networkidle")


def open_timecard(page, timecard_id: str):
    page.locator(f"text={timecard_id}").first.click()
    page.wait_for_load_state("networkidle")


def screenshot(page, name: str) -> str:
    os.makedirs(REPORTS_OUTPUT_DIR, exist_ok=True)
    path = os.path.join(REPORTS_OUTPUT_DIR, name)
    page.screenshot(path=path, full_page=True)
    print(f"[SPARTA] Screenshot: {path}")
    return path


def action_decision(page, decision: str, dry_run: bool = False):
    """Click the Approve or Reject button, then confirm in the dialog."""
    if dry_run:
        print(f"[DRY RUN] Would click: {decision}")
        return
    btn_text = "Approve" if decision == "APPROVE" else "Reject"
    page.locator(f"text={btn_text}").first.click()
    page.wait_for_selector("text=Comments", timeout=10000)
    # Click the confirm button inside the dialog
    page.locator("button.slds-button--brand, button[class*='brand']").first.click()
    page.wait_for_load_state("networkidle")
    print(f"[SPARTA] {btn_text} actioned")


# ─── Timecard detail extraction ──────────────────────────────────────────────

def extract_timecard_details(page) -> dict:
    """Parse key fields from an open timecard page."""
    def safe_text(selector):
        try:
            return page.locator(selector).first.inner_text().strip()
        except Exception:
            return ""

    details = {
        "resource":    safe_text("text=Resource >> xpath=following-sibling::*[1]"),
        "start_date":  safe_text("text=Start Date >> xpath=following-sibling::*[1]"),
        "end_date":    safe_text("text=End Date >> xpath=following-sibling::*[1]"),
        "total_hours": safe_text("text=Total Hours >> xpath=following-sibling::*[1]"),
        "project":     safe_text("text=Project >> xpath=following-sibling::*[1]"),
    }
    return details


# ─── Main pipeline ───────────────────────────────────────────────────────────

import urllib.parse

KNOWN_ACCOUNT_IDS = {
    # Pre-populated from resolved lookups — add more as you process resources
    # "Full Name": "jira-account-id",
    "Olayemi Ojo":    "712020:2be049ef-fda2-4ad2-b0ef-79c20b203732",
    "Francis Adewale": "712020:b2cd1c38-c5b3-4ee2-9e9d-64fbd5e0c03c",
    "Raihan Kamal":   "712020:a7e14e54-8d5e-4c3a-b5f1-d2e8a0c9f123",
}


def parse_sparta_date(date_str: str) -> datetime:
    """Parse Sparta date formats: dd/mm/yyyy or dd-Mon-yyyy."""
    for fmt in ("%d/%m/%Y", "%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


def process_single_timecard(page, timecard_id: str, dry_run: bool = False) -> dict:
    """
    Full 10-step process for a single timecard.
    Returns a result dict with decision and report path.
    """
    print(f"\n{'='*60}")
    print(f"PROCESSING: {timecard_id}")
    print(f"{'='*60}")

    # Step 1 — Home → Timecards → Open record
    go_home_then_timecards(page)
    open_timecard(page, timecard_id)

    # Step 2 — Screenshot of open timecard
    sc_open = screenshot(page, f"{timecard_id}_open.png")

    # Step 3 — Extract timecard details
    details = extract_timecard_details(page)
    resource = details.get("resource", "Unknown")
    start_str = details.get("start_date", "")
    end_str = details.get("end_date", "")
    hours_str = details.get("total_hours", "0").replace(",", "")
    project = details.get("project", "")
    sparta_hours = float(hours_str) if hours_str else 0.0

    print(f"[SPARTA] Resource: {resource} | {start_str} – {end_str} | {sparta_hours}h")

    # Step 4 — Resolve JIRA account ID
    account_id = KNOWN_ACCOUNT_IDS.get(resource) or resolve_jira_account_id(resource)
    if not account_id:
        print(f"[ERROR] Cannot resolve JIRA account for '{resource}' — skipping")
        return {"timecard_id": timecard_id, "decision": "SKIPPED", "error": "No JIRA account ID"}

    # Step 5 — Pull JIRA worklogs
    start_dt = parse_sparta_date(start_str)
    end_dt = parse_sparta_date(end_str).replace(hour=23, minute=59, second=59)
    jira_data = pull_worklogs(account_id, start_dt, end_dt)

    # Step 6 — Apply decision matrix
    matrix_result = apply_matrix(
        jira_total=jira_data["total_hours"],
        sparta_hours=sparta_hours,
        leave_holiday_hours=jira_data["leave_holiday_hours"],
    )
    decision = matrix_result["decision"]

    # Step 7 — Action in Sparta
    action_decision(page, decision, dry_run=dry_run)

    # Step 8 — Confirmation screenshot
    sc_confirm = screenshot(page, f"{timecard_id}_confirmed.png")

    # Step 9 — Generate PDF audit report
    report_path = generate_report(
        timecard_id=timecard_id,
        resource=resource,
        period_start=start_str,
        period_end=end_str,
        sparta_hours=sparta_hours,
        project=project,
        decision=decision,
        rule=matrix_result["rule"],
        jira_logs=jira_data["logs"],
        jira_total=jira_data["total_hours"],
        leave_holiday_hours=jira_data["leave_holiday_hours"],
        project_hours=jira_data["project_hours"],
        gap=matrix_result["gap"],
        output_dir=REPORTS_OUTPUT_DIR,
    )

    result = {
        "timecard_id": timecard_id,
        "resource": resource,
        "period": f"{start_str} – {end_str}",
        "sparta_hours": sparta_hours,
        "jira_total": jira_data["total_hours"],
        "leave_holiday_hours": jira_data["leave_holiday_hours"],
        "decision": decision,
        "report_path": report_path,
    }

    # Step 10 — Report back
    print(f"\n[DONE] {timecard_id} → {decision}D | Report: {report_path}")
    return result


def run_pipeline(timecard_filter: str = None, dry_run: bool = False):
    """
    Main entry point.
    If timecard_filter is given, only that timecard ID is processed.
    """
    summary = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=BROWSER_HEADLESS, slow_mo=BROWSER_SLOW_MO)
        context = browser.new_context()
        page = context.new_page()

        login(page)
        go_home_then_timecards(page)

        if timecard_filter:
            timecard_ids = [timecard_filter]
        else:
            # Scrape pending IDs from the timecards list
            links = page.locator("a").all()
            timecard_ids = [
                l.inner_text().strip()
                for l in links
                if l.inner_text().strip().startswith("TCH-")
            ]
            print(f"\n[PIPELINE] Found {len(timecard_ids)} pending timecards: {timecard_ids}")

        for tc_id in timecard_ids:
            try:
                result = process_single_timecard(page, tc_id, dry_run=dry_run)
                summary.append(result)
            except Exception as e:
                print(f"[ERROR] Failed on {tc_id}: {e}")
                summary.append({"timecard_id": tc_id, "decision": "ERROR", "error": str(e)})

        browser.close()

    # ── Final Summary ──
    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE — SUMMARY")
    print(f"{'='*60}")
    for r in summary:
        status = r.get("decision", "?")
        print(f"  {r['timecard_id']:35} → {status}")
    print(f"\n{len(summary)} timecard(s) processed.")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sparta Timecard Approval Pipeline")
    parser.add_argument("--timecard_id", help="Process a single timecard ID only")
    parser.add_argument("--dry_run", action="store_true", help="Run without actioning in Sparta")
    args = parser.parse_args()

    run_pipeline(timecard_filter=args.timecard_id, dry_run=args.dry_run)
