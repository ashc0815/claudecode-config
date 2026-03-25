"""可插拔评估器系统。

对标 Langsmith Evaluators / Langfuse Score 模式：
每个 Evaluator 接收 (TestCase, pipeline_output) → Score。
"""

from eval.evaluators.base import Evaluator
from eval.evaluators.tier import TierAccuracyEvaluator
from eval.evaluators.signals import SignalRecallEvaluator
from eval.evaluators.latency import LatencySLAEvaluator
from eval.evaluators.cost import CostEvaluator
from eval.evaluators.llm_judge import LLMJudgeEvaluator

# 默认评估器集合
DEFAULT_EVALUATORS: list[Evaluator] = [
    TierAccuracyEvaluator(),
    SignalRecallEvaluator(),
    LatencySLAEvaluator(),
    CostEvaluator(),
]

__all__ = [
    "Evaluator",
    "TierAccuracyEvaluator",
    "SignalRecallEvaluator",
    "LatencySLAEvaluator",
    "CostEvaluator",
    "LLMJudgeEvaluator",
    "DEFAULT_EVALUATORS",
]
