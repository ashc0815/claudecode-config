"""数据集管理 — 加载、版本化、过滤。

对标 Langfuse Dataset / Langsmith Dataset 模式：
- 数据集有版本（内容哈希）
- 支持按类别、标签、切片过滤
- 实验记录关联数据集版本，保证可复现
"""

from __future__ import annotations

from typing import List, Optional

from eval.models import (
    DatasetMeta,
    SliceDefinition,
    TestCase,
    load_all_test_cases,
)


class Dataset:
    """带版本追踪的评测数据集。"""

    def __init__(
        self,
        cases: List[TestCase],
        name: str = "concurshield-eval",
    ):
        self.cases = cases
        self.meta = DatasetMeta.from_test_cases(cases, name=name)

    # ------------------------------------------------------------------
    # 工厂方法
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        categories: Optional[List[str]] = None,
        name: str = "concurshield-eval",
    ) -> Dataset:
        """从 test_cases/ 加载数据集。"""
        cases = load_all_test_cases(categories)
        return cls(cases, name=name)

    # ------------------------------------------------------------------
    # 过滤
    # ------------------------------------------------------------------

    def filter_by_categories(self, categories: List[str]) -> Dataset:
        """返回仅包含指定类别的子集。"""
        filtered = [tc for tc in self.cases if tc.category in categories]
        return Dataset(filtered, name=self.meta.name)

    def filter_by_slice(self, slice_def: SliceDefinition) -> Dataset:
        """返回匹配切片定义的子集。"""
        filtered = [tc for tc in self.cases if slice_def.matches(tc)]
        return Dataset(filtered, name=f"{self.meta.name}:{slice_def.name}")

    def filter_by_ids(self, case_ids: List[str]) -> Dataset:
        """返回指定 case_id 的子集。"""
        id_set = set(case_ids)
        filtered = [tc for tc in self.cases if tc.case_id in id_set]
        return Dataset(filtered, name=self.meta.name)

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------

    @property
    def categories(self) -> List[str]:
        return self.meta.categories

    def __len__(self) -> int:
        return len(self.cases)

    def __iter__(self):
        return iter(self.cases)

    def __repr__(self) -> str:
        return (
            f"Dataset(name={self.meta.name!r}, version={self.meta.version!r}, "
            f"cases={len(self.cases)}, categories={self.meta.categories})"
        )
