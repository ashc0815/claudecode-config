"""报告生成器 — 生成 Markdown、JSON 和 HTML 评测报告。

增强版：
- 新增多维评分汇总表
- 新增切片分析报告
- 新增回归对比报告
- 新增自包含 HTML 交互式报告
"""

from __future__ import annotations

import html as html_mod
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


# ---------------------------------------------------------------------------
# HTML 报告
# ---------------------------------------------------------------------------

def generate_html_report(
    summary: EvalSummary,
    results: List[EvalResult],
    experiment: Optional[Experiment] = None,
    slice_metrics: Optional[Dict] = None,
    regression: Optional[RegressionResult] = None,
) -> str:
    """生成自包含 HTML 交互式评测报告。"""
    esc = html_mod.escape
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    total = summary.total_cases
    pass_rate = summary.passed / total * 100 if total else 0
    fail_rate = summary.failed / total * 100 if total else 0
    err_rate = summary.errors / total * 100 if total else 0

    # --- Build sections ---
    meta_rows = f"""
        <tr><td>生成时间</td><td>{now}</td></tr>
        <tr><td>总用例数</td><td>{total}</td></tr>"""
    if experiment:
        meta_rows += f"""
        <tr><td>实验 ID</td><td><code>{esc(experiment.experiment_id)}</code></td></tr>"""
        if experiment.name:
            meta_rows += f"""
        <tr><td>实验名称</td><td>{esc(experiment.name)}</td></tr>"""
        meta_rows += f"""
        <tr><td>数据集版本</td><td><code>{esc(experiment.dataset.version)}</code></td></tr>"""
        if experiment.git_commit:
            meta_rows += f"""
        <tr><td>Git commit</td><td><code>{esc(experiment.git_commit)}</code></td></tr>"""
        if experiment.is_baseline:
            meta_rows += """
        <tr><td>标记</td><td><span class="badge baseline">BASELINE</span></td></tr>"""

    # Overview cards
    overview_html = f"""
    <div class="cards">
        <div class="card">
            <div class="card-value">{total}</div>
            <div class="card-label">总用例</div>
        </div>
        <div class="card pass">
            <div class="card-value">{summary.passed}</div>
            <div class="card-label">通过 ({pass_rate:.1f}%)</div>
            <div class="bar"><div class="bar-fill pass-bg" style="width:{pass_rate:.1f}%"></div></div>
        </div>
        <div class="card fail">
            <div class="card-value">{summary.failed}</div>
            <div class="card-label">失败 ({fail_rate:.1f}%)</div>
            <div class="bar"><div class="bar-fill fail-bg" style="width:{fail_rate:.1f}%"></div></div>
        </div>
        <div class="card warn">
            <div class="card-value">{summary.errors}</div>
            <div class="card-label">错误 ({err_rate:.1f}%)</div>
        </div>
        <div class="card">
            <div class="card-value">{summary.false_positive_rate:.1%}</div>
            <div class="card-label">误报率 (FP)</div>
        </div>
        <div class="card">
            <div class="card-value">{summary.false_negative_rate:.1%}</div>
            <div class="card-label">漏报率 (FN)</div>
        </div>
        <div class="card {"fail" if summary.severe_miss_count else ""}">
            <div class="card-value">{summary.severe_miss_count}</div>
            <div class="card-label">严重漏报</div>
        </div>
    </div>"""

    # Score summary
    score_html = ""
    if summary.score_summary:
        score_rows = ""
        for name, stats in sorted(summary.score_summary.items()):
            mean = stats["mean"]
            pr = stats["pass_rate"]
            color = "pass" if pr >= 0.8 else ("warn" if pr >= 0.5 else "fail")
            score_rows += f"""
            <tr>
                <td>{esc(name)}</td>
                <td>
                    <div class="bar-inline">
                        <div class="bar-fill {color}-bg" style="width:{mean*100:.0f}%"></div>
                    </div>
                    {mean:.2f}
                </td>
                <td>{stats.get('min', 0):.2f}</td>
                <td>{stats.get('max', 0):.2f}</td>
                <td><span class="badge {color}">{pr:.0%}</span></td>
                <td>{int(stats.get('count', 0))}</td>
            </tr>"""
        score_html = f"""
    <section>
        <h2>多维评分汇总</h2>
        <table>
            <thead><tr><th>维度</th><th>均值</th><th>最小</th><th>最大</th><th>通过率</th><th>样本</th></tr></thead>
            <tbody>{score_rows}</tbody>
        </table>
    </section>"""

    # Category accuracy
    cat_rows = ""
    for cat, info in sorted(summary.accuracy_by_category.items()):
        acc = info["accuracy"]
        color = "pass" if acc >= 0.8 else ("warn" if acc >= 0.5 else "fail")
        cat_rows += f"""
            <tr>
                <td>{esc(cat)}</td>
                <td>{info['total']}</td>
                <td>{info['passed']}</td>
                <td>
                    <div class="bar-inline">
                        <div class="bar-fill {color}-bg" style="width:{acc*100:.0f}%"></div>
                    </div>
                    <span class="badge {color}">{acc:.0%}</span>
                </td>
            </tr>"""
    cat_html = f"""
    <section>
        <h2>按类别准确率</h2>
        <table>
            <thead><tr><th>类别</th><th>总数</th><th>通过</th><th>准确率</th></tr></thead>
            <tbody>{cat_rows}</tbody>
        </table>
    </section>"""

    # Confusion matrix
    cm = summary.confusion_matrix
    cm_rows = ""
    for expected in _TIERS:
        row = cm.get(expected, {})
        cells = ""
        for actual in _TIERS:
            val = row.get(actual, 0)
            cls = "cm-diag" if expected == actual else ("cm-off" if val > 0 else "")
            cells += f'<td class="{cls}">{val}</td>'
        cm_rows += f"<tr><th>{expected}</th>{cells}</tr>"
    cm_html = f"""
    <section>
        <h2>混淆矩阵</h2>
        <table class="cm-table">
            <thead><tr><th>期望 \\ 实际</th><th>T1</th><th>T2</th><th>T3</th><th>T4</th></tr></thead>
            <tbody>{cm_rows}</tbody>
        </table>
    </section>"""

    # Slice analysis
    slice_html = ""
    if slice_metrics:
        slice_rows = ""
        for name, sm in sorted(slice_metrics.items()):
            d = sm.to_dict()
            acc = d["accuracy"]
            color = "pass" if acc >= 0.8 else ("warn" if acc >= 0.5 else "fail")
            slice_rows += f"""
            <tr>
                <td>{esc(name)}</td>
                <td>{d['total']}</td>
                <td>{d['passed']}</td>
                <td><span class="badge {color}">{acc:.0%}</span></td>
                <td>{d['false_positives']}</td>
                <td>{d['false_negatives']}</td>
                <td>{d['severe_misses']}</td>
                <td>{d['avg_duration_ms']:.0f}ms</td>
            </tr>"""
        slice_html = f"""
    <section>
        <h2>切片分析</h2>
        <table>
            <thead><tr><th>切片</th><th>总数</th><th>通过</th><th>准确率</th><th>FP</th><th>FN</th><th>严重漏报</th><th>平均耗时</th></tr></thead>
            <tbody>{slice_rows}</tbody>
        </table>
    </section>"""

    # Regression
    regression_html = ""
    if regression:
        status_cls = "fail" if regression.has_regression else "pass"
        status_text = "检测到退化" if regression.has_regression else "无退化"
        reg_items = ""
        for item in regression.items:
            icon_cls = "fail" if item.change_type in ("regressed", "new_failure") else "pass"
            label = {"improved": "改善", "regressed": "退化", "new_failure": "新增失败", "fixed": "修复"}.get(item.change_type, item.change_type)
            reg_items += f"""
                <tr class="{icon_cls}-row">
                    <td><code>{esc(item.case_id)}</code></td>
                    <td><span class="badge {icon_cls}">{label}</span></td>
                    <td>{esc(item.detail)}</td>
                </tr>"""
        regression_html = f"""
    <section>
        <h2>回归对比 <span class="badge {status_cls}">{status_text}</span></h2>
        <p>Baseline: <code>{esc(regression.baseline_id)}</code> vs Current: <code>{esc(regression.current_id)}</code></p>
        <div class="cards">
            <div class="card"><div class="card-value">{regression.total_compared}</div><div class="card-label">对比用例</div></div>
            <div class="card"><div class="card-value">{regression.accuracy_delta:+.2%}</div><div class="card-label">准确率变化</div></div>
            <div class="card pass"><div class="card-value">{regression.improved}</div><div class="card-label">改善</div></div>
            <div class="card fail"><div class="card-value">{regression.regressed}</div><div class="card-label">退化</div></div>
            <div class="card pass"><div class="card-value">{regression.fixed}</div><div class="card-label">修复</div></div>
            <div class="card fail"><div class="card-value">{regression.new_failures}</div><div class="card-label">新增失败</div></div>
        </div>
        <table>
            <thead><tr><th>用例</th><th>变化</th><th>详情</th></tr></thead>
            <tbody>{reg_items}</tbody>
        </table>
    </section>"""

    # Case details
    case_rows = ""
    for r in results:
        if r.error:
            status_cls = "warn"
            status_icon = "&#9888;"
        elif r.tier_match:
            status_cls = "pass"
            status_icon = "&#10003;"
        else:
            status_cls = "fail"
            status_icon = "&#10007;"

        tags_html = ""
        if r.is_false_positive:
            tags_html += '<span class="badge warn">FP</span> '
        if r.is_false_negative:
            tags_html += '<span class="badge warn">FN</span> '
        if r.is_severe_miss:
            tags_html += '<span class="badge fail">严重漏报</span> '

        signals = ", ".join(r.actual_signals) if r.actual_signals else "-"
        score_cells = ""
        if r.scores:
            for s in r.scores:
                sc = s.score
                c = "pass" if sc >= 0.8 else ("warn" if sc >= 0.5 else "fail")
                score_cells += f'<span class="badge {c}" title="{esc(s.reason)}">{esc(s.name)}: {sc:.2f}</span> '

        expected_range = "-".join(r.expected_tier_range)
        error_html = f'<div class="error-msg">{esc(r.error)}</div>' if r.error else ""

        case_rows += f"""
            <tr class="{status_cls}-row" onclick="this.classList.toggle('expanded')">
                <td><span class="status-icon {status_cls}">{status_icon}</span></td>
                <td><code>{esc(r.case_id)}</code></td>
                <td>{esc(r.category)}</td>
                <td>{esc(expected_range)}</td>
                <td>{esc(r.actual_tier or 'N/A')}</td>
                <td>{r.actual_score}</td>
                <td>{r.duration_ms}ms</td>
                <td>{tags_html}</td>
            </tr>
            <tr class="detail-row">
                <td colspan="8">
                    <div class="detail-content">
                        <p><strong>信号:</strong> {esc(signals)}</p>
                        {f'<p><strong>评分:</strong> {score_cells}</p>' if score_cells else ''}
                        {error_html}
                    </div>
                </td>
            </tr>"""

    case_html = f"""
    <section>
        <h2>逐用例详情</h2>
        <div class="filter-bar">
            <input type="text" id="caseFilter" placeholder="搜索用例 ID / 类别..." oninput="filterCases()">
            <select id="statusFilter" onchange="filterCases()">
                <option value="all">全部状态</option>
                <option value="pass">通过</option>
                <option value="fail">失败</option>
                <option value="warn">错误</option>
            </select>
        </div>
        <table class="case-table" id="caseTable">
            <thead><tr><th></th><th>ID</th><th>类别</th><th>期望 Tier</th><th>实际 Tier</th><th>分数</th><th>耗时</th><th>标签</th></tr></thead>
            <tbody>{case_rows}</tbody>
        </table>
    </section>"""

    # Cost
    cost_html = f"""
    <section>
        <h2>成本分析</h2>
        <div class="cards">
            <div class="card"><div class="card-value">{summary.total_api_calls}</div><div class="card-label">总 API 调用</div></div>
            <div class="card"><div class="card-value">{summary.total_duration_ms}ms</div><div class="card-label">总耗时</div></div>
            <div class="card"><div class="card-value">{summary.avg_duration_ms:.1f}ms</div><div class="card-label">平均耗时</div></div>
        </div>
    </section>"""

    # Assemble full HTML
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ConcurShield 评测报告</title>
<style>
:root {{
    --bg: #0d1117;
    --surface: #161b22;
    --surface2: #21262d;
    --border: #30363d;
    --text: #e6edf3;
    --text-dim: #8b949e;
    --pass: #3fb950;
    --pass-bg-c: rgba(63,185,80,0.15);
    --fail: #f85149;
    --fail-bg-c: rgba(248,81,73,0.15);
    --warn: #d29922;
    --warn-bg-c: rgba(210,153,34,0.15);
    --accent: #58a6ff;
    --radius: 8px;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
}}
h1 {{
    font-size: 1.8rem;
    margin-bottom: 0.5rem;
    background: linear-gradient(90deg, var(--accent), var(--pass));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}
h2 {{
    font-size: 1.3rem;
    margin-bottom: 1rem;
    color: var(--text);
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.5rem;
}}
section {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
}}
th, td {{
    padding: 0.5rem 0.75rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
}}
th {{ color: var(--text-dim); font-weight: 600; font-size: 0.8rem; text-transform: uppercase; }}
tr:hover {{ background: var(--surface2); }}
.meta-table td:first-child {{ color: var(--text-dim); width: 120px; }}
code {{ background: var(--surface2); padding: 0.15em 0.4em; border-radius: 4px; font-size: 0.85em; }}

