"""Rule engine — parameterized rules with dynamic weights (V1.1 HITL).

V1 had 10 hardcoded if-else rules. V1.1 makes every rule parameterized:
each rule reads its thresholds and weight from the database, allowing the
learning cycle (learner.py) to auto-tune them based on user feedback.
"""

import hashlib
import json
import logging
from datetime import datetime, date
from typing import Any, Optional

from . import db

logger = logging.getLogger(__name__)

# ── Rule Severity Scores ──
SEVERITY_SCORES = {"critical": 40, "high": 25, "medium": 15, "low": 8}

# ── In-memory cache for rule params (refreshed per request) ──
_params_cache: dict[str, dict] = {}


def _load_params(rule_name: str, defaults: dict) -> dict:
    """Load rule params from DB, falling back to defaults."""
    if rule_name in _params_cache:
        return _params_cache[rule_name]

    params = dict(defaults)
    try:
        db_params = db.get_active_rule_params(rule_name)
        for p in db_params:
            val = p["param_value"]
            # param_value is stored as JSONB
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    pass
            params[p["param_name"]] = val
    except Exception:
        logger.warning("Failed to load DB params for %s, using defaults", rule_name)

    _params_cache[rule_name] = params
    return params


def _clear_cache():
    _params_cache.clear()


# ── Helper functions ──


def _is_weekend(d: str | date) -> bool:
    if isinstance(d, str):
        d = datetime.strptime(d[:10], "%Y-%m-%d").date()
    return d.weekday() >= 5  # Saturday=5, Sunday=6


CHINESE_HOLIDAYS_2026 = {
    # Simplified — in production, use a holiday API
    "2026-01-01", "2026-01-29", "2026-01-30", "2026-01-31",
    "2026-02-01", "2026-02-02", "2026-04-05", "2026-05-01",
    "2026-06-19", "2026-10-01", "2026-10-02", "2026-10-03",
}


def _is_holiday(d: str | date) -> bool:
    if isinstance(d, date):
        d = d.isoformat()
    return d[:10] in CHINESE_HOLIDAYS_2026


def _is_weekend_or_holiday(d: str | date) -> bool:
    return _is_weekend(d) or _is_holiday(d)


def _invoice_hash(invoice_number: str) -> str:
    return hashlib.sha256(invoice_number.encode()).hexdigest()[:16]


# ── Context helpers (query DB for aggregates) ──

# These are stubs — in production they query Supabase
_duplicate_hashes: set[str] = set()
_vendor_monthly_counts: dict[str, int] = {}
_same_day_vendor_counts: dict[str, int] = {}
_yearly_phone_counts: dict[str, int] = {}


def set_context(
    duplicate_hashes: set[str] | None = None,
    vendor_monthly_counts: dict[str, int] | None = None,
    same_day_vendor_counts: dict[str, int] | None = None,
    yearly_phone_counts: dict[str, int] | None = None,
):
    """Set aggregation context before rule evaluation.

    In production, this pulls from Redis/Supabase. For V1.1 MVP,
    the caller (main.py) computes these from recent audit_results.
    """
    global _duplicate_hashes, _vendor_monthly_counts
    global _same_day_vendor_counts, _yearly_phone_counts
    if duplicate_hashes is not None:
        _duplicate_hashes = duplicate_hashes
    if vendor_monthly_counts is not None:
        _vendor_monthly_counts = vendor_monthly_counts
    if same_day_vendor_counts is not None:
        _same_day_vendor_counts = same_day_vendor_counts
    if yearly_phone_counts is not None:
        _yearly_phone_counts = yearly_phone_counts


# ── Rule Definitions ──

RULES: dict[str, dict[str, Any]] = {
    "threshold_proximity": {
        "description": "金额接近审批阈值",
        "defaults": {
            "threshold": 50000,
            "proximity_pct": 0.02,
            "weight": 1.0,
            "min_weight": 0.3,
        },
        "severity": "high",
    },
    "weekend_invoice": {
        "description": "周末/节假日开具的发票",
        "defaults": {
            "weight": 1.0,
            "min_weight": 0.2,
        },
        "severity": "medium",
    },
    "vendor_frequency": {
        "description": "供应商月度出现频次异常",
        "defaults": {
            "max_monthly_count": 3,
            "weight": 1.0,
            "min_weight": 0.3,
        },
        "severity": "medium",
    },
    "round_amount": {
        "description": "整数金额（无零头）",
        "defaults": {
            "min_amount": 1000,
            "weight": 0.8,
            "min_weight": 0.2,
        },
        "severity": "low",
    },
    "duplicate_invoice": {
        "description": "发票号重复",
        "defaults": {
            "weight": 1.0,
            "min_weight": 1.0,  # Cannot be reduced
        },
        "severity": "critical",
    },
    "amount_mismatch": {
        "description": "凭证金额与报销金额不匹配",
        "defaults": {
            "tolerance_pct": 0.01,
            "weight": 1.0,
            "min_weight": 0.8,
        },
        "severity": "high",
    },
    "split_billing": {
        "description": "疑似拆单（同日同供应商多笔）",
        "defaults": {
            "max_same_day_vendor": 2,
            "weight": 1.0,
            "min_weight": 0.5,
        },
        "severity": "high",
    },
    "late_night_taxi": {
        "description": "深夜打车（22:00 后）无加班审批",
        "defaults": {
            "cutoff_hour": 22,
            "weight": 0.9,
            "min_weight": 0.3,
        },
        "severity": "medium",
    },
    "phone_limit": {
        "description": "手机号码年度额度超限",
        "defaults": {
            "max_phones_per_year": 2,
            "weight": 1.0,
            "min_weight": 0.5,
        },
        "severity": "high",
    },
    "invoice_expired": {
        "description": "发票超过有效报销期限",
        "defaults": {
            "max_days": 180,
            "weight": 1.0,
            "min_weight": 0.8,
        },
        "severity": "high",
    },
}


