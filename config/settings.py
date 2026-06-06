"""
Sparta Timecard Approvals — Configuration
==========================================
Fill in your credentials and settings below before running any scripts.
Store this file securely — never commit credentials to version control.
Use environment variables in production (see comments).
"""

import os

# ─────────────────────────────────────────────
# SPARTA PORTAL
# ─────────────────────────────────────────────
SPARTA_LOGIN_URL   = "https://customerspartaglobal.my.site.com/Client/s/login/"
SPARTA_HOME_URL    = "https://customerspartaglobal.my.site.com/Client/s/"
SPARTA_USERNAME    = os.environ.get("SPARTA_USERNAME", "your.username@company.com.sparta")
SPARTA_PASSWORD    = os.environ.get("SPARTA_PASSWORD", "your_password_here")

# ─────────────────────────────────────────────
# JIRA
# ─────────────────────────────────────────────
JIRA_BASE_URL      = "https://raildeliverygroup.atlassian.net"
JIRA_EMAIL         = os.environ.get("JIRA_EMAIL", "your.email@company.com")
JIRA_API_TOKEN     = os.environ.get("JIRA_API_TOKEN", "your_jira_api_token_here")

# ─────────────────────────────────────────────
# KEYWORDS — tasks matching these are treated as Leave/Holiday
# ─────────────────────────────────────────────
LEAVE_HOLIDAY_KEYWORDS = ["leave", "holiday", "bank holiday"]

# ─────────────────────────────────────────────
# REPORT OUTPUT
# ─────────────────────────────────────────────
REPORTS_OUTPUT_DIR = "reports"

# ─────────────────────────────────────────────
# BROWSER (Playwright)
# ─────────────────────────────────────────────
BROWSER_HEADLESS   = True   # Set False to watch the browser during debugging
BROWSER_SLOW_MO    = 500    # Milliseconds between actions (increase if Sparta is slow)