/* Cards */
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin-bottom: 1rem; }}
.card {{
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
    text-align: center;
}}
.card-value {{ font-size: 1.6rem; font-weight: 700; }}
.card-label {{ font-size: 0.8rem; color: var(--text-dim); margin-top: 0.25rem; }}
.card.pass .card-value {{ color: var(--pass); }}
.card.fail .card-value {{ color: var(--fail); }}
.card.warn .card-value {{ color: var(--warn); }}

/* Bars */
.bar {{ height: 4px; background: var(--surface); border-radius: 2px; margin-top: 0.5rem; overflow: hidden; }}
.bar-inline {{ display: inline-block; width: 60px; height: 8px; background: var(--surface); border-radius: 4px; overflow: hidden; vertical-align: middle; margin-right: 0.5rem; }}
.bar-fill {{ height: 100%; border-radius: 2px; transition: width 0.3s; }}
.pass-bg {{ background: var(--pass); }}
.fail-bg {{ background: var(--fail); }}
.warn-bg {{ background: var(--warn); }}

/* Badges */
.badge {{
    display: inline-block;
    padding: 0.15em 0.5em;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
}}
.badge.pass {{ background: var(--pass-bg-c); color: var(--pass); }}
.badge.fail {{ background: var(--fail-bg-c); color: var(--fail); }}
.badge.warn {{ background: var(--warn-bg-c); color: var(--warn); }}
.badge.baseline {{ background: rgba(88,166,255,0.15); color: var(--accent); }}