def _check_rule(rule_name: str, expense: dict, params: dict) -> bool:
    """Check if a specific rule is triggered for the given expense."""
    amount = expense.get("amount", 0)
    invoice_date = expense.get("invoice_date", "")
    invoice_number = expense.get("invoice_number", "")
    vendor = expense.get("vendor_name", "")
    expense_type = expense.get("expense_type", "")

    if rule_name == "threshold_proximity":
        threshold = params.get("threshold", 50000)
        proximity = params.get("proximity_pct", 0.02)
        lower = threshold * (1 - proximity)
        return lower <= amount < threshold

    elif rule_name == "weekend_invoice":
        return bool(invoice_date) and _is_weekend_or_holiday(invoice_date)

    elif rule_name == "vendor_frequency":
        max_count = params.get("max_monthly_count", 3)
        return _vendor_monthly_counts.get(vendor, 0) > max_count

    elif rule_name == "round_amount":
        min_amt = params.get("min_amount", 1000)
        return amount >= min_amt and amount == int(amount)

    elif rule_name == "duplicate_invoice":
        if not invoice_number:
            return False
        h = _invoice_hash(invoice_number)
        if h in _duplicate_hashes:
            return True
        _duplicate_hashes.add(h)
        return False

    elif rule_name == "amount_mismatch":
        claimed = expense.get("claimed_amount", amount)
        ocr_amount = expense.get("ocr_amount", amount)
        if claimed == 0:
            return False
        tolerance = params.get("tolerance_pct", 0.01)
        return abs(ocr_amount - claimed) / claimed > tolerance

    elif rule_name == "split_billing":
        max_count = params.get("max_same_day_vendor", 2)
        key = f"{invoice_date}_{vendor}"
        return _same_day_vendor_counts.get(key, 0) > max_count

    elif rule_name == "late_night_taxi":
        cutoff = params.get("cutoff_hour", 22)
        if expense_type != "transportation.taxi":
            return False
        expense_time = expense.get("expense_time", "")
        if not expense_time:
            return False
        try:
            hour = int(expense_time.split(":")[0])
        except (ValueError, IndexError):
            return False
        return hour >= cutoff and not expense.get("has_overtime_approval", False)

    elif rule_name == "phone_limit":
        if expense_type != "communication.phone":
            return False
        emp_id = expense.get("employee_id", "")
        max_phones = params.get("max_phones_per_year", 2)
        return _yearly_phone_counts.get(emp_id, 0) >= max_phones

    elif rule_name == "invoice_expired":
        if not invoice_date:
            return False
        max_days = params.get("max_days", 180)
        try:
            inv_date = datetime.strptime(invoice_date[:10], "%Y-%m-%d").date()
            delta = (date.today() - inv_date).days
            return delta > max_days
        except ValueError:
            return False

    return False


def _get_rule_confidence(rule_name: str) -> float:
    """Calculate rule confidence based on historical feedback."""
    try:
        stats = db.get_rule_feedback_stats()
        if rule_name in stats:
            s = stats[rule_name]
            total = s["agree"] + s["disagree"]
            if total >= 5:
                return round(s["agree"] / total, 2)
    except Exception:
        pass
    return 0.70  # Default when insufficient data


def evaluate(expense: dict) -> dict:
    """Evaluate all rules against an expense.

    Args:
        expense: Dict with keys like amount, invoice_date, vendor_name, etc.

    Returns:
        {
            "risk_level": "pass" | "warn" | "fail",
            "risk_score": 0-100,
            "triggered_rules": [
                {"rule": "...", "description": "...", "severity": "...",
                 "weight": 1.0, "score": 25, "confidence": 0.82}
            ]
        }
    """
    _clear_cache()

    triggered = []
    total_score = 0

    for rule_name, rule_def in RULES.items():
        params = _load_params(rule_name, rule_def["defaults"])

        if _check_rule(rule_name, expense, params):
            weight = max(
                params.get("weight", 1.0),
                params.get("min_weight", 0.0),
            )
            base_score = SEVERITY_SCORES.get(rule_def["severity"], 10)
            score = round(base_score * weight)
            confidence = _get_rule_confidence(rule_name)

            triggered.append({
                "rule": rule_name,
                "description": rule_def["description"],
                "severity": rule_def["severity"],
                "weight": weight,
                "score": score,
                "confidence": confidence,
            })
            total_score += score

    # Decision: PASS / WARN / FAIL
    risk_level = "pass"
    if any(t["severity"] == "critical" for t in triggered):
        risk_level = "fail"
    elif total_score >= 50:
        risk_level = "fail"
    elif total_score >= 20:
        risk_level = "warn"

    return {
        "risk_level": risk_level,
        "risk_score": min(total_score, 100),
        "triggered_rules": triggered,
    }


def get_current_params_snapshot() -> dict:
    """Get a snapshot of all current rule parameters for audit trail."""
    snapshot = {}
    for rule_name, rule_def in RULES.items():
        snapshot[rule_name] = _load_params(rule_name, rule_def["defaults"])
    return snapshot
