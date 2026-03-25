"""指标计算器 — 从评测结果计算汇总指标。"""

from __future__ import annotations

from typing import List

from eval.models import EvalResult, EvalSummary

_TIERS = ["T1", "T2", "T3", "T4"]


def compute_metrics(results: List[EvalResult]) -> EvalSummary:
    """从 EvalResult 列表计算 EvalSummary。"""

    total = len(results)

    # ------------------------------------------------------------------
    # 1. 基础统计
    # ------------------------------------------------------------------
    errors = sum(1 for r in results if r.error is not None)
    passed = sum(1 for r in results if r.error is None and r.tier_match)
    failed = total - passed - errors

    # ------------------------------------------------------------------
    # 2. 按类别准确率
    # ------------------------------------------------------------------
    cat_stats: dict[str, dict] = {}
    for r in results:
        cat = r.category
        if cat not in cat_stats:
            cat_stats[cat] = {"total": 0, "passed": 0}
        cat_stats[cat]["total"] += 1
        if r.error is None and r.tier_match:
            cat_stats[cat]["passed"] += 1

    accuracy_by_category: dict[str, dict] = {}
    for cat, s in cat_stats.items():
        accuracy_by_category[cat] = {
            "total": s["total"],
            "passed": s["passed"],
            "accuracy": round(s["passed"] / s["total"], 4) if s["total"] else 0.0,
        }

    # ------------------------------------------------------------------
    # 3. 误报率: normal 中 actual_tier != "T1" 的比例
    # ------------------------------------------------------------------
    normal_cases = [r for r in results if r.category == "normal" and r.error is None]
    false_positives = sum(1 for r in normal_cases if r.actual_tier != "T1")
    false_positive_rate = (
        round(false_positives / len(normal_cases), 4) if normal_cases else 0.0
    )

    # ------------------------------------------------------------------
    # 4. 漏报率: 非 normal、非盲区中 actual_tier == "T1" 的比例
    # ------------------------------------------------------------------
    non_normal = [
        r for r in results
        if r.category != "normal"
        and r.error is None
        and not _is_known_blind_spot(r)
    ]
    false_negatives = sum(1 for r in non_normal if r.actual_tier == "T1")
    false_negative_rate = (
        round(false_negatives / len(non_normal), 4) if non_normal else 0.0
    )

    # ------------------------------------------------------------------
    # 5. 严重漏报数
    # ------------------------------------------------------------------
    severe_miss_count = sum(1 for r in results if r.is_severe_miss)

    # ------------------------------------------------------------------
    # 6. 混淆矩阵 4×4 (expected_tier_range[0] vs actual_tier)
    # ------------------------------------------------------------------
    confusion_matrix = _build_confusion_matrix(results)

    # ------------------------------------------------------------------
    # 7. 成本
    # ------------------------------------------------------------------
    total_api_calls = sum(r.api_calls for r in results)
    total_duration_ms = sum(r.duration_ms for r in results)
    avg_duration_ms = round(total_duration_ms / total, 2) if total else 0.0

    # ------------------------------------------------------------------
    # 8. 盲区结果
    # ------------------------------------------------------------------
    known_blind_spot_results = [
        {
            "case_id": r.case_id,
            "category": r.category,
            "expected_tier_range": r.expected_tier_range,
            "actual_tier": r.actual_tier,
            "tier_match": r.tier_match,
            "actual_signals": r.actual_signals,
            "notes": r.error or "",
        }
        for r in results
        if _is_known_blind_spot(r)
    ]

    return EvalSummary(
        total_cases=total,
        passed=passed,
        failed=failed,
        errors=errors,
        accuracy_by_category=accuracy_by_category,
        false_positive_rate=false_positive_rate,
        false_negative_rate=false_negative_rate,
        severe_miss_count=severe_miss_count,
        confusion_matrix=confusion_matrix,
        total_api_calls=total_api_calls,
        total_duration_ms=total_duration_ms,
        avg_duration_ms=avg_duration_ms,
        known_blind_spot_results=known_blind_spot_results,
    )


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


def _is_known_blind_spot(result: EvalResult) -> bool:
    """判断是否为已知盲区（通过 full_report 中保存的原始 TestCase 信息或 is_false_negative 逻辑推断）。"""
    # EvalResult 本身未保存 is_known_blind_spot，需从 full_report 或标记推断
    # 如果 is_false_negative 为 False 且 category != "normal" 且 actual_tier == "T1"，
    # 说明该用例是 known blind spot（runner 中的逻辑）
    if result.category != "normal" and result.actual_tier == "T1" and not result.is_false_negative:
        return True
    # 也检查 full_report 中是否保存了该标记
    if result.full_report and result.full_report.get("is_known_blind_spot"):
        return True
    return False


def _build_confusion_matrix(results: List[EvalResult]) -> dict:
    """构建 4×4 混淆矩阵: expected (行) vs actual (列)。

    expected 取 expected_tier_range[0] 作为主要预期等级。
    仅统计无错误的结果。
    """
    matrix: dict[str, dict[str, int]] = {
        t: {t2: 0 for t2 in _TIERS} for t in _TIERS
    }

    for r in results:
        if r.error is not None:
            continue
        expected = r.expected_tier_range[0] if r.expected_tier_range else r.expected_tier
        actual = r.actual_tier
        if expected in matrix and actual in matrix.get(expected, {}):
            matrix[expected][actual] += 1

    return matrix