/* Confusion matrix */
.cm-table {{ text-align: center; }}
.cm-table th, .cm-table td {{ width: 60px; text-align: center; }}
.cm-diag {{ background: var(--pass-bg-c); color: var(--pass); font-weight: 700; }}
.cm-off {{ background: var(--fail-bg-c); color: var(--fail); }}

/* Case details */
.case-table tr {{ cursor: pointer; }}
.status-icon {{ font-weight: 700; font-size: 1.1rem; }}
.status-icon.pass {{ color: var(--pass); }}
.status-icon.fail {{ color: var(--fail); }}
.status-icon.warn {{ color: var(--warn); }}
.pass-row {{ border-left: 3px solid var(--pass); }}
.fail-row {{ border-left: 3px solid var(--fail); }}
.warn-row {{ border-left: 3px solid var(--warn); }}
.detail-row {{ display: none; }}
.expanded + .detail-row {{ display: table-row; }}
.detail-content {{ padding: 0.75rem; background: var(--bg); border-radius: var(--radius); }}
.error-msg {{ color: var(--fail); margin-top: 0.5rem; font-family: monospace; white-space: pre-wrap; }}

/* Filter */
.filter-bar {{ display: flex; gap: 0.75rem; margin-bottom: 1rem; }}
.filter-bar input, .filter-bar select {{
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.5rem 0.75rem;
    color: var(--text);
    font-size: 0.9rem;
}}
.filter-bar input {{ flex: 1; }}
.filter-bar input:focus, .filter-bar select:focus {{ outline: none; border-color: var(--accent); }}
</style>
</head>
<body>

