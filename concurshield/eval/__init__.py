"""ConcurShield evaluation platform.

架构灵感来自：
- Langfuse: Dataset → DatasetRun → Score 模式
- Langsmith: Evaluator → Experiment 模式
- Scale Nucleus: Slice-based evaluation 模式
- Anthropic "Demystifying Evals": 多维评分 + 诚实评估
"""

from .models import (
    TestCase,
    EvalResult,
    EvalSummary,
    Score,
    DatasetMeta,
    Experiment,
    SliceDefinition,
    RegressionResult,
    RegressionItem,
    load_all_test_cases,
)
from .dataset import Dataset
from .runner import EvalRunner
from .metrics import compute_metrics
from .report import generate_markdown_report, generate_json_report
from .experiment import ExperimentStore, compare_experiments
from .slicing import SliceAnalyzer, BUILTIN_SLICES

__all__ = [
    # 数据模型
    "TestCase",
    "EvalResult",
    "EvalSummary",
    "Score",
    "DatasetMeta",
    "Experiment",
    "SliceDefinition",
    "RegressionResult",
    "RegressionItem",
    # 数据集
    "Dataset",
    "load_all_test_cases",
    # 运行
    "EvalRunner",
    "compute_metrics",
    # 实验追踪
    "ExperimentStore",
    "compare_experiments",
    # 切片
    "SliceAnalyzer",
    "BUILTIN_SLICES",
    # 报告
    "generate_markdown_report",
    "generate_json_report",
]
