"""Fin-Wellness — FastAPI + CLI entry point.

Two modes:
  1. API mode: uvicorn app.main:app (for future mobile/web client)
  2. CLI mode: python -m app.main chat / import / status / review
"""

import asyncio
import logging
import sys
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from . import db
from .capabilities.importer import import_csv
from .capabilities.net_worth import calculate_net_worth
from .config import settings
from .orchestrator import chat

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Fin-Wellness 财务健康助手",
    description="陪伴式 AI 财务助手 — 不是记账工具，是改善财务状态的伙伴",
    version="0.1.0",
)


# ── Startup ──

@app.on_event("startup")
async def startup():
    db.init_db()


# ── API Endpoints ──


@app.post("/chat")
async def api_chat(message: str):
    """Chat with the AI financial assistant."""
    response = await chat(message)
    return {"response": response}


@app.post("/import")
async def api_import(file: UploadFile = File(...), source: str = ""):
    """Import transactions from CSV."""
    content = await file.read()
    result = import_csv(content, source_hint=source)
    return result


@app.get("/status")
async def api_status():
    """Get current financial status (net worth + this month summary)."""
    net_worth = calculate_net_worth()
    monthly = db.get_monthly_summary()
    goals = db.get_active_goals()
    commitments = db.get_active_commitments()

    return {
        "net_worth": net_worth,
        "monthly_summary": monthly,
        "active_goals": goals,
        "active_commitments": commitments,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ── CLI Mode ──


def cli():
    """Simple CLI interface for the financial assistant."""
    db.init_db()

    if len(sys.argv) < 2:
        print("用法:")
        print("  python -m app.main chat          # 和 AI 财务助手对话")
        print("  python -m app.main import <file>  # 导入 CSV 账单")
        print("  python -m app.main status         # 查看财务状态")
        return

    command = sys.argv[1]

    if command == "chat":
        print("💬 财务健康助手（输入 quit 退出）")
        print("=" * 40)
        while True:
            try:
                user_input = input("\n你: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再见！")
                break

            if user_input.lower() in ("quit", "exit", "q"):
                print("再见！随时来找我聊～")
                break

            if not user_input:
                continue

            response = asyncio.run(chat(user_input))
            print(f"\n助手: {response}")

    elif command == "import":
        if len(sys.argv) < 3:
            print("用法: python -m app.main import <csv文件路径> [alipay|wechat]")
            return

        filepath = sys.argv[2]
        source = sys.argv[3] if len(sys.argv) > 3 else ""

        content = Path(filepath).read_bytes()
        result = import_csv(content, source_hint=source)
        print(f"导入完成: {result['imported']} 笔交易")
        print(f"格式: {result['format']}")
        if result.get("categories_auto"):
            print(f"自动分类: {result['categories_auto']} 笔")
        if result.get("date_range"):
            print(f"日期范围: {result['date_range']}")

    elif command == "status":
        nw = calculate_net_worth()
        monthly = db.get_monthly_summary()

        print(f"\n📊 财务状态 ({nw['date']})")
        print("=" * 40)
        print(f"净资产: ¥{nw['net_worth']:,.0f}")
        print(f"  总资产: ¥{nw['total_assets']:,.0f}")
        print(f"  总负债: ¥{nw['total_liabilities']:,.0f}")

        if monthly.get("expenses"):
            print(f"\n📅 本月支出: ¥{monthly['total_expense']:,.0f}")
            for e in monthly["expenses"][:5]:
                print(f"  {e['category']}: ¥{e['total']:,.0f} ({e['count']}笔)")

        if monthly.get("total_income"):
            print(f"\n💰 本月收入: ¥{monthly['total_income']:,.0f}")

    else:
        print(f"未知命令: {command}")
        print("可用命令: chat, import, status")


if __name__ == "__main__":
    cli()
