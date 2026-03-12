"""Feishu notification module — enhanced interactive cards for V1.1 HITL."""

import logging
from typing import Any

import httpx

from .config import settings
from .models import AuditResult, WeeklyReportData

logger = logging.getLogger(__name__)


async def _send_feishu(payload: dict) -> bool:
    """Send a message to Feishu webhook."""
    if not settings.feishu_webhook_url:
        logger.warning("Feishu webhook URL not configured, skipping notification")
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(settings.feishu_webhook_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                logger.error("Feishu API error: %s", data)
                return False
            return True
    except Exception as e:
        logger.error("Failed to send Feishu notification: %s", e)
        return False


def _severity_emoji(severity: str) -> str:
    return {"critical": "🔴", "high": "🔴", "medium": "🟡", "low": "🟢"}.get(
        severity, "⚪"
    )


def _precision_emoji(precision: float) -> str:
    if precision >= 0.7:
        return "🟢"
    elif precision >= 0.4:
        return "🟡"
    return "🔴"


async def send_audit_result(result: AuditResult) -> bool:
    """Send audit result as interactive Feishu card.

    V1.1 enhancement: includes per-rule precision and confidence scores.
    """
    risk_emoji = {"pass": "✅", "warn": "⚠️", "fail": "🚫"}.get(result.risk_level, "❓")

    # Build risk flags text
    flags_text = ""
    for i, flag in enumerate(result.risk_flags, 1):
        emoji = _severity_emoji(flag.severity)
        prec_text = f" | 历史精准率: {flag.confidence:.0%}" if flag.confidence else ""
        flags_text += f"{i}. {emoji} {flag.description}\n   置信度: {flag.confidence:.0%}{prec_text}\n\n"

    if not flags_text:
        flags_text = "未发现风险标记"

    card = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🔍 凭证扫描结果  #{result.audit_id}",
                },
                "template": {"pass": "green", "warn": "orange", "fail": "red"}.get(
                    result.risk_level, "blue"
                ),
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**金额**: ¥{result.ocr_structured.get('amount', 0):,.2f}",
                            },
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**风险等级**: {risk_emoji} {result.risk_level.upper()} ({result.risk_score}/100)",
                            },
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**供应商**: {result.ocr_structured.get('vendor_name', '未知')}",
                            },
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**发票号**: {result.ocr_structured.get('invoice_number', '未知')}",
                            },
                        },
                    ],
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📋 AI 审计发现:**\n\n{flags_text}",
                    },
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**💡 AI 分析:** {result.ai_reasoning[:300]}",
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "✅ 确认异常"},
                            "type": "primary",
                            "value": {
                                "action": "confirmed",
                                "audit_id": result.audit_id,
                            },
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "❌ 标记误报"},
                            "type": "danger",
                            "value": {
                                "action": "false_positive",
                                "audit_id": result.audit_id,
                            },
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "🔍 需要调查"},
                            "type": "default",
                            "value": {
                                "action": "investigate",
                                "audit_id": result.audit_id,
                            },
                        },
                    ],
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"Prompt: {result.prompt_version} | 处理耗时: {result.processing_time_ms}ms | 您的反馈将帮助 AI 持续优化",
                        }
                    ],
                },
            ],
        },
    }

    return await _send_feishu(card)


async def send_weekly_report(report: WeeklyReportData) -> bool:
    """Send weekly performance report as Feishu card."""
    # Build rule performance text
    rules_text = ""
    for rp in report.rule_performances[:5]:
        emoji = _precision_emoji(rp.precision)
        warning = " ⚠️ 建议调整" if rp.precision < 0.4 else ""
        rules_text += f"{emoji} {rp.rule}   精准率 {rp.precision:.0%}   触发 {rp.trigger_count} 次{warning}\n"

    if not rules_text:
        rules_text = "本周无足够数据"

    # Build adjustments text
    adj_text = ""
    for adj in report.adjustments:
        adj_text += f"🔧 {adj.rule}: {adj.reason}\n"
    if not adj_text:
        adj_text = "本周无调优建议"

    card = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📊 OpenClaw 周报  {report.week_start} ~ {report.week_end}",
                },
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**── 本周概览 ──**\n"
                            f"处理凭证: **{report.total_audits}** 笔\n"
                            f"自动通过: {report.pass_count} 笔 ({_pct(report.pass_count, report.total_audits)})\n"
                            f"标记复核: {report.warn_count} 笔 ({_pct(report.warn_count, report.total_audits)})\n"
                            f"直接驳回: {report.fail_count} 笔 ({_pct(report.fail_count, report.total_audits)})"
                        ),
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**── 准确率 ──**\n"
                            f"精准率: **{report.precision:.0%}**\n"
                            f"误报率: {report.false_positive_rate:.0%}\n"
                            f"反馈覆盖率: {report.feedback_rate:.0%}\n"
                            f"确认异常: **{report.confirmed_anomalies}** 笔"
                        ),
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**── 规则表现 TOP 5 ──**\n{rules_text}",
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**── 待处理建议 ──**\n{adj_text}",
                    },
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "✅ 批准全部"},
                            "type": "primary",
                            "value": {"action": "approve_all"},
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "📋 逐条审批"},
                            "type": "default",
                            "value": {"action": "review_individual"},
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "❌ 暂不调整"},
                            "type": "danger",
                            "value": {"action": "reject_all"},
                        },
                    ],
                },
            ],
        },
    }

    return await _send_feishu(card)


async def send_adjustment_proposal(adjustments: list[dict]) -> bool:
    """Send rule adjustment proposals to admin for approval."""
    adj_lines = []
    for adj in adjustments:
        adj_lines.append(
            f"**{adj['rule']}**: 当前权重 {adj.get('current_weight', 1.0)} → 建议 {adj['new_weight']}\n"
            f"  原因: {adj['reason']}\n"
            f"  用户反馈: {', '.join(adj.get('user_reasons', [])[:2]) or '无'}"
        )

    card = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🔧 规则调优建议（需要您的批准）",
                },
                "template": "orange",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "\n\n".join(adj_lines),
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "⚠️ 调整将在您批准后生效。所有变更记录在审计日志中。",
                        }
                    ],
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "✅ 批准全部"},
                            "type": "primary",
                            "value": {"action": "approve_all_adjustments"},
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "❌ 拒绝"},
                            "type": "danger",
                            "value": {"action": "reject_all_adjustments"},
                        },
                    ],
                },
            ],
        },
    }

    return await _send_feishu(card)


def _pct(part: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{part / total:.0%}"
