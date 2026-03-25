"""延迟 SLA 评估器。"""

from __future__ import annotations

from typing import Any, Dict

from eval.evaluators.base import Evaluator
from eval.models import Score, TestCase


class LatencySLAEvaluator(Evaluator):
    """评估分析耗时是否在 SLA 内。

    默认 SLA:
    - ≤ 3000ms → 1.0 (pass)
    - ≤ 5000ms → 0.5 (warn)
    - > 5000ms → 0.0 (fail)

    可通过构造函数自定义阈值。
    """

    def __init__(self, pass_ms: int = 3000, warn_ms: int = 5000):
        self.pass_ms = pass_ms
        self.warn_ms = warn_ms

    @property
    def name(self) -> str:
        return "latency_sla"

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
        if duration_ms <= self.pass_ms:
            return Score(
                name=self.name, score=1.0, label="pass",
                reason=f"{duration_ms}ms <= {self.pass_ms}ms SLA",
            )
        if duration_ms <= self.warn_ms:
            return Score(
                name=self.name, score=0.5, label="warn",
                reason=f"{duration_ms}ms > {self.pass_ms}ms but <= {self.warn_ms}ms",
            )
        return Score(
            name=self.name, score=0.0, label="fail",
            reason=f"{duration_ms}ms > {self.warn_ms}ms SLA",
        )
