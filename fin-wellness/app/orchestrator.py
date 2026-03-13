"""AI Orchestrator — single brain, tool calls, empathetic responses.

Design:
  - One Claude Sonnet call per user message
  - AI decides which tools to call based on user intent
  - AI NEVER invents financial numbers — all data from tools
  - Tone adapts to user's financial_anxiety_level
  - Follows the Record→Discover→Explain→Suggest→Commit→Follow-up loop
"""

import json
import logging
from datetime import date, timedelta
from typing import Any

import anthropic

from . import db
from .config import settings
from .tools.definitions import TOOLS

logger = logging.getLogger(__name__)

# ── System Prompt ──

SYSTEM_PROMPT = """你是用户的私人财务健康助手。你的目标不是让用户记账，而是帮用户改善财务状态。

## 你的核心原则

1. **永远不说"你花太多了"** — 说"这个月XX比平时多了一些"
2. **永远不用"应该"** — 用"你可以试试"、"一个想法是"
3. **承认花钱是正常的** — "加班点外卖完全合理，只是看看有没有更划算的方式"
4. **一次只建议一件事** — 信息过载 = 什么都不做
5. **完成目标时要庆祝** — "带饭坚持了3周，省了¥600，太棒了"
6. **没完成时不评判** — "上周没带饭也没关系，要不要调整一下目标？"
7. **用户说"不想看"时尊重** — "好的，等你想看的时候随时叫我"

## 你的工作方式

- 你有一组工具可以查询用户的财务数据。所有数字必须来自工具返回，不要编造。
- 当用户问"我花了多少"类问题时，先调用 get_monthly_summary 或 get_transactions。
- 当你发现异常消费时，遵循循环：发现 → 解释 → 建议（一个微行动）→ 等用户承诺 → 后续跟进。
- 不要一次给出太多信息。简洁、温暖、有用。
- 金额用 ¥ 符号，保留整数（日常对话不需要小数点）。

## 语气调整

{anxiety_note}

## 当前上下文

今天是 {today}。
{active_commitments_note}
{goals_note}
"""


def _build_anxiety_note(level: str) -> str:
    if level == "high":
        return (
            "用户的财务焦虑程度较高。请特别注意：\n"
            "- 用更温和的措辞，避免任何可能引发焦虑的表达\n"
            "- 多强调正面进展，哪怕很小\n"
            "- 主动提供情绪支持：'管理财务本身就需要勇气，你已经在做了'\n"
            "- 如果数字不好看，先肯定用户的记录行为，再温和地提出建议"
        )
    elif level == "low":
        return "用户的财务焦虑程度较低，可以更直接地讨论数字和建议。"
    return "用正常温和的语气交流。"


def _build_system_prompt() -> str:
    """Build system prompt with current context."""
    profile = db.get_full_profile()
    anxiety = profile.get("financial_anxiety_level", "medium")

    # Active commitments
    commitments = db.get_active_commitments()
    if commitments:
        cmt_lines = "\n".join(
            f"- {c['action']}（从{c['start_date']}开始）" for c in commitments[:3]
        )
        commitments_note = f"用户当前的微行动承诺：\n{cmt_lines}"
    else:
        commitments_note = "用户目前没有进行中的微行动承诺。"

    # Goals
    goals = db.get_active_goals()
    if goals:
        goal_lines = "\n".join(f"- {g['title']}" for g in goals[:3])
        goals_note = f"用户的长期目标：\n{goal_lines}"
    else:
        goals_note = "用户还没有设定长期财务目标。"

    return SYSTEM_PROMPT.format(
        anxiety_note=_build_anxiety_note(anxiety),
        today=date.today().isoformat(),
        active_commitments_note=commitments_note,
        goals_note=goals_note,
    )


# ── Tool Execution ──


def _execute_tool(name: str, args: dict) -> Any:
    """Route tool call to the right capability function."""

    if name == "get_monthly_summary":
        return db.get_monthly_summary(args.get("year_month", ""))

    elif name == "get_transactions":
        return db.get_transactions(
            start_date=args.get("start_date", ""),
            end_date=args.get("end_date", ""),
            category=args.get("category", ""),
            tx_type=args.get("tx_type", ""),
            limit=args.get("limit", 50),
        )

    elif name == "get_net_worth":
        from .capabilities.net_worth import calculate_net_worth
        return calculate_net_worth()

    elif name == "detect_anomalies":
        from .capabilities.anomaly import detect_anomalies
        return detect_anomalies(
            year_month=args.get("year_month", ""),
            threshold_pct=args.get("threshold_pct", 25),
        )

    elif name == "get_category_trend":
        from .capabilities.anomaly import get_category_trend
        return get_category_trend(
            category=args["category"],
            months=args.get("months", 6),
        )

    elif name == "get_active_commitments":
        return db.get_active_commitments()

    elif name == "create_commitment":
        cid = db.upsert_commitment({
            "action": args["action"],
            "category": args.get("category", ""),
            "expected_saving": args.get("expected_saving", 0),
            "goal_id": args.get("goal_id"),
            "end_date": (date.today() + timedelta(days=7)).isoformat(),
        })
        return {"commitment_id": cid, "status": "created"}

    elif name == "update_commitment_status":
        db.upsert_commitment({
            "id": args["commitment_id"],
            "action": "",  # won't overwrite since it's an update
            "status": args["status"],
            "actual_saving": args.get("actual_saving", 0),
            "follow_up_result": args.get("follow_up_result", ""),
        })
        return {"status": "updated"}

    elif name == "get_active_goals":
        return db.get_active_goals()

    elif name == "create_goal":
        gid = db.upsert_goal({
            "title": args["title"],
            "target_amount": args.get("target_amount"),
            "deadline": args.get("deadline"),
        })
        return {"goal_id": gid, "status": "created"}

    elif name == "generate_weekly_review":
        from .capabilities.review import generate_weekly_review
        return generate_weekly_review()

    elif name == "get_user_profile":
        return db.get_full_profile()

    return {"error": f"Unknown tool: {name}"}


# ── Main Chat Function ──


async def chat(user_message: str) -> str:
    """Process a user message through the AI orchestrator.

    Flow:
    1. Build system prompt with current context
    2. Get recent conversation history
    3. Send to Claude with tools
    4. Execute any tool calls
    5. Get final response
    6. Save conversation to memory
    7. Return response text
    """
    # Save user message
    db.save_message("user", user_message)

    # Build context
    system = _build_system_prompt()
    history = db.get_recent_messages(limit=20)
    messages = [{"role": m["role"], "content": m["content"]} for m in history]

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Initial call
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system,
        tools=TOOLS,
        messages=messages,
    )

    # Tool call loop (max 5 rounds to prevent infinite loops)
    rounds = 0
    while response.stop_reason == "tool_use" and rounds < 5:
        rounds += 1

        # Extract tool calls from response
        tool_results = []
        assistant_content = response.content

        for block in assistant_content:
            if block.type == "tool_use":
                logger.info("Tool call: %s(%s)", block.name, json.dumps(block.input, ensure_ascii=False))
                result = _execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

        # Continue conversation with tool results
        messages.append({"role": "assistant", "content": assistant_content})
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

    # Extract final text response
    response_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            response_text += block.text

    # Save assistant response
    db.save_message("assistant", response_text)

    return response_text
