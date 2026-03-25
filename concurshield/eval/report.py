"""报告生成器 — 生成 Markdown 和 JSON 评测报告。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from eval.models import EvalResult, EvalSummary

_TIERS = ["T1", "T2", "T3", "T4"]


# ---------------------------------------------------------------------------
# Markdown 报告
# ---------------------------------------------------------------------------

def generate_markdown_report(
    summary: EvalSummary, results: List[EvalResult]
) -> str:
    """生成完整的 Markdown 评测报告。"""
    sections = [
        _section_header(summary),
        _section_overview(summary),
        _section_category_accuracy(summary),
        _section_confusion_matrix(summary),
        _section_case_details(results),
        _section_blind_spots(summary),
        _section_cost(summary),
        _section_capability_assessment(),
    ]
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# JSON 报告
# ---------------------------------------------------------------------------

def generate_json_report(
    summary: EvalSummary, results: List[EvalResult]
) -> dict:
    """生成结构化 JSON 报告。"""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary.model_dump(),
        "results": [r.model_dump() for r in results],
    }


# ---------------------------------------------------------------------------
# Markdown 各节
# ---------------------------------------------------------------------------

def _section_header(summary: EvalSummary) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        f"# ConcurShield 评测报告\n\n"
        f"生成时间: {now}  \n"
        f"总用例数: {summary.total_cases}\n"
    )


def _section_overview(summary: EvalSummary) -> str:
    total = summary.total_cases
    pass_rate = f"{summary.passed / total * 100:.1f}%" if total else "N/A"

    return (
        "## 1. 总览\n\n"
        "| 指标 | 值 |\n"
        "| --- | --- |\n"
        f"| 总用例 | {total} |\n"
        f"| 通过 | {summary.passed} ({pass_rate}) |\n"
        f"| 失败 | {summary.failed} |\n"
        f"| 错误 | {summary.errors} |\n"
        f"| 误报率 (FP) | {summary.false_positive_rate:.2%} |\n"
        f"| 漏报率 (FN) | {summary.false_negative_rate:.2%} |\n"
        f"| 严重漏报 | {summary.severe_miss_count} |\n"
    )


def _section_category_accuracy(summary: EvalSummary) -> str:
    lines = [
        "## 2. 按类别准确率\n",
        "| 类别 | 总数 | 通过 | 准确率 |",
        "| --- | --- | --- | --- |",
    ]
    for cat, info in sorted(summary.accuracy_by_category.items()):
        acc = f"{info['accuracy']:.1%}"
        lines.append(f"| {cat} | {info['total']} | {info['passed']} | {acc} |")
    return "\n".join(lines) + "\n"


def _section_confusion_matrix(summary: EvalSummary) -> str:
    cm = summary.confusion_matrix
    lines = [
        "## 3. 混淆矩阵\n",
        "| Expected \\ Actual | T1 | T2 | T3 | T4 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for expected in _TIERS:
        row = cm.get(expected, {})
        cells = " | ".join(str(row.get(t, 0)) for t in _TIERS)
        lines.append(f"| **{expected}** | {cells} |")
    return "\n".join(lines) + "\n"


def _section_case_details(results: List[EvalResult]) -> str:
    lines = ["## 4. 逐用例详情\n"]

    for r in results:
        icon = "✅" if r.tier_match and r.error is None else "❌"
        if r.error:
            icon = "⚠️"

        # 标题行
        lines.append(f"### {r.case_id} {icon}\n")

        # 标注
        tags: List[str] = []
        if r.is_false_positive:
            tags.append("⚠️ FALSE_POSITIVE")
        if r.is_false_negative:
            tags.append("⚠️ FALSE_NEGATIVE")
        if r.is_severe_miss:
            tags.append("⚠️ SEVERE_MISS")
        if tags:
            lines.append(f"**{' | '.join(tags)}**\n")

        expected_range = "-".join(r.expected_tier_range)
        lines.append(f"- **类别**: {r.category}")
        lines.append(f"- **预期 Tier**: {expected_range}")
        lines.append(f"- **实际 Tier**: {r.actual_tier or 'N/A'}")
        lines.append(f"- **实际分数**: {r.actual_score}")
        lines.append(f"- **实际信号**: {', '.join(r.actual_signals) if r.actual_signals else '无'}")
        lines.append(f"- **耗时**: {r.duration_ms}ms")

        if r.error:
            lines.append(f"- **错误**: `{r.error}`")

        lines.append("")  # 空行分隔

    return "\n".join(lines)


def _section_blind_spots(summary: EvalSummary) -> str:
    lines = ["## 5. 已知盲区测试\n"]

    if not summary.known_blind_spot_results:
        lines.append("无已知盲区用例。\n")
        return "\n".join(lines)

    for bs in summary.known_blind_spot_results:
        lines.append(f"### {bs['case_id']}\n")
        expected_range = "-".join(bs.get("expected_tier_range", []))
        lines.append(f"- **类别**: {bs['category']}")
        lines.append(f"- **预期 Tier**: {expected_range}")
        lines.append(f"- **实际 Tier**: {bs.get('actual_tier', 'N/A')}")
        lines.append(f"- **Tier 匹配**: {'是' if bs.get('tier_match') else '否'}")
        lines.append(f"- **实际信号**: {', '.join(bs.get('actual_signals', [])) or '无'}")
        if bs.get("notes"):
            lines.append(f"- **备注**: {bs['notes']}")
        lines.append("")

    lines.append(
        "> **MVP 已知能力边界**: 以上用例属于当前模型已知的检测盲区，"
        "将在后续版本中通过行为分析等手段改进。\n"
    )
    return "\n".join(lines)


def _section_cost(summary: EvalSummary) -> str:
    return (
        "## 6. 成本分析\n\n"
        "| 指标 | 值 |\n"
        "| --- | --- |\n"
        f"| 总 API 调用 | {summary.total_api_calls} |\n"
        f"| 总耗时 | {summary.total_duration_ms}ms |\n"
        f"| 平均耗时 | {summary.avg_duration_ms:.1f}ms |\n"
    )


def _section_capability_assessment() -> str:
    return (
        "## 7. 诚实的能力评估\n\n"
        "ConcurShield 不声称能检测所有发票欺诈。\n\n"
        "- pHash 只能检测重复提交。\n"
        "- 视觉异常是弱启发性信号。\n"
        "- \u201c真商户+AI发票\u201d是 MVP 已知盲区。\n"
        "- 第二阶段行为分析是关键补充。\n"
    )
