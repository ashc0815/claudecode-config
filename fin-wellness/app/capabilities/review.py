"""Weekly review generator — the Follow-up step of the core loop.

Generates a structured weekly financial review:
- What happened this week (numbers from data, not AI)
- How commitments went (celebrate wins, no judgment on misses)
- Any anomalies worth noting
- One suggestion for next week
"""

from datetime import date, timedelta

from .. import db
from .anomaly import detect_anomalies


def generate_weekly_review() -> dict:
    """Generate a weekly financial review.

    Returns structured data — the AI orchestrator turns this into
    a warm, encouraging message.
    """
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)             # Sunday

    # ── This week's transactions ──
    txs = db.get_transactions(
        start_date=week_start.isoformat(),
        end_date=week_end.isoformat(),
    )

    total_income = sum(t["amount"] for t in txs if t.get("tx_type") == "income")
    total_expense = sum(t["amount"] for t in txs if t.get("tx_type") == "expense")

    # Top expense categories this week
    category_totals: dict[str, float] = {}
    for t in txs:
        if t.get("tx_type") == "expense":
            cat = t.get("category", "未分类") or "未分类"
            category_totals[cat] = category_totals.get(cat, 0) + t["amount"]

    top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]

    # ── Commitment follow-up ──
    commitments = db.get_active_commitments()
    commitment_reviews = []
    for cmt in commitments:
        start = cmt.get("start_date", "")
        if start and start <= week_end.isoformat():
            # Check if the related category spending changed
            category = cmt.get("category", "")
            expected = cmt.get("expected_saving", 0)

            # Simple check: did spending in this category go down this week?
            category_spend = category_totals.get(category, 0)
            avg_weekly = db.get_category_monthly_avg(category, months=3) / 4.3 if category else 0

            actual_saving = max(0, round(avg_weekly - category_spend, 0))

            commitment_reviews.append({
                "action": cmt.get("action", ""),
                "category": category,
                "expected_saving": expected,
                "actual_saving": actual_saving,
                "improved": category_spend < avg_weekly if avg_weekly > 0 else None,
                "commitment_id": cmt.get("id", ""),
            })

    # ── Anomalies (monthly, but shown in weekly context) ──
    month = today.strftime("%Y-%m")
    anomalies = detect_anomalies(year_month=month, threshold_pct=20)

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "total_income": round(total_income, 0),
        "total_expense": round(total_expense, 0),
        "net_flow": round(total_income - total_expense, 0),
        "top_categories": [
            {"category": cat, "amount": round(amt, 0)}
            for cat, amt in top_categories
        ],
        "transaction_count": len(txs),
        "commitment_reviews": commitment_reviews,
        "anomalies": anomalies[:3],  # Max 3 to avoid overwhelm
    }
