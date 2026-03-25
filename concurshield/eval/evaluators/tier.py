"""Tier 准确率评估器。"""

from __future__ import annotations

from typing import Any, Dict

from eval.evaluators.base import Evaluator
from eval.models import Score, TestCase

_TIER_ORDER = {"T1": 0, "T2": 1, "T3": 2, "T4": 3}


class TierAccuracyEvaluator(Evaluator):
    """评估 actual_tier 是否在 expected_tier_range 内。

    评分：
    - 1.0: 精确匹配
    - 0.5: 偏差 1 级
    - 0.0: 偏差 ≥2 级或完全不匹配
    """

    @property
    def name(self) -> str:
        return "tier_accuracy"

    def evaluate(
        self,
        test_case: TestCase,
        actual_tier: str,
        actual_score: float,
        actual_signals: list[str],
        duration_ms: int,
        api_calls: int,
        full_report: Dict[str, Any] | None = None,
    ) -> Score:
        expected_range = test_case.expected_tier_range
        expected_primary = test_case.expected_tier

        if actual_tier in expected_range:
            return Score(
                name=self.name, score=1.0, label="pass",
                reason=f"{actual_tier} in {expected_range}",
            )

        # 计算与最近可接受 tier 的距离
        actual_idx = _TIER_ORDER.get(actual_tier, -1)
        if actual_idx < 0:
            return Score(
                name=self.name, score=0.0, label="fail",
                reason=f"Unknown tier: {actual_tier}",
            )

        min_distance = min(
            abs(actual_idx - _TIER_ORDER.get(t, 99))
            for t in expected_range
        )

        if min_distance == 1:
            return Score(
                name=self.name, score=0.5, label="partial",
                reason=f"{actual_tier} off by 1 from {expected_range}",
            )

        return Score(
            name=self.name, score=0.0, label="fail",
            reason=f"{actual_tier} off by {min_distance} from {expected_range}",
        )
