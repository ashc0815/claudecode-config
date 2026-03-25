"""LLM-as-Judge 评估器（占位实现）。

对标 Anthropic "Demystifying Evals" 中的 model-graded eval：
使用 LLM 对 pipeline 输出的报告质量进行主观评分。

第二阶段实现时，将调用 Claude API 进行评分。
"""

from __future__ import annotations

from typing import Any, Dict

from eval.evaluators.base import Evaluator
from eval.models import Score, TestCase


class LLMJudgeEvaluator(Evaluator):
    """LLM-as-Judge 评估器。

    当前为占位实现，返回 score=-1 表示未启用。
    第二阶段将实现：
    1. 构造 prompt（含 test_case + full_report）
    2. 调用 Claude API 评分
    3. 解析结构化输出为 Score
    """

    def __init__(self, rubric: str = "default"):
        self.rubric = rubric
        self._enabled = False

    @property
    def name(self) -> str:
        return "llm_judge"

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
        if not self._enabled:
            return Score(
                name=self.name,
                score=-1.0,
                label="disabled",
                reason="LLM judge not enabled. Set _enabled=True with API key.",
            )

        # TODO: 第二阶段实现
        # 1. Build prompt with rubric + full_report
        # 2. Call Claude API
        # 3. Parse structured output
        return Score(
            name=self.name, score=-1.0, label="not_implemented",
            reason="LLM judge evaluation not yet implemented",
        )
