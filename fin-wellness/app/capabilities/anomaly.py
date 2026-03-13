"""Anomaly detection — find unusual spending patterns.

Not about "you spent too much" — about "here's something different from your usual pattern."
Tone: curious, not judgmental.
"""

import logging
from datetime import date, timedelta

from .. import db

logger = logging.getLogger(__name__)


def detect_anomalies(year_month: str = "", threshold_pct: float = 25) -> list[dict]:
    """Detect categories where spending deviates from historical average.

    Args:
        year_month: Month to analyze (default: current month)
        threshold_pct: Minimum % deviation to flag (default: 25%)

    Returns:
        List of anomalies, each with:
        - category, current_amount, avg_amount, deviation_pct
        - direction: "higher" or "lower"
    """
    if not year_month:
        year_month = date.today().strftime("%Y-%m")

    # Get this month's summary
    summary = db.get_monthly_summary(year_month)
    anomalies = []

    for entry in summary.get("expenses", []):
        category = entry["category"]
        current = entry["total"]

        if not category or current < 10:  # Skip trivial amounts
            continue

        # Get historical average (last 3 months, excluding current)
        avg = db.get_category_monthly_avg(category, months=3)

        if avg < 10:  # No meaningful history
            continue

        deviation_pct = ((current - avg) / avg) * 100

        if abs(deviation_pct) >= threshold_pct:
            direction = "higher" if deviation_pct > 0 else "lower"
            anomalies.append({
                "category": category,
                "current_amount": round(current, 0),
                "avg_amount": round(avg, 0),
                "deviation_pct": round(deviation_pct, 1),
                "direction": direction,
                "count": entry["count"],
            })

    # Sort by absolute deviation (most unusual first)
    anomalies.sort(key=lambda x: abs(x["deviation_pct"]), reverse=True)

    return anomalies


def get_category_trend(category: str, months: int = 6) -> list[dict]:
    """Get monthly spending trend for a specific category.

    Used by AI to explain WHY something changed.
    e.g. "外卖在加班月份明显增加"
    """
    trend = []
    today = date.today()

    for i in range(months):
        # Go back i months
        target = today.replace(day=1) - timedelta(days=i * 30)
        ym = target.strftime("%Y-%m")

        summary = db.get_monthly_summary(ym)
        amount = 0
        count = 0
        for entry in summary.get("expenses", []):
            if entry["category"] == category or entry["category"].startswith(f"{category}."):
                amount += entry["total"]
                count += entry["count"]

        trend.append({
            "month": ym,
            "amount": round(amount, 0),
            "count": count,
        })

    trend.reverse()  # Oldest first
    return trend
