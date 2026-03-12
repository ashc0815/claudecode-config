"""SAP Concur API connector — OAuth2 auth + expense/receipt CRUD.

OpenClaw sits BETWEEN employee and Concur:
  Employee uploads voucher
    → OpenClaw validates (OCR + Rules + AI)
    → PASS/WARN-approved: push to Concur via API
    → Concur handles approval flow (manager → finance → payment)
    → OpenClaw pulls back approved data for post-audit reconciliation

Concur REST API v4 reference:
  - Expense Reports: /api/v3.0/expense/reports
  - Expense Entries: /api/v3.0/expense/entries
  - Receipt Images: /api/v3.0/expense/receiptimages
  - OAuth2: /oauth2/v0/token
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from .config import settings

logger = logging.getLogger(__name__)

# ── OAuth2 Token Management ──

_token_cache: dict[str, Any] = {
    "access_token": None,
    "expires_at": None,
    "refresh_token": None,
}

CONCUR_BASE_URL = "https://us.api.concursolutions.com"
CONCUR_AUTH_URL = "https://us.api.concursolutions.com/oauth2/v0/token"


async def _get_access_token() -> str:
    """Get a valid OAuth2 access token, refreshing if expired."""
    now = datetime.now(timezone.utc)

    if _token_cache["access_token"] and _token_cache["expires_at"] and now < _token_cache["expires_at"]:
        return _token_cache["access_token"]

    # Refresh token flow
    async with httpx.AsyncClient(timeout=15.0) as client:
        payload = {
            "grant_type": "refresh_token",
            "client_id": settings.concur_client_id,
            "client_secret": settings.concur_client_secret,
            "refresh_token": settings.concur_refresh_token,
        }
        resp = await client.post(CONCUR_AUTH_URL, data=payload)
        resp.raise_for_status()
        data = resp.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["refresh_token"] = data.get("refresh_token", _token_cache["refresh_token"])
    _token_cache["expires_at"] = now + timedelta(seconds=data.get("expires_in", 3600) - 60)

    logger.info("Concur OAuth2 token refreshed, expires at %s", _token_cache["expires_at"])
    return _token_cache["access_token"]


async def _concur_request(method: str, path: str, **kwargs) -> dict:
    """Make an authenticated request to Concur API."""
    token = await _get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    headers.update(kwargs.pop("headers", {}))

    url = f"{CONCUR_BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(method, url, headers=headers, **kwargs)
        resp.raise_for_status()
        if resp.status_code == 204:
            return {}
        return resp.json()


# ═══════════════════════════════════════════════
# PHASE 1: 上行 — OpenClaw → Concur（事前审核通过后）
# ═══════════════════════════════════════════════


async def create_expense_report(
    employee_login_id: str,
    report_name: str,
    policy_id: str = "",
    currency_code: str = "CNY",
) -> dict:
    """Create a new expense report in Concur.

    Called when OpenClaw审核通过 (PASS) or 财务人工通过 (WARN→approved).
    """
    payload = {
        "Name": report_name,
        "CurrencyCode": currency_code,
    }
    if policy_id:
        payload["PolicyID"] = policy_id

    result = await _concur_request(
        "POST",
        "/api/v3.0/expense/reports",
        json=payload,
    )
    logger.info("Created Concur report: %s", result.get("ID"))
    return result


async def create_expense_entry(
    report_id: str,
    expense_data: dict,
) -> dict:
    """Create an expense entry within a Concur report.

    Maps OpenClaw's structured OCR output to Concur's expense fields.

    Args:
        report_id: Concur report ID
        expense_data: OpenClaw structured data from OCR + audit
            {
                "amount": 4999.00,
                "currency": "CNY",
                "vendor_name": "XX餐饮公司",
                "invoice_date": "2026-03-10",
                "expense_type": "meals",
                "invoice_number": "INV-2026-0312",
                "risk_level": "pass",
                "risk_score": 12,
                "audit_id": "AUD-xxx"
            }
    """
    # Map OpenClaw expense_type to Concur ExpenseTypeCode
    type_mapping = {
        "meals": "DINNR",
        "transportation.taxi": "TAXIX",
        "transportation.train": "TRAIN",
        "transportation.flight": "AIRFR",
        "hotel": "LODNG",
        "office_supplies": "OFFIC",
        "communication.phone": "PHONE",
        "entertainment": "ENTMN",
        "other": "MISCL",
    }

    concur_type = type_mapping.get(
        expense_data.get("expense_type", "other"), "MISCL"
    )

    payload = {
        "ReportID": report_id,
        "TransactionAmount": expense_data.get("amount", 0),
        "TransactionCurrencyCode": expense_data.get("currency", "CNY"),
        "TransactionDate": expense_data.get("invoice_date", ""),
        "VendorDescription": expense_data.get("vendor_name", ""),
        "ExpenseTypeCode": concur_type,
        "Comment": _build_audit_comment(expense_data),
        # Custom fields for OpenClaw audit metadata
        "Custom1": expense_data.get("audit_id", ""),         # OpenClaw 审计ID
        "Custom2": expense_data.get("risk_level", ""),        # 风险等级
        "Custom3": str(expense_data.get("risk_score", 0)),    # 风险评分
        "Custom4": expense_data.get("invoice_number", ""),    # 发票号
    }

    result = await _concur_request(
        "POST",
        "/api/v3.0/expense/entries",
        json=payload,
    )
    logger.info("Created Concur entry: %s in report %s", result.get("ID"), report_id)
    return result


async def upload_receipt_image(
    entry_id: str,
    image_bytes: bytes,
    content_type: str = "image/jpeg",
) -> dict:
    """Upload receipt/invoice image to Concur and attach to expense entry."""
    token = await _get_access_token()

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{CONCUR_BASE_URL}/api/v3.0/expense/receiptimages",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": content_type,
                "Accept": "application/json",
            },
            content=image_bytes,
        )
        resp.raise_for_status()
        image_result = resp.json()

    image_id = image_result.get("ID", "")
    if image_id and entry_id:
        # Attach image to entry
        await _concur_request(
            "PUT",
            f"/api/v3.0/expense/entries/{entry_id}",
            json={"ReceiptImageID": image_id},
        )

    return image_result


async def submit_report(report_id: str) -> dict:
    """Submit a report into the Concur approval workflow.

    After this, the report goes through:
    Manager approval → Finance approval → Payment
    """
    result = await _concur_request(
        "POST",
        f"/api/v3.0/expense/reports/{report_id}/submit",
        json={"Comment": "Submitted via OpenClaw after AI audit"},
    )
    logger.info("Submitted Concur report %s to approval flow", report_id)
    return result


async def push_to_concur(
    expense_data: dict,
    image_bytes: bytes | None = None,
    employee_login_id: str = "",
    auto_submit: bool = False,
) -> dict:
    """Full pipeline: create report → add entry → attach receipt → submit.

    This is the main function called after OpenClaw audit passes.

    Returns:
        {
            "concur_report_id": "...",
            "concur_entry_id": "...",
            "concur_image_id": "...",
            "submitted": True/False,
            "status": "pushed_to_concur"
        }
    """
    audit_id = expense_data.get("audit_id", "unknown")

    # 1. Create report
    report_name = (
        f"OpenClaw-{expense_data.get('invoice_date', 'undated')}-"
        f"{expense_data.get('vendor_name', 'unknown')[:20]}"
    )
    report = await create_expense_report(
        employee_login_id=employee_login_id,
        report_name=report_name,
    )
    report_id = report.get("ID", "")

    # 2. Create entry
    entry = await create_expense_entry(report_id, expense_data)
    entry_id = entry.get("ID", "")

    # 3. Attach receipt image
    image_id = ""
    if image_bytes:
        image_result = await upload_receipt_image(entry_id, image_bytes)
        image_id = image_result.get("ID", "")

    # 4. Auto-submit (optional — for PASS items)
    submitted = False
    if auto_submit:
        await submit_report(report_id)
        submitted = True

    logger.info(
        "Pushed audit %s to Concur: report=%s entry=%s submitted=%s",
        audit_id, report_id, entry_id, submitted,
    )

    return {
        "concur_report_id": report_id,
        "concur_entry_id": entry_id,
        "concur_image_id": image_id,
        "submitted": submitted,
        "status": "pushed_to_concur",
    }


# ═══════════════════════════════════════════════
# PHASE 2: 下行 — Concur → OpenClaw（事后审计数据回流）
# ═══════════════════════════════════════════════


async def pull_approved_reports(
    modified_after: str = "",
    limit: int = 100,
) -> list[dict]:
    """Pull recently approved/processed reports from Concur.

    Called periodically (hourly cron) to get post-approval data
    for cross-validation against original voucher.

    Key checks:
    - Manager changed the amount? (approved ¥4,500 but original was ¥4,999)
    - Report was rejected? (flag for review)
    - Payment completed? (close the audit loop)
    """
    params: dict[str, Any] = {"limit": limit}
    if modified_after:
        params["modifiedDateAfter"] = modified_after

    result = await _concur_request(
        "GET",
        "/api/v3.0/expense/reports",
        params=params,
    )
    return result.get("Items", [])


async def pull_report_entries(report_id: str) -> list[dict]:
    """Pull all expense entries for a specific report."""
    result = await _concur_request(
        "GET",
        f"/api/v3.0/expense/entries",
        params={"reportID": report_id},
    )
    return result.get("Items", [])


async def reconcile_with_concur(audit_id: str, concur_report_id: str) -> dict:
    """Cross-validate Concur approved data against OpenClaw's original audit.

    This is the post-audit reconciliation — checking if anything changed
    between what OpenClaw audited and what Concur finally approved.

    Returns:
        {
            "audit_id": "AUD-xxx",
            "discrepancies": [
                {"field": "amount", "openclaw": 4999, "concur": 4500, "note": "经理改了金额"},
                ...
            ],
            "concur_status": "approved" | "rejected" | "pending",
            "amount_changed": True/False,
        }
    """
    from . import db as database

    # Get OpenClaw's original audit
    audit = database.get_audit_result(audit_id)
    if not audit:
        return {"error": f"Audit {audit_id} not found"}

    openclaw_data = audit.get("ocr_structured", {})

    # Get Concur's final data
    entries = await pull_report_entries(concur_report_id)
    if not entries:
        return {"error": f"No entries found for Concur report {concur_report_id}"}

    # Find matching entry (by Custom1 = audit_id)
    concur_entry = None
    for entry in entries:
        if entry.get("Custom1") == audit_id:
            concur_entry = entry
            break

    if not concur_entry:
        # Fallback: match by invoice number
        inv_num = openclaw_data.get("invoice_number", "")
        for entry in entries:
            if entry.get("Custom4") == inv_num:
                concur_entry = entry
                break

    if not concur_entry:
        return {"error": "No matching Concur entry found", "audit_id": audit_id}

    # Cross-validate
    discrepancies = []

    # Amount check
    oc_amount = openclaw_data.get("amount", 0)
    cc_amount = concur_entry.get("TransactionAmount", 0)
    if abs(oc_amount - cc_amount) > 0.01:
        discrepancies.append({
            "field": "amount",
            "openclaw_value": oc_amount,
            "concur_value": cc_amount,
            "delta": round(cc_amount - oc_amount, 2),
            "note": "经理审批时修改了金额" if cc_amount != oc_amount else "",
        })

    # Date check
    oc_date = openclaw_data.get("invoice_date", "")
    cc_date = concur_entry.get("TransactionDate", "")
    if oc_date and cc_date and oc_date[:10] != cc_date[:10]:
        discrepancies.append({
            "field": "date",
            "openclaw_value": oc_date,
            "concur_value": cc_date,
            "note": "日期不一致",
        })

    # Vendor check
    oc_vendor = openclaw_data.get("vendor_name", "")
    cc_vendor = concur_entry.get("VendorDescription", "")
    if oc_vendor and cc_vendor and oc_vendor != cc_vendor:
        discrepancies.append({
            "field": "vendor",
            "openclaw_value": oc_vendor,
            "concur_value": cc_vendor,
            "note": "供应商名称不一致",
        })

    # Log reconciliation
    database.append_audit_log(
        event_type="reconciliation",
        actor="system",
        audit_id=audit_id,
        details={
            "concur_report_id": concur_report_id,
            "discrepancies": discrepancies,
            "concur_status": concur_entry.get("ApprovalStatusName", "unknown"),
        },
    )

    return {
        "audit_id": audit_id,
        "concur_report_id": concur_report_id,
        "concur_status": concur_entry.get("ApprovalStatusName", "unknown"),
        "discrepancies": discrepancies,
        "amount_changed": any(d["field"] == "amount" for d in discrepancies),
    }


def _build_audit_comment(expense_data: dict) -> str:
    """Build a comment for Concur entry with OpenClaw audit summary."""
    risk_level = expense_data.get("risk_level", "unknown")
    risk_score = expense_data.get("risk_score", 0)
    audit_id = expense_data.get("audit_id", "")

    level_label = {"pass": "通过", "warn": "需关注", "fail": "驳回"}.get(risk_level, risk_level)

    return (
        f"[OpenClaw AI审核] {level_label} | 风险评分: {risk_score}/100 | "
        f"审计ID: {audit_id}"
    )
