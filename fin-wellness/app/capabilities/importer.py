"""CSV bill importer — supports Alipay, WeChat Pay, and generic bank exports.

Lazy mode: user dumps a CSV, we figure out the format and import.
"""

import csv
import io
import logging
import re
from datetime import datetime
from typing import Optional

from .. import db
from .classifier import classify_transaction

logger = logging.getLogger(__name__)


# ── Format Detection ──


def _detect_format(header: list[str]) -> str:
    """Detect CSV format from header row."""
    header_str = ",".join(header).lower()

    if "交易时间" in header_str and "商品说明" in header_str:
        return "alipay"
    if "交易时间" in header_str and "交易类型" in header_str and "商品" in header_str:
        return "wechat"
    if "transaction date" in header_str or "trans. date" in header_str:
        return "bank_en"

    # Generic: look for date-like and amount-like columns
    return "generic"


# ── Parsers ──


def _parse_amount(s: str) -> float:
    """Parse amount string, handling ¥, commas, and +/- signs."""
    s = s.strip().replace("¥", "").replace(",", "").replace(" ", "")
    if not s or s == "/":
        return 0.0
    return float(s)


def _parse_alipay(rows: list[dict]) -> list[dict]:
    """Parse Alipay (支付宝) CSV export."""
    transactions = []
    for row in rows:
        # Skip header/footer noise
        if not row.get("交易时间") or not row.get("金额"):
            continue

        amount = _parse_amount(row.get("金额", "0"))
        income_expense = row.get("收/支", "").strip()

        if income_expense == "收入":
            tx_type = "income"
        elif income_expense == "支出":
            tx_type = "expense"
        else:
            tx_type = "transfer"

        # Parse date
        date_str = row.get("交易时间", "").strip()[:10]

        description = row.get("商品说明", "").strip()
        counterparty = row.get("交易对方", "").strip()

        tx = {
            "date": date_str,
            "amount": abs(amount),
            "tx_type": tx_type,
            "description": description,
            "counterparty": counterparty,
            "source": "alipay_csv",
        }

        # Auto-classify
        category, confidence = classify_transaction(description, counterparty)
        tx["category"] = category
        tx["ai_category_confidence"] = confidence

        transactions.append(tx)

    return transactions


def _parse_wechat(rows: list[dict]) -> list[dict]:
    """Parse WeChat Pay (微信支付) CSV export."""
    transactions = []
    for row in rows:
        if not row.get("交易时间"):
            continue

        amount = _parse_amount(row.get("金额(元)", row.get("金额", "0")))
        income_expense = row.get("收/支", "").strip()

        if income_expense == "收入":
            tx_type = "income"
        elif income_expense == "支出":
            tx_type = "expense"
        else:
            tx_type = "transfer"

        date_str = row.get("交易时间", "").strip()[:10]
        description = row.get("商品", row.get("商品说明", "")).strip()
        counterparty = row.get("交易对方", "").strip()

        tx = {
            "date": date_str,
            "amount": abs(amount),
            "tx_type": tx_type,
            "description": description,
            "counterparty": counterparty,
            "source": "wechat_csv",
        }

        category, confidence = classify_transaction(description, counterparty)
        tx["category"] = category
        tx["ai_category_confidence"] = confidence

        transactions.append(tx)

    return transactions


def _parse_generic(rows: list[dict]) -> list[dict]:
    """Parse generic CSV with best-effort column mapping."""
    transactions = []

    # Try to find relevant columns
    if not rows:
        return []

    sample_keys = list(rows[0].keys())

    date_col = _find_column(sample_keys, ["日期", "date", "交易日期", "交易时间", "时间"])
    amount_col = _find_column(sample_keys, ["金额", "amount", "交易金额", "发生额"])
    desc_col = _find_column(sample_keys, ["描述", "摘要", "备注", "description", "memo", "商品说明"])
    type_col = _find_column(sample_keys, ["类型", "收支", "收/支", "type"])

    if not date_col or not amount_col:
        logger.warning("Cannot identify date/amount columns in generic CSV")
        return []

    for row in rows:
        date_str = row.get(date_col, "").strip()[:10]
        amount = _parse_amount(row.get(amount_col, "0"))
        description = row.get(desc_col, "").strip() if desc_col else ""

        tx_type = "expense"
        if type_col:
            t = row.get(type_col, "").strip()
            if "收" in t or "income" in t.lower():
                tx_type = "income"
            elif "转" in t or "transfer" in t.lower():
                tx_type = "transfer"
        elif amount > 0 and "收" not in description:
            tx_type = "expense"

        tx = {
            "date": date_str,
            "amount": abs(amount),
            "tx_type": tx_type,
            "description": description,
            "source": "generic_csv",
        }

        category, confidence = classify_transaction(description, "")
        tx["category"] = category
        tx["ai_category_confidence"] = confidence

        transactions.append(tx)

    return transactions


def _find_column(keys: list[str], candidates: list[str]) -> Optional[str]:
    """Find a column name from candidates."""
    for candidate in candidates:
        for key in keys:
            if candidate.lower() in key.lower():
                return key
    return None


# ── Main Import Function ──


def import_csv(file_content: str | bytes, source_hint: str = "") -> dict:
    """Import transactions from CSV content.

    Auto-detects format (Alipay, WeChat, generic).

    Args:
        file_content: CSV string or bytes
        source_hint: Optional hint like "alipay", "wechat"

    Returns:
        {"imported": 42, "format": "alipay", "batch_id": "imp-xxxx"}
    """
    if isinstance(file_content, bytes):
        # Try common encodings
        for enc in ["utf-8-sig", "utf-8", "gbk", "gb2312", "gb18030"]:
            try:
                file_content = file_content.decode(enc)
                break
            except UnicodeDecodeError:
                continue

    # Skip Alipay/WeChat metadata header lines
    lines = file_content.strip().split("\n")
    data_start = 0
    for i, line in enumerate(lines):
        if "," in line and not line.startswith("#") and not line.startswith("-"):
            # Check if this looks like a header row
            if any(kw in line for kw in ["交易时间", "日期", "date", "Date", "金额"]):
                data_start = i
                break
            # Or if previous attempts failed, start from here
            if i > 10:
                break

    csv_text = "\n".join(lines[data_start:])
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)

    if not rows:
        return {"imported": 0, "format": "empty", "error": "No data rows found"}

    # Detect format
    header = list(rows[0].keys())
    fmt = source_hint or _detect_format(header)

    # Parse
    if fmt == "alipay":
        transactions = _parse_alipay(rows)
    elif fmt == "wechat":
        transactions = _parse_wechat(rows)
    else:
        transactions = _parse_generic(rows)

    if not transactions:
        return {"imported": 0, "format": fmt, "error": "No valid transactions found"}

    # Insert
    batch_id = None
    count = db.insert_transactions(transactions)

    return {
        "imported": count,
        "format": fmt,
        "categories_auto": sum(1 for t in transactions if t.get("ai_category_confidence", 0) > 0.5),
        "date_range": f"{transactions[-1]['date']} ~ {transactions[0]['date']}" if transactions else "",
    }
