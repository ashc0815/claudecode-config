"""信号召回率评估器。"""

from __future__ import annotations

from typing import Any, Dict

from eval.evaluators.base import Evaluator
from eval.models import Score, TestCase


class SignalRecallEvaluator(Evaluator):
    """评估 expected_signals 中有多少被实际检测到。

    评分 = 召回率 (0.0-1.0)。
    如果 expected_signals 为空，返回 1.0（无需检测信号的用例）。
    """

    @property
    def name(self) -> str:
        return "signal_recall"

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
        expected = set(test_case.expected_signals)

        if not expected:
            return Score(
                name=self.name, score=1.0, label="pass",
                reason="No signals expected",
            )

        actual = set(actual_signals)
        hits = expected & actual
        recall = len(hits) / len(expected)

        missed = expected - actual
        label = "pass" if recall >= 1.0 else "partial" if recall > 0 else "fail"

        return Score(
            name=self.name,
            score=round(recall, 4),
            label=label,
            reason=f"Recalled {len(hits)}/{len(expected)}"
                   + (f", missed: {sorted(missed)}" if missed else ""),
        )
