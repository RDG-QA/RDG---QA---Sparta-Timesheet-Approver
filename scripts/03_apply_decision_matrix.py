"""
Step 3 — Apply Decision Matrix
================================
Applies the agreed approval/rejection logic against JIRA worklog data
and the Sparta-reported hours.

Decision Matrix:
┌──────────────────────────────────────────────────────────┬───────────┐
│ Scenario                                                 │ Decision  │
├──────────────────────────────────────────────────────────┼───────────┤
│ JIRA total = Sparta, no leave/holiday tasks              │ APPROVE   │
│ JIRA total = Sparta, but leave/holiday task exists       │ REJECT    │
│ JIRA total ≠ Sparta, gap = leave/holiday hours           │ APPROVE   │
│ JIRA total ≠ Sparta, gap ≠ leave/holiday hours           │ REJECT    │
└──────────────────────────────────────────────────────────┴───────────┘

Usage (standalone):
    python scripts/03_apply_decision_matrix.py \
        --jira_total 40 --sparta_hours 32 --leave_hours 8
"""

import argparse
import sys

TOLERANCE = 0.01  # floating-point tolerance for hour comparison


def apply_matrix(jira_total: float, sparta_hours: float, leave_holiday_hours: float) -> dict:
    """
    Apply the decision matrix.

    Args:
        jira_total:           Total hours logged in JIRA for the period
        sparta_hours:         Hours reported in the Sparta timecard
        leave_holiday_hours:  Hours in JIRA against leave/holiday tasks

    Returns:
        {
            "decision":  "APPROVE" | "REJECT",
            "rule":      str,       # Human-readable rule that was applied
            "gap":       float,     # jira_total - sparta_hours
        }
    """
    gap = round(jira_total - sparta_hours, 2)
    hours_match = abs(gap) < TOLERANCE

    if hours_match and leave_holiday_hours < TOLERANCE:
        # Scenario 1: Equal hours, no leave/holiday → APPROVE
        decision = "APPROVE"
        rule = (
            f"JIRA total ({jira_total}h) equals Sparta ({sparta_hours}h) "
            f"and no leave/holiday tasks found."
        )

    elif hours_match and leave_holiday_hours >= TOLERANCE:
        # Scenario 2: Equal hours BUT leave/holiday task exists → REJECT
        decision = "REJECT"
        rule = (
            f"JIRA total ({jira_total}h) equals Sparta ({sparta_hours}h) "
            f"but leave/holiday task(s) totalling {leave_holiday_hours}h were found. "
            f"These must not be included in the submitted hours."
        )

    elif not hours_match and abs(abs(gap) - leave_holiday_hours) < TOLERANCE:
        # Scenario 3: Hours differ, but gap is exactly explained by leave/holiday → APPROVE
        decision = "APPROVE"
        rule = (
            f"JIRA total ({jira_total}h) differs from Sparta ({sparta_hours}h) by {abs(gap)}h. "
            f"This gap is fully accounted for by leave/holiday hours ({leave_holiday_hours}h)."
        )

    else:
        # Scenario 4: Hours differ and gap is NOT explained → REJECT
        decision = "REJECT"
        rule = (
            f"JIRA total ({jira_total}h) differs from Sparta ({sparta_hours}h) by {abs(gap)}h. "
            f"Leave/holiday hours ({leave_holiday_hours}h) do not fully explain this gap."
        )

    result = {"decision": decision, "rule": rule, "gap": gap}
    print(f"\n[MATRIX] Decision : {decision}")
    print(f"[MATRIX] Rule     : {rule}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply timecard decision matrix")
    parser.add_argument("--jira_total",    type=float, required=True)
    parser.add_argument("--sparta_hours",  type=float, required=True)
    parser.add_argument("--leave_hours",   type=float, required=True)
    args = parser.parse_args()

    result = apply_matrix(args.jira_total, args.sparta_hours, args.leave_hours)
    print("\n[OUTPUT]", result)
