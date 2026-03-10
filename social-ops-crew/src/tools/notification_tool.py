"""Notification tools — Telegram alerts and human-in-the-loop approval."""

from __future__ import annotations

import os

import httpx


# ── Handlers ────────────────────────────────────────────────────────

def telegram_notify(message: str) -> str:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        print(f"[NOTIFICATION] {message}")
        return "Notification printed to console (Telegram not configured)"

    resp = httpx.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
    )
    resp.raise_for_status()
    return "Notification sent via Telegram"


def request_human_approval(action_description: str, details: str) -> str:
    print(f"\n{'=' * 60}")
    print(f"APPROVAL REQUIRED: {action_description}")
    print(f"{'=' * 60}")
    print(details)
    print(f"{'=' * 60}")

    auto_approve = os.environ.get("AUTO_APPROVE", "false").lower() == "true"
    if auto_approve:
        print("[AUTO-APPROVED based on config]")
        return "approved"

    try:
        response = input("\nApprove? [y/n/modify]: ").strip().lower()
    except EOFError:
        return "approved"

    if response in ("y", "yes", ""):
        return "approved"
    elif response in ("n", "no"):
        return "rejected"
    else:
        return f"modified: {response}"


# ── Schemas ─────────────────────────────────────────────────────────

TELEGRAM_NOTIFY_SCHEMA = {
    "name": "telegram_notify",
    "description": "Send a notification message via Telegram.",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Message to send"},
        },
        "required": ["message"],
    },
}

HUMAN_APPROVAL_SCHEMA = {
    "name": "request_human_approval",
    "description": (
        "Request human approval for a pending action. "
        "Blocks until approved/rejected. Use for content review and strategy changes."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action_description": {"type": "string", "description": "What needs approval"},
            "details": {"type": "string", "description": "Content/plan to review"},
        },
        "required": ["action_description", "details"],
    },
}

# ── Registry ────────────────────────────────────────────────────────

NOTIFICATION_TOOLS = {
    "telegram_notify": (TELEGRAM_NOTIFY_SCHEMA, telegram_notify),
    "request_human_approval": (HUMAN_APPROVAL_SCHEMA, request_human_approval),
}
