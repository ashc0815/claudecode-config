"""报告生成器 — 生成 Markdown 和 JSON 评测报告。

增强版：
- 新增多维评分汇总表
- 新增切片分析报告
- 新增回归对比报告
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from eval.models import (
    EvalResult,
    EvalSummary,
    Experiment,
    RegressionResult,
)

_TIERS = ["T1", "T2", "T3", "T4"]


# ---------------------------------------------------------------------------
# Markdown 报告
# ---------------------------------------------------------------------------

def generate_markdown_report(
    summary: EvalSummary,
    results: List[EvalResult],
    experiment: Optional[Experiment] = None,
    slice_metrics: Optional[Dict] = None,
    regression: Optional[RegressionResult] = None,
) -> str:
    """生成完整的 Markdown 评测报告。"""
    sections = [
        _section_header(summary, experiment),
        _section_overview(summary),
        _section_score_summary(summary),
        _section_category_accuracy(summary),
        _section_confusion_matrix(summary),
    ]

    if slice_metrics:
        sections.append(_section_slice_analysis(slice_metrics))

    if regression:
        sections.append(_section_regression(regression))

    sections.extend([
        _section_case_details(results),
        _section_blind_spots(summary),
        _section_cost(summary),
        _section_capability_assessment(),
    ])

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# JSON 报告
# ---------------------------------------------------------------------------

def generate_json_report(
    summary: EvalSummary,
    results: List[EvalResult],
    experiment: Optional[Experiment] = None,
    slice_metrics: Optional[Dict] = None,
    regression: Optional[RegressionResult] = None,
) -> dict:
    """生成结构化 JSON 报告。"""
    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary.model_dump(),
        "results": [r.model_dump() for r in results],
    }

    if experiment:
        report["experiment"] = {
            "id": experiment.experiment_id,
            "name": experiment.name,
            "git_commit": experiment.git_commit,
            "dataset_version": experiment.dataset.version,
            "created_at": experiment.created_at,
            "is_baseline": experiment.is_baseline,
            "tags": experiment.tags,
        }

    if slice_metrics:
        report["slices"] = {
            name: sm.to_dict() for name, sm in slice_metrics.items()
        }

    if regression:
        report["regression"] = regression.model_dump()

    return report


# ---------------------------------------------------------------------------
# Markdown 各节
# ---------------------------------------------------------------------------

def _section_header(summary: EvalSummary, experiment: Optional[Experiment] = None) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        f"# ConcurShield 评测报告\n",
        f"生成时间: {now}  ",
        f"总用例数: {summary.total_cases}  ",
    ]
    if experiment:
        lines.append(f"实验 ID: `{experiment.experiment_id}`  ")
        if experiment.name:
            lines.append(f"实验名称: {experiment.name}  ")
        lines.append(f"数据集版本: `{experiment.dataset.version}`  ")
        if experiment.git_commit:
            lines.append(f"Git commit: `{experiment.git_commit}`  ")
        if experiment.is_baseline:
            lines.append("**[BASELINE]**  ")
    lines.append("")
    return "\n".join(lines)


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


def _section_score_summary(summary: EvalSummary) -> str:
    """多维评分汇总表（新增）。"""
    if not summary.score_summary:
        return ""

    lines = [
        "## 2. 多维评分汇总\n",
        "| 维度 | 均值 | 最小 | 最大 | 通过率 | 样本数 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, stats in sorted(summary.score_summary.items()):
        lines.append(
            f"| {name} | {stats['mean']:.2f} | {stats['min']:.2f} | "
            f"{stats['max']:.2f} | {stats['pass_rate']:.1%} | "
            f"{int(stats.get('count', 0))} |"
        )
    lines.append("")
    return "\n".join(lines)


def _section_category_accuracy(summary: EvalSummary) -> str:
    lines = [
        "## 3. 按类别准确率\n",
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
        "## 4. 混淆矩阵\n",
        "| Expected \\ Actual | T1 | T2 | T3 | T4 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for expected in _TIERS:
        row = cm.get(expected, {})
        cells = " | ".join(str(row.get(t, 0)) for t in _TIERS)
        lines.append(f"| **{expected}** | {cells} |")
    return "\n".join(lines) + "\n"


def _section_slice_analysis(slice_metrics: Dict) -> str:
    """切片分析表（新增）。"""
    lines = [
        "## 5. 切片分析\n",
        "| 切片 | 总数 | 通过 | 准确率 | FP | FN | 严重漏报 | 平均耗时 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, sm in sorted(slice_metrics.items()):
        d = sm.to_dict()
        lines.append(
            f"| {name} | {d['total']} | {d['passed']} | "
            f"{d['accuracy']:.1%} | {d['false_positives']} | "
            f"{d['false_negatives']} | {d['severe_misses']} | "
            f"{d['avg_duration_ms']:.0f}ms |"
        )

    # 附加评分维度均值
    has_scores = any(sm.score_means for sm in slice_metrics.values())
    if has_scores:
        lines.append("")
        # 收集所有维度名
        all_dims = sorted(set(
            dim for sm in slice_metrics.values() for dim in sm.score_means
        ))
        header = "| 切片 | " + " | ".join(all_dims) + " |"
        sep = "| --- | " + " | ".join(["---"] * len(all_dims)) + " |"
        lines.extend(["", header, sep])
        for name, sm in sorted(slice_metrics.items()):
            cells = " | ".join(
                f"{sm.score_means.get(d, 0):.2f}" for d in all_dims
            )
            lines.append(f"| {name} | {cells} |")

    lines.append("")
    return "\n".join(lines)


def _section_regression(regression: RegressionResult) -> str:
    """回归对比报告（新增）。"""
    lines = [
        "## 6. 回归对比\n",
        f"Baseline: `{regression.baseline_id}` vs Current: `{regression.current_id}`\n",
        "| 指标 | 值 |",
        "| --- | --- |",
        f"| 对比用例数 | {regression.total_compared} |",
        f"| 准确率变化 | {regression.accuracy_delta:+.2%} |",
        f"| 改善 | {regression.improved} |",
        f"| 退化 | {regression.regressed} |",
        f"| 新增失败 | {regression.new_failures} |",
        f"| 修复 | {regression.fixed} |",
        "",
    ]

    if regression.has_regression:
        lines.append("### 退化用例\n")
        for item in regression.items:
            if item.change_type in ("regressed", "new_failure"):
                lines.append(f"- **{item.case_id}**: {item.detail}")
        lines.append("")

    if regression.fixed or regression.improved:
        lines.append("### 改善用例\n")
        for item in regression.items:
            if item.change_type in ("fixed", "improved"):
                lines.append(f"- **{item.case_id}**: {item.detail}")
        lines.append("")

    return "\n".join(lines)


def _section_case_details(results: List[EvalResult]) -> str:
    section_num = "7"
    lines = [f"## {section_num}. 逐用例详情\n"]

    for r in results:
        icon = "\u2705" if r.tier_match and r.error is None else "\u274c"
        if r.error:
            icon = "\u26a0\ufe0f"

        lines.append(f"### {r.case_id} {icon}\n")

        tags: List[str] = []
        if r.is_false_positive:
            tags.append("\u26a0\ufe0f FALSE_POSITIVE")
        if r.is_false_negative:
            tags.append("\u26a0\ufe0f FALSE_NEGATIVE")
        if r.is_severe_miss:
            tags.append("\u26a0\ufe0f SEVERE_MISS")
        if tags:
            lines.append(f"**{' | '.join(tags)}**\n")

        expected_range = "-".join(r.expected_tier_range)
        lines.append(f"- **\u7c7b\u522b**: {r.category}")
        lines.append(f"- **\u9884\u671f Tier**: {expected_range}")
        lines.append(f"- **\u5b9e\u9645 Tier**: {r.actual_tier or 'N/A'}")
        lines.append(f"- **\u5b9e\u9645\u5206\u6570**: {r.actual_score}")
        signals_str = ", ".join(r.actual_signals) if r.actual_signals else "\u65e0"
        lines.append(f"- **\u5b9e\u9645\u4fe1\u53f7**: {signals_str}")
        lines.append(f"- **\u8017\u65f6**: {r.duration_ms}ms")

        # 多维评分详情
        if r.scores:
            score_parts = [
                f"{s.name}: {s.score:.2f} ({s.label})"
                for s in r.scores if s.score >= 0
            ]
            if score_parts:
                lines.append(f"- **\u8bc4\u5206**: {' | '.join(score_parts)}")

        if r.error:
            lines.append(f"- **\u9519\u8bef**: `{r.error}`")

        lines.append("")

    return "\n".join(lines)


def _section_blind_spots(summary: EvalSummary) -> str:
    lines = ["## 8. \u5df2\u77e5\u76f2\u533a\u6d4b\u8bd5\n"]

    if not summary.known_blind_spot_results:
        lines.append("\u65e0\u5df2\u77e5\u76f2\u533a\u7528\u4f8b\u3002\n")
        return "\n".join(lines)

    for bs in summary.known_blind_spot_results:
        lines.append(f"### {bs['case_id']}\n")
        expected_range = "-".join(bs.get("expected_tier_range", []))
        lines.append(f"- **\u7c7b\u522b**: {bs['category']}")
        lines.append(f"- **\u9884\u671f Tier**: {expected_range}")
        lines.append(f"- **\u5b9e\u9645 Tier**: {bs.get('actual_tier', 'N/A')}")
        tier_match_str = "\u662f" if bs.get("tier_match") else "\u5426"
        lines.append(f"- **Tier \u5339\u914d**: {tier_match_str}")
        bs_signals = ", ".join(bs.get("actual_signals", [])) or "\u65e0"
        lines.append(f"- **\u5b9e\u9645\u4fe1\u53f7**: {bs_signals}")
        if bs.get("notes"):
            lines.append(f"- **\u5907\u6ce8**: {bs['notes']}")
        lines.append("")

    lines.append(
        "> **MVP \u5df2\u77e5\u80fd\u529b\u8fb9\u754c**: \u4ee5\u4e0a\u7528\u4f8b\u5c5e\u4e8e\u5f53\u524d\u6a21\u578b\u5df2\u77e5\u7684\u68c0\u6d4b\u76f2\u533a\uff0c"
        "\u5c06\u5728\u540e\u7eed\u7248\u672c\u4e2d\u901a\u8fc7\u884c\u4e3a\u5206\u6790\u7b49\u624b\u6bb5\u6539\u8fdb\u3002\n"
    )
    return "\n".join(lines)


def _section_cost(summary: EvalSummary) -> str:
    return (
        "## 9. \u6210\u672c\u5206\u6790\n\n"
        "| \u6307\u6807 | \u503c |\n"
        "| --- | --- |\n"
        f"| \u603b API \u8c03\u7528 | {summary.total_api_calls} |\n"
        f"| \u603b\u8017\u65f6 | {summary.total_duration_ms}ms |\n"
        f"| \u5e73\u5747\u8017\u65f6 | {summary.avg_duration_ms:.1f}ms |\n"
    )


def _section_capability_assessment() -> str:
    return (
        "## 10. \u8bda\u5b9e\u7684\u80fd\u529b\u8bc4\u4f30\n\n"
        "ConcurShield \u4e0d\u58f0\u79f0\u80fd\u68c0\u6d4b\u6240\u6709\u53d1\u7968\u6b3a\u8bc8\u3002\n\n"
        "- pHash \u53ea\u80fd\u68c0\u6d4b\u91cd\u590d\u63d0\u4ea4\u3002\n"
        "- \u89c6\u89c9\u5f02\u5e38\u662f\u5f31\u542f\u53d1\u6027\u4fe1\u53f7\u3002\n"
        "- \u201c\u771f\u5546\u6237+AI\u53d1\u7968\u201d\u662f MVP \u5df2\u77e5\u76f2\u533a\u3002\n"
        "- \u7b2c\u4e8c\u9636\u6bb5\u884c\u4e3a\u5206\u6790\u662f\u5173\u952e\u8865\u5145\u3002\n"
    )
