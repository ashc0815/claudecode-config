"""Notification tools for human-in-the-loop approval and status updates."""

from __future__ import annotations

import os

import httpx
from crewai.tools import BaseTool
from pydantic import Field


class TelegramNotifyTool(BaseTool):
    name: str = "telegram_notify"
    description: str = (
        "Send a notification message via Telegram. Input: 'message' (text to send). "
        "Used for daily plan approval requests, publish confirmations, and alerts."
    )

    bot_token: str = Field(default="")
    chat_id: str = Field(default="")

    def model_post_init(self, __context: object) -> None:
        self.bot_token = self.bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = self.chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")

    def _run(self, message: str) -> str:
        if not self.bot_token or not self.chat_id:
            # Fallback: print to console if Telegram not configured
            print(f"[NOTIFICATION] {message}")
            return "Notification printed to console (Telegram not configured)"

        resp = httpx.post(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
            },
        )
        resp.raise_for_status()
        return "Notification sent via Telegram"


class HumanApprovalTool(BaseTool):
    name: str = "request_human_approval"
    description: str = (
        "Request human approval for a pending action. Input: 'action_description' "
        "(what needs approval) and 'details' (the content/plan to review). "
        "Blocks until approval is received or times out (30 min → auto-approve "
        "if auto_approve is enabled in strategy config)."
    )

    def _run(self, action_description: str, details: str) -> str:
        # In production, this would:
        # 1. Send approval request via Telegram/Slack
        # 2. Listen for reply (webhook or polling)
        # 3. Return "approved" / "rejected" / "modified: <changes>"
        #
        # For MVP, use console input:
        print(f"\n{'='*60}")
        print(f"APPROVAL REQUIRED: {action_description}")
        print(f"{'='*60}")
        print(details)
        print(f"{'='*60}")

        # In automated mode, check for pre-configured auto-approve
        auto_approve = os.environ.get("AUTO_APPROVE", "false").lower() == "true"
        if auto_approve:
            print("[AUTO-APPROVED based on config]")
            return "approved"

        try:
            response = input("\nApprove? [y/n/modify]: ").strip().lower()
        except EOFError:
            return "approved"  # Non-interactive mode

        if response in ("y", "yes", ""):
            return "approved"
        elif response in ("n", "no"):
            return "rejected"
        else:
            return f"modified: {response}"
