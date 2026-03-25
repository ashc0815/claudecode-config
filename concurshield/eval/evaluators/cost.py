"""成本效率评估器。"""

from __future__ import annotations

from typing import Any, Dict

from eval.evaluators.base import Evaluator
from eval.models import Score, TestCase


class CostEvaluator(Evaluator):
    """评估单次分析的 API 调用次数是否合理。

    默认阈值：
    - ≤ 3 次 → 1.0 (efficient)
    - ≤ 5 次 → 0.5 (acceptable)
    - > 5 次 → 0.0 (excessive)
    """

    def __init__(self, efficient_max: int = 3, acceptable_max: int = 5):
        self.efficient_max = efficient_max
        self.acceptable_max = acceptable_max

    @property
    def name(self) -> str:
        return "cost_efficiency"

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
        if api_calls <= self.efficient_max:
            return Score(
                name=self.name, score=1.0, label="efficient",
                reason=f"{api_calls} calls <= {self.efficient_max}",
            )
        if api_calls <= self.acceptable_max:
            return Score(
                name=self.name, score=0.5, label="acceptable",
                reason=f"{api_calls} calls <= {self.acceptable_max}",
            )
        return Score(
            name=self.name, score=0.0, label="excessive",
            reason=f"{api_calls} calls > {self.acceptable_max}",
        )
