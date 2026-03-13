"""Local-first SQLite data access layer.

All data stays on device. No cloud dependency.
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from .config import settings

_DB_PATH: Optional[str] = None


def _get_db_path() -> str:
    global _DB_PATH
    if _DB_PATH is None:
        _DB_PATH = settings.db_path
    return _DB_PATH


@contextmanager
def get_conn():
    """Get a SQLite connection with WAL mode for better concurrency."""
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database from migration SQL."""
    migration_path = Path(__file__).parent.parent / "migrations" / "001_local_schema.sql"
    sql = migration_path.read_text(encoding="utf-8")
    with get_conn() as conn:
        conn.executescript(sql)


def _gen_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ── Transactions ──


def insert_transactions(txs: list[dict], batch_id: str = "") -> int:
    """Bulk insert transactions (from CSV import)."""
    if not batch_id:
        batch_id = _gen_id("imp-")

    with get_conn() as conn:
        for tx in txs:
            conn.execute(
                """INSERT INTO transactions
                   (id, date, amount, tx_type, category, subcategory,
                    description, account_id, counterparty, source, tags,
                    ai_category_confidence, import_batch_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tx.get("id") or _gen_id("tx-"),
                    tx["date"],
                    tx["amount"],
                    tx.get("tx_type", "expense"),
                    tx.get("category", ""),
                    tx.get("subcategory", ""),
                    tx.get("description", ""),
                    tx.get("account_id", ""),
                    tx.get("counterparty", ""),
                    tx.get("source", ""),
                    json.dumps(tx.get("tags", []), ensure_ascii=False),
                    tx.get("ai_category_confidence", 0.0),
                    batch_id,
                ),
            )
    return len(txs)


def get_transactions(
    start_date: str = "",
    end_date: str = "",
    category: str = "",
    tx_type: str = "",
    limit: int = 500,
) -> list[dict]:
    """Query transactions with optional filters."""
    query = "SELECT * FROM transactions WHERE 1=1"
    params: list[Any] = []

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if category:
        query += " AND (category = ? OR category LIKE ?)"
        params.extend([category, f"{category}.%"])
    if tx_type:
        query += " AND tx_type = ?"
        params.append(tx_type)

    query += " ORDER BY date DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_monthly_summary(year_month: str = "") -> dict:
    """Get expense/income summary for a month. Default: current month."""
    if not year_month:
        year_month = date.today().strftime("%Y-%m")

    with get_conn() as conn:
        rows = conn.execute(
            """SELECT tx_type, category, SUM(amount) as total, COUNT(*) as count
               FROM transactions
               WHERE date LIKE ?
               GROUP BY tx_type, category
               ORDER BY total DESC""",
            (f"{year_month}%",),
        ).fetchall()

    summary = {"month": year_month, "expenses": [], "income": [], "total_expense": 0, "total_income": 0}
    for r in rows:
        row = dict(r)
        entry = {"category": row["category"], "total": row["total"], "count": row["count"]}
        if row["tx_type"] == "expense":
            summary["expenses"].append(entry)
            summary["total_expense"] += row["total"]
        elif row["tx_type"] == "income":
            summary["income"].append(entry)
            summary["total_income"] += row["total"]

    return summary


def get_category_monthly_avg(category: str, months: int = 3) -> float:
    """Get average monthly spend for a category over last N months."""
    end = date.today()
    start = end - timedelta(days=months * 30)

    with get_conn() as conn:
        row = conn.execute(
            """SELECT SUM(amount) as total
               FROM transactions
               WHERE tx_type = 'expense'
                 AND (category = ? OR category LIKE ?)
                 AND date >= ? AND date <= ?""",
            (category, f"{category}.%", start.isoformat(), end.isoformat()),
        ).fetchone()

    total = dict(row)["total"] or 0
    return round(total / months, 2)


# ── Accounts ──


def upsert_account(account: dict) -> str:
    acc_id = account.get("id") or _gen_id("acc-")
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO accounts
               (id, name, account_type, balance, currency, institution, is_asset, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                acc_id,
                account["name"],
                account.get("account_type", "cash"),
                account.get("balance", 0),
                account.get("currency", "CNY"),
                account.get("institution", ""),
                1 if account.get("is_asset", True) else 0,
                account.get("notes", ""),
            ),
        )
    return acc_id


def get_all_accounts() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM accounts").fetchall()
    return [dict(r) for r in rows]


# ── Assets ──


def upsert_asset(asset: dict) -> str:
    asset_id = asset.get("id") or _gen_id("ast-")
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO assets
               (id, name, asset_type, ticker, shares, cost_basis,
                current_value, last_updated, account_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                asset_id,
                asset["name"],
                asset.get("asset_type", ""),
                asset.get("ticker", ""),
                asset.get("shares", 0),
                asset.get("cost_basis", 0),
                asset.get("current_value", 0),
                asset.get("last_updated", datetime.now().isoformat()),
                asset.get("account_id", ""),
            ),
        )
    return asset_id


def get_all_assets() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM assets").fetchall()
    return [dict(r) for r in rows]


# ── Goals & Commitments ──


def upsert_goal(goal: dict) -> str:
    goal_id = goal.get("id") or _gen_id("goal-")
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO goals
               (id, title, target_amount, current_amount, deadline, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                goal_id,
                goal["title"],
                goal.get("target_amount"),
                goal.get("current_amount", 0),
                goal.get("deadline"),
                goal.get("status", "active"),
            ),
        )
    return goal_id


def get_active_goals() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM goals WHERE status = 'active' ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_commitment(commitment: dict) -> str:
    cid = commitment.get("id") or _gen_id("cmt-")
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO commitments
               (id, goal_id, action, category, expected_saving,
                start_date, end_date, status, follow_up_result, actual_saving)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cid,
                commitment.get("goal_id"),
                commitment["action"],
                commitment.get("category", ""),
                commitment.get("expected_saving", 0),
                commitment.get("start_date", date.today().isoformat()),
                commitment.get("end_date"),
                commitment.get("status", "active"),
                commitment.get("follow_up_result", ""),
                commitment.get("actual_saving", 0),
            ),
        )
    return cid


def get_active_commitments() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM commitments WHERE status = 'active' ORDER BY start_date DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ── User Profile ──


def set_profile(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO user_profile (key, value) VALUES (?, ?)",
            (key, value),
        )


def get_profile(key: str, default: str = "") -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM user_profile WHERE key = ?", (key,)).fetchone()
    return dict(row)["value"] if row else default


def get_full_profile() -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM user_profile").fetchall()
    return {r["key"]: r["value"] for r in rows}


# ── Categories ──


def get_categories() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return [dict(r) for r in rows]


# ── Conversations (短期记忆) ──


def save_message(role: str, content: str, tool_calls: list = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (id, role, content, tool_calls) VALUES (?, ?, ?, ?)",
            (_gen_id("msg-"), role, content, json.dumps(tool_calls or [])),
        )


def get_recent_messages(limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


# ── Habit Profile (中期记忆) ──


def update_habit(category: str, metric: str, value: Any, period: str = ""):
    with get_conn() as conn:
        habit_id = f"{category}:{metric}:{period}"
        conn.execute(
            """INSERT OR REPLACE INTO habit_profile (id, category, metric, value, period)
               VALUES (?, ?, ?, ?, ?)""",
            (habit_id, category, metric, json.dumps(value, ensure_ascii=False), period),
        )


def get_habits(category: str = "") -> list[dict]:
    with get_conn() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM habit_profile WHERE category = ?", (category,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM habit_profile").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["value"] = json.loads(d["value"])
        result.append(d)
    return result
