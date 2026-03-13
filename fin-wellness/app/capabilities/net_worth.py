"""Net worth calculator — one number to see the full picture.

The core insight: users track expenses but never see their overall financial position.
Net Worth = Total Assets - Total Liabilities

This is the "看得懂" solution: stop staring at individual transactions,
zoom out to see if you're moving in the right direction.
"""

from datetime import date

from .. import db


def calculate_net_worth() -> dict:
    """Calculate current net worth from all accounts and assets.

    Returns:
        {
            "date": "2026-03-13",
            "net_worth": 152000,
            "total_assets": 200000,
            "total_liabilities": 48000,
            "breakdown": {
                "cash_and_savings": 50000,
                "investments": 150000,
                "credit_card_debt": -8000,
                "loans": -40000,
            },
            "accounts": [...]
        }
    """
    accounts = db.get_all_accounts()
    assets = db.get_all_assets()

    total_assets = 0.0
    total_liabilities = 0.0
    breakdown = {
        "cash_and_savings": 0.0,
        "investments": 0.0,
        "credit_card_debt": 0.0,
        "loans": 0.0,
        "other_assets": 0.0,
    }

    account_details = []

    for acc in accounts:
        balance = acc.get("balance", 0)
        acc_type = acc.get("account_type", "other")
        is_asset = acc.get("is_asset", 1)

        if is_asset:
            total_assets += balance
            if acc_type in ("cash", "savings"):
                breakdown["cash_and_savings"] += balance
            else:
                breakdown["other_assets"] += balance
        else:
            total_liabilities += abs(balance)
            if acc_type == "credit_card":
                breakdown["credit_card_debt"] -= abs(balance)
            elif acc_type == "loan":
                breakdown["loans"] -= abs(balance)

        account_details.append({
            "name": acc.get("name", ""),
            "type": acc_type,
            "balance": balance,
            "is_asset": bool(is_asset),
        })

    # Add investment assets
    for asset in assets:
        value = asset.get("current_value", 0)
        total_assets += value
        breakdown["investments"] += value

    net_worth = total_assets - total_liabilities

    return {
        "date": date.today().isoformat(),
        "net_worth": round(net_worth, 2),
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "breakdown": {k: round(v, 2) for k, v in breakdown.items()},
        "accounts": account_details,
    }
