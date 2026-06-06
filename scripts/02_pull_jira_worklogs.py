"""
Step 2 — Pull JIRA Worklogs
============================
Fetches all worklogs for a given JIRA account ID within a date range.
Returns structured data including leave/holiday classification.

Usage (standalone):
    python scripts/02_pull_jira_worklogs.py \
        --account_id "712020:xxxxx" \
        --start "2026-05-18" \
        --end "2026-05-24"
"""

import json
import base64
import urllib.request
import urllib.error
from datetime import datetime
import argparse
import sys
import os

# Allow running standalone or imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import (
    JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, LEAVE_HOLIDAY_KEYWORDS
)


def get_credentials() -> str:
    """Return Base64-encoded Basic Auth credentials."""
    raw = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
    return base64.b64encode(raw.encode()).decode()


def jira_request(url: str, payload: dict = None) -> dict:
    """Make a JIRA REST API request. GET if no payload, POST if payload provided."""
    credentials = get_credentials()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"[JIRA] HTTP {e.code} on {url}: {e.read().decode()}")
        return {}


def get_issues_for_account(account_id: str) -> dict:
    """Return {issue_key: summary} for all issues the account has logged work on."""
    url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"
    payload = {
        "jql": f"worklogAuthor = '{account_id}'",
        "fields": ["summary"],
        "maxResults": 100,
    }
    data = jira_request(url, payload)
    return {
        issue["key"]: issue["fields"]["summary"]
        for issue in data.get("issues", [])
    }


def get_worklogs_for_issue(issue_key: str) -> list:
    """Return all worklogs for a given issue."""
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/worklog?maxResults=200"
    data = jira_request(url)
    return data.get("worklogs", [])


def is_leave_or_holiday(summary: str) -> bool:
    """Return True if the task summary matches leave/holiday keywords."""
    summary_lower = summary.lower()
    return any(kw in summary_lower for kw in LEAVE_HOLIDAY_KEYWORDS)


def pull_worklogs(account_id: str, start_date: datetime, end_date: datetime) -> dict:
    """
    Pull all JIRA worklogs for `account_id` within [start_date, end_date].

    Returns:
        {
            "logs": [{"date", "issue", "summary", "hours", "is_leave_holiday"}, ...],
            "total_hours": float,
            "leave_holiday_hours": float,
            "project_hours": float,
        }
    """
    print(f"\n[JIRA] Fetching issues for account: {account_id}")
    issues = get_issues_for_account(account_id)
    print(f"[JIRA] Found {len(issues)} issues to scan")

    logs = []
    for issue_key, summary in issues.items():
        worklogs = get_worklogs_for_issue(issue_key)
        for wl in worklogs:
            author_id = wl.get("author", {}).get("accountId", "")
            if author_id != account_id:
                continue
            started = datetime.fromisoformat(wl["started"][:19])
            if not (start_date <= started <= end_date):
                continue
            hours = wl["timeSpentSeconds"] / 3600
            logs.append({
                "date": started.strftime("%d/%m/%Y"),
                "issue": issue_key,
                "summary": summary,
                "hours": round(hours, 2),
                "is_leave_holiday": is_leave_or_holiday(summary),
            })

    logs.sort(key=lambda x: x["date"])
    total_hours = sum(l["hours"] for l in logs)
    leave_holiday_hours = sum(l["hours"] for l in logs if l["is_leave_holiday"])
    project_hours = total_hours - leave_holiday_hours

    print(f"\n[JIRA] Worklogs ({start_date.date()} to {end_date.date()}):")
    for log in logs:
        tag = " *** LEAVE/HOLIDAY ***" if log["is_leave_holiday"] else ""
        print(f"  {log['date']} | {log['issue']} | {log['hours']}h | {log['summary'][:60]}{tag}")
    print(f"\n  Total JIRA hours      : {round(total_hours, 2)}")
    print(f"  Leave/Holiday hours   : {round(leave_holiday_hours, 2)}")
    print(f"  Project hours         : {round(project_hours, 2)}")

    return {
        "logs": logs,
        "total_hours": round(total_hours, 2),
        "leave_holiday_hours": round(leave_holiday_hours, 2),
        "project_hours": round(project_hours, 2),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pull JIRA worklogs for a user/period")
    parser.add_argument("--account_id", required=True, help="JIRA account ID")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    args = parser.parse_args()

    start_dt = datetime.strptime(args.start, "%Y-%m-%d")
    end_dt = datetime.strptime(args.end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    result = pull_worklogs(args.account_id, start_dt, end_dt)
    print("\n[OUTPUT]", json.dumps(result, indent=2))
