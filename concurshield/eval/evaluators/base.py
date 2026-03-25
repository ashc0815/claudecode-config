"""评估器基类。

对标 Langsmith 的 run_evaluator / Langfuse 的 eval function。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from eval.models import Score, TestCase


class Evaluator(ABC):
    """评估器抽象基类。

    每个评估器对单个用例的 pipeline 输出打一个维度的分。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """评分维度名称。"""

    @abstractmethod
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
        """执行评估，返回 Score。"""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
