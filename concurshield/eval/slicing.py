"""切片分析 — 按维度对评测结果进行子集分析。

对标 Scale Nucleus 的 Slice-based evaluation：
- 预定义切片（按类别、按难度、按信号类型）
- 自定义切片（任意 predicate）
- 每个切片独立计算指标
"""

from __future__ import annotations

from typing import Dict, List

from eval.models import EvalResult, EvalSummary, SliceDefinition


# ---------------------------------------------------------------------------
# 预置切片
# ---------------------------------------------------------------------------

BUILTIN_SLICES: List[SliceDefinition] = [
    SliceDefinition(
        name="normal_only",
        description="仅正常发票（检测误报）",
        categories=["normal"],
    ),
    SliceDefinition(
        name="fraud_only",
        description="所有欺诈类型",
        categories=["tampered", "ai_generated", "prompt_injection", "duplicates"],
    ),
    SliceDefinition(
        name="high_risk",
        description="高风险: 期望 T3/T4 的用例",
    ),
    SliceDefinition(
        name="blind_spots",
        description="已知盲区用例",
        categories=["real_merchant_ai"],
    ),
]


def _is_high_risk(result: EvalResult) -> bool:
    """判断是否为高风险用例（期望 T3 或 T4）。"""
    return any(t in ("T3", "T4") for t in result.expected_tier_range)


# ---------------------------------------------------------------------------
# 切片分析
# ---------------------------------------------------------------------------

class SliceAnalyzer:
    """对评测结果进行切片分析。"""

    def __init__(self, slices: List[SliceDefinition] | None = None):
        self.slices = slices or BUILTIN_SLICES

    def analyze(
        self, results: List[EvalResult]
    ) -> Dict[str, SliceMetrics]:
        """对所有切片计算指标。"""
        output: Dict[str, SliceMetrics] = {}

        for s in self.slices:
            filtered = self._filter_results(results, s)
            if not filtered:
                continue
            output[s.name] = SliceMetrics.from_results(s, filtered)

        return output

    def _filter_results(
        self, results: List[EvalResult], slice_def: SliceDefinition
    ) -> List[EvalResult]:
        """按切片定义过滤结果。"""
        # 特殊切片用自定义逻辑
        if slice_def.name == "high_risk":
            return [r for r in results if _is_high_risk(r)]

        return [r for r in results if slice_def.matches_result(r)]


class SliceMetrics:
    """单个切片的指标。"""

    def __init__(
        self,
        slice_def: SliceDefinition,
        total: int,
        passed: int,
        failed: int,
        errors: int,
        false_positives: int,
        false_negatives: int,
        severe_misses: int,
        avg_duration_ms: float,
        score_means: Dict[str, float],
    ):
        self.slice_def = slice_def
        self.total = total
        self.passed = passed
        self.failed = failed
        self.errors = errors
        self.false_positives = false_positives
        self.false_negatives = false_negatives
        self.severe_misses = severe_misses
        self.avg_duration_ms = avg_duration_ms
        self.score_means = score_means

    @property
    def accuracy(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @classmethod
    def from_results(
        cls, slice_def: SliceDefinition, results: List[EvalResult]
    ) -> SliceMetrics:
        total = len(results)
        errors = sum(1 for r in results if r.error is not None)
        passed = sum(1 for r in results if r.error is None and r.tier_match)
        failed = total - passed - errors
        fp = sum(1 for r in results if r.is_false_positive)
        fn = sum(1 for r in results if r.is_false_negative)
        sm = sum(1 for r in results if r.is_severe_miss)
        durations = [r.duration_ms for r in results]
        avg_dur = sum(durations) / len(durations) if durations else 0.0

        # 按评分维度计算均值
        score_means: Dict[str, float] = {}
        if results and results[0].scores:
            score_names = [s.name for s in results[0].scores if s.score >= 0]
            for name in score_names:
                vals = [
                    s.score for r in results
                    for s in r.scores
                    if s.name == name and s.score >= 0
                ]
                if vals:
                    score_means[name] = round(sum(vals) / len(vals), 4)

        return cls(
            slice_def=slice_def,
            total=total,
            passed=passed,
            failed=failed,
            errors=errors,
            false_positives=fp,
            false_negatives=fn,
            severe_misses=sm,
            avg_duration_ms=round(avg_dur, 1),
            score_means=score_means,
        )

    def to_dict(self) -> dict:
        return {
            "slice": self.slice_def.name,
            "description": self.slice_def.description,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "accuracy": round(self.accuracy, 4),
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "severe_misses": self.severe_misses,
            "avg_duration_ms": self.avg_duration_ms,
            "score_means": self.score_means,
        }
