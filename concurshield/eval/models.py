"""评测数据模型（Pydantic v2）— 增强版。

新增模型：
- Score: 多维评分（Langsmith Evaluator 模式）
- DatasetMeta: 数据集版本元信息（Langfuse Dataset 模式）
- Experiment: 实验追踪（Langfuse DatasetRun 模式）
- SliceDefinition: 切片定义（Scale Nucleus 模式）
- RegressionResult: 回归对比结果
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 核心模型（保持向后兼容）
# ---------------------------------------------------------------------------

class TestCase(BaseModel):
    """单个评测用例。"""

    case_id: str = Field(..., description="用例 ID，如 NORMAL_001")
    category: str = Field(
        ...,
        description="类别: normal / tampered / ai_generated / prompt_injection / duplicates / real_merchant_ai",
    )
    image_path: str = Field(..., description="测试图片相对路径")
    description: str = Field(..., description="用例描述")
    expected_tier: str = Field(..., description="预期 Tier: T1 / T2 / T3 / T4")
    expected_tier_range: List[str] = Field(
        ..., description="可接受的 Tier 范围"
    )
    expected_signals: List[str] = Field(
        ..., description="预期触发的信号 ID"
    )
    is_known_blind_spot: bool = Field(
        False, description="是否为已知盲区"
    )
    notes: str = Field("", description="备注")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="自定义标签，用于切片分析"
    )


# ---------------------------------------------------------------------------
# 多维评分（Langsmith Evaluator 模式）
# ---------------------------------------------------------------------------

class Score(BaseModel):
    """单个评分维度。

    对标 Langfuse Score / Langsmith EvaluationResult。
    支持三种类型：numeric（0-1）、categorical、boolean。
    """

    name: str = Field(..., description="评分维度名，如 tier_accuracy")
    score: float = Field(..., description="归一化分数 0.0-1.0")
    label: str = Field("", description="分类标签，如 pass/fail")
    reason: str = Field("", description="评分理由")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvalResult(BaseModel):
    """单个用例的评测结果 — 增强版。"""

    case_id: str
    category: str
    expected_tier: str
    expected_tier_range: List[str]
    actual_tier: str = ""
    actual_score: float = 0.0
    actual_signals: List[str] = []
    tier_match: bool = False
    signals_match: bool = False
    is_false_positive: bool = False
    is_false_negative: bool = False
    is_severe_miss: bool = False
    api_calls: int = 0
    duration_ms: int = 0
    error: Optional[str] = None
    full_report: Optional[dict] = None
    # 新增：多维评分
    scores: List[Score] = Field(default_factory=list, description="多维评分")

    def get_score(self, name: str) -> Optional[Score]:
        """按名称获取评分。"""
        for s in self.scores:
            if s.name == name:
                return s
        return None


class EvalSummary(BaseModel):
    """整体评测汇总。"""

    total_cases: int
    passed: int
    failed: int
    errors: int
    accuracy_by_category: dict
    false_positive_rate: float
    false_negative_rate: float
    severe_miss_count: int
    confusion_matrix: dict
    total_api_calls: int
    total_duration_ms: int
    avg_duration_ms: float
    known_blind_spot_results: List[dict]
    # 新增：多维评分汇总
    score_summary: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="各评分维度的 mean / min / max / pass_rate",
    )


# ---------------------------------------------------------------------------
# 数据集版本化（Langfuse Dataset 模式）
# ---------------------------------------------------------------------------

class DatasetMeta(BaseModel):
    """数据集版本元信息。"""

    name: str = Field(default="concurshield-eval")
    version: str = Field(default="")
    content_hash: str = Field(default="", description="所有用例 JSON 的 SHA256")
    total_cases: int = 0
    categories: List[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @classmethod
    def from_test_cases(cls, cases: List[TestCase], name: str = "concurshield-eval") -> DatasetMeta:
        """从用例列表生成元信息。"""
        serialized = json.dumps(
            [tc.model_dump() for tc in cases], sort_keys=True, ensure_ascii=False
        )
        content_hash = hashlib.sha256(serialized.encode()).hexdigest()[:12]
        categories = sorted(set(tc.category for tc in cases))
        return cls(
            name=name,
            version=f"v-{content_hash}",
            content_hash=content_hash,
            total_cases=len(cases),
            categories=categories,
        )


# ---------------------------------------------------------------------------
# 实验追踪（Langfuse DatasetRun / Langsmith Experiment 模式）
# ---------------------------------------------------------------------------

class Experiment(BaseModel):
    """一次完整的评测实验。

    对标 Langfuse DatasetRun / Langsmith Experiment。
    """

    experiment_id: str = Field(
        default_factory=lambda: uuid4().hex[:12]
    )
    name: str = Field(default="", description="实验名称/标签")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    dataset: DatasetMeta = Field(default_factory=DatasetMeta)
    config: Dict[str, Any] = Field(
        default_factory=dict, description="运行时配置快照"
    )
    git_commit: str = Field(default="", description="Git commit SHA")
    summary: Optional[EvalSummary] = None
    results: List[EvalResult] = Field(default_factory=list)
    is_baseline: bool = Field(default=False, description="是否标记为基线")
    tags: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 切片定义（Scale Nucleus 模式）
# ---------------------------------------------------------------------------

class SliceDefinition(BaseModel):
    """切片定义，用于子集分析。"""

    name: str = Field(..., description="切片名称")
    description: str = Field(default="")
    # 过滤条件：category 列表 / metadata key-value / 自定义 case_id 列表
    categories: Optional[List[str]] = None
    metadata_filters: Dict[str, Any] = Field(default_factory=dict)
    case_ids: Optional[List[str]] = None
    # 对应函数式 predicate（运行时注入，不序列化）

    def matches(self, tc: TestCase) -> bool:
        """判断用例是否匹配此切片。"""
        if self.case_ids is not None:
            if tc.case_id not in self.case_ids:
                return False
        if self.categories is not None:
            if tc.category not in self.categories:
                return False
        for k, v in self.metadata_filters.items():
            if tc.metadata.get(k) != v:
                return False
        return True

    def matches_result(self, result: EvalResult) -> bool:
        """判断结果是否匹配此切片。"""
        if self.case_ids is not None:
            if result.case_id not in self.case_ids:
                return False
        if self.categories is not None:
            if result.category not in self.categories:
                return False
        return True


# ---------------------------------------------------------------------------
# 回归对比
# ---------------------------------------------------------------------------

class RegressionItem(BaseModel):
    """单个用例的回归变化。"""

    case_id: str
    change_type: str = Field(
        ..., description="improved / regressed / new_failure / fixed"
    )
    baseline_tier: str = ""
    current_tier: str = ""
    baseline_passed: bool = False
    current_passed: bool = False
    detail: str = ""


class RegressionResult(BaseModel):
    """两次实验的回归对比结果。"""

    baseline_id: str
    current_id: str
    total_compared: int = 0
    improved: int = 0
    regressed: int = 0
    new_failures: int = 0
    fixed: int = 0
    accuracy_delta: float = 0.0
    items: List[RegressionItem] = Field(default_factory=list)

    @property
    def has_regression(self) -> bool:
        return self.regressed > 0 or self.new_failures > 0


# ---------------------------------------------------------------------------
# 辅助函数（保持向后兼容）
# ---------------------------------------------------------------------------

_TEST_CASES_DIR = Path(__file__).parent / "test_cases"

_CATEGORY_FILE_MAP: dict[str, str] = {
    "normal": "normal.json",
    "tampered": "tampered.json",
    "ai_generated": "ai_generated.json",
    "prompt_injection": "prompt_injection.json",
    "duplicates": "duplicates.json",
    "real_merchant_ai": "real_merchant_ai.json",
}


def load_all_test_cases(
    categories: Optional[List[str]] = None,
) -> List[TestCase]:
    """从 eval/test_cases/ 下所有 JSON 文件加载用例。"""
    test_cases: List[TestCase] = []

    if categories is not None:
        files = [
            _TEST_CASES_DIR / _CATEGORY_FILE_MAP[cat]
            for cat in categories
            if cat in _CATEGORY_FILE_MAP
        ]
    else:
        files = sorted(_TEST_CASES_DIR.glob("*.json"))

    for fp in files:
        if not fp.exists():
            continue
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            test_cases.append(TestCase(**item))

    return test_cases
