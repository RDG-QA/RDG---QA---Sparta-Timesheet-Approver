"""
Step 1 — Fetch Pending Timecards from Sparta
=============================================
Uses Playwright (browser automation) to log into the Sparta portal
and retrieve the list of timecards pending approval.

Returns a list of timecard records for downstream processing.

Dependencies:
    pip install playwright
    playwright install chromium

Usage:
    python scripts/01_fetch_pending_timecards.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import (
    SPARTA_LOGIN_URL, SPARTA_HOME_URL,
    SPARTA_USERNAME, SPARTA_PASSWORD,
    BROWSER_HEADLESS, BROWSER_SLOW_MO
)

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


def login_to_sparta(page) -> bool:
    """Navigate to Sparta login page and authenticate. Returns True on success."""
    print(f"[SPARTA] Navigating to login: {SPARTA_LOGIN_URL}")
    page.goto(SPARTA_LOGIN_URL)
    page.wait_for_load_state("networkidle")

    try:
        page.fill("input[type='email'], input[name*='user'], input[id*='user']", SPARTA_USERNAME)
        page.fill("input[type='password']", SPARTA_PASSWORD)
        page.click("button[type='submit'], input[type='submit']")
        page.wait_for_load_state("networkidle")
        print("[SPARTA] Login successful")
        return True
    except PlaywrightTimeout:
        print("[SPARTA] ERROR: Login timed out — check credentials or page structure")
        return False


def navigate_to_timecards(page):
    """Click the Timecards menu item from the Sparta home page."""
    print("[SPARTA] Navigating to Timecards menu")
    page.goto(SPARTA_HOME_URL)
    page.wait_for_load_state("networkidle")

    # Try clicking the Timecards nav link
    timecards_link = page.locator("text=Timecards").first
    timecards_link.click()
    page.wait_for_load_state("networkidle")
    print("[SPARTA] Timecards page loaded")


def get_pending_timecards(page) -> list:
    """
    Scrape the pending timecard records from the Timecards list view.
    Returns a list of dicts: [{id, resource, start_date, end_date, total_hours, project}, ...]
    """
    timecards = []
    rows = page.locator("table tbody tr, .slds-table tbody tr").all()

    for row in rows:
        cells = row.locator("td").all()
        if len(cells) < 4:
            continue
        tc = {
            "id": cells[0].inner_text().strip(),
            "resource": cells[1].inner_text().strip() if len(cells) > 1 else "",
            "start_date": cells[2].inner_text().strip() if len(cells) > 2 else "",
            "end_date": cells[3].inner_text().strip() if len(cells) > 3 else "",
            "total_hours": cells[4].inner_text().strip() if len(cells) > 4 else "",
            "status": cells[5].inner_text().strip() if len(cells) > 5 else "",
        }
        if tc["id"].startswith("TCH-"):
            timecards.append(tc)

    print(f"[SPARTA] Found {len(timecards)} pending timecards")
    for tc in timecards:
        print(f"  {tc['id']} | {tc['resource']} | {tc['start_date']} – {tc['end_date']} | {tc['total_hours']}h")
    return timecards


def open_timecard(page, timecard_id: str):
    """Click on a specific timecard by ID to open its detail view."""
    print(f"[SPARTA] Opening timecard: {timecard_id}")
    link = page.locator(f"text={timecard_id}").first
    link.click()
    page.wait_for_load_state("networkidle")


def take_screenshot(page, filename: str) -> str:
    """Take a screenshot of the current page. Returns the file path."""
    os.makedirs("reports", exist_ok=True)
    path = os.path.join("reports", filename)
    page.screenshot(path=path, full_page=True)
    print(f"[SPARTA] Screenshot saved: {path}")
    return path


def fetch_pending_timecards() -> list:
    """Full flow: login → navigate → fetch. Returns list of timecard dicts."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=BROWSER_HEADLESS, slow_mo=BROWSER_SLOW_MO)
        context = browser.new_context()
        page = context.new_page()

        if not login_to_sparta(page):
            browser.close()
            return []

        navigate_to_timecards(page)
        timecards = get_pending_timecards(page)
        browser.close()
        return timecards


if __name__ == "__main__":
    result = fetch_pending_timecards()
    print("\n[OUTPUT]")
    print(json.dumps(result, indent=2))
