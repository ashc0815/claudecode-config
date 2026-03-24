"""评测数据模型（Pydantic v2）"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


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


class EvalResult(BaseModel):
    """单个用例的评测结果。"""

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


# ---------------------------------------------------------------------------
# 辅助函数
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
    """从 eval/test_cases/ 下所有 JSON 文件加载用例。

    Args:
        categories: 如果不为 None，只加载指定类别。

    Returns:
        加载的 TestCase 列表。
    """
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