<header>
    <h1>ConcurShield 评测报告</h1>
    <table class="meta-table">
        <tbody>{meta_rows}</tbody>
    </table>
</header>

<section>
    <h2>总览</h2>
    {overview_html}
</section>

{score_html}
{cat_html}
{cm_html}
{slice_html}
{regression_html}
{case_html}
{cost_html}

<footer style="text-align:center; color:var(--text-dim); padding:2rem 0; font-size:0.8rem;">
    ConcurShield Eval Platform &mdash; {now}
</footer>

<script>
function filterCases() {{
    const text = document.getElementById('caseFilter').value.toLowerCase();
    const status = document.getElementById('statusFilter').value;
    const rows = document.querySelectorAll('#caseTable tbody tr');
    for (let i = 0; i < rows.length; i += 2) {{
        const dataRow = rows[i];
        const detailRow = rows[i + 1];
        const id = dataRow.querySelector('code')?.textContent.toLowerCase() || '';
        const cat = dataRow.children[2]?.textContent.toLowerCase() || '';
        const rowClass = dataRow.className;
        const matchText = !text || id.includes(text) || cat.includes(text);
        const matchStatus = status === 'all' || rowClass.includes(status);
        const show = matchText && matchStatus;
        dataRow.style.display = show ? '' : 'none';
        detailRow.style.display = 'none';
        dataRow.classList.remove('expanded');
    }}
}}
</script>
</body>
</html>"""
