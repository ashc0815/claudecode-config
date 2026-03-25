"""实验追踪 — 存储、加载、对比、回归检测。

对标 Langfuse DatasetRun / Langsmith Experiment 模式：
- 每次 eval run = 一个 Experiment
- 存储在 .eval_history/ 目录
- 支持标记 baseline、对比两次实验、检测回归
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List, Optional

from eval.models import (
    EvalResult,
    EvalSummary,
    Experiment,
    DatasetMeta,
    RegressionItem,
    RegressionResult,
)

_HISTORY_DIR = Path(__file__).parent.parent.parent / ".eval_history"


class ExperimentStore:
    """实验持久化存储。"""

    def __init__(self, history_dir: Path | str = _HISTORY_DIR):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 创建
    # ------------------------------------------------------------------

    def create_experiment(
        self,
        name: str = "",
        dataset: DatasetMeta | None = None,
        config: dict | None = None,
        tags: list[str] | None = None,
    ) -> Experiment:
        """创建新实验。"""
        git_commit = self._get_git_commit()
        exp = Experiment(
            name=name,
            dataset=dataset or DatasetMeta(),
            config=config or {},
            git_commit=git_commit,
            tags=tags or [],
        )
        return exp

    # ------------------------------------------------------------------
    # 保存 / 加载
    # ------------------------------------------------------------------

    def save(self, experiment: Experiment) -> Path:
        """保存实验到磁盘。"""
        fp = self.history_dir / f"{experiment.experiment_id}.json"
        fp.write_text(
            json.dumps(experiment.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 维护 baseline 指针
        if experiment.is_baseline:
            self._set_baseline_pointer(experiment.experiment_id)

        return fp

    def load(self, experiment_id: str) -> Experiment:
        """加载指定实验。"""
        fp = self.history_dir / f"{experiment_id}.json"
        if not fp.exists():
            raise FileNotFoundError(f"Experiment {experiment_id} not found")
        data = json.loads(fp.read_text(encoding="utf-8"))
        return Experiment(**data)

    def list_experiments(self) -> List[Experiment]:
        """列出所有实验（不加载 results 以节省内存）。"""
        experiments = []
        for fp in sorted(self.history_dir.glob("*.json")):
            if fp.name == "baseline.txt":
                continue
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                # 轻量加载：清空 results
                data["results"] = []
                experiments.append(Experiment(**data))
            except Exception:
                continue
        return experiments

    # ------------------------------------------------------------------
    # Baseline 管理
    # ------------------------------------------------------------------

    def get_baseline_id(self) -> Optional[str]:
        """获取当前 baseline 实验 ID。"""
        pointer = self.history_dir / "baseline.txt"
        if pointer.exists():
            return pointer.read_text(encoding="utf-8").strip()
        return None

    def get_baseline(self) -> Optional[Experiment]:
        """加载 baseline 实验。"""
        bid = self.get_baseline_id()
        if bid:
            return self.load(bid)
        return None

    def set_baseline(self, experiment_id: str) -> None:
        """设置指定实验为 baseline。"""
        self._set_baseline_pointer(experiment_id)

    def _set_baseline_pointer(self, experiment_id: str) -> None:
        pointer = self.history_dir / "baseline.txt"
        pointer.write_text(experiment_id, encoding="utf-8")

    # ------------------------------------------------------------------
    # 回归检测
    # ------------------------------------------------------------------

    def compare(
        self,
        baseline_id: str,
        current_id: str,
    ) -> RegressionResult:
        """对比两次实验，检测回归。"""
        baseline = self.load(baseline_id)
        current = self.load(current_id)
        return compare_experiments(baseline, current)

    def check_regression(self, current: Experiment) -> Optional[RegressionResult]:
        """与 baseline 对比，返回回归结果。无 baseline 返回 None。"""
        bid = self.get_baseline_id()
        if not bid:
            return None
        baseline = self.load(bid)
        return compare_experiments(baseline, current)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    @staticmethod
    def _get_git_commit() -> str:
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()[:12]
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# 回归对比逻辑
# ---------------------------------------------------------------------------

def compare_experiments(
    baseline: Experiment, current: Experiment
) -> RegressionResult:
    """逐用例对比两次实验。"""
    baseline_map = {r.case_id: r for r in baseline.results}
    current_map = {r.case_id: r for r in current.results}
    all_ids = sorted(set(baseline_map) | set(current_map))

    items: List[RegressionItem] = []
    improved = regressed = new_failures = fixed = 0

    for cid in all_ids:
        b = baseline_map.get(cid)
        c = current_map.get(cid)

        if b is None or c is None:
            continue  # 新增或删除的用例，不算回归

        b_pass = b.error is None and b.tier_match
        c_pass = c.error is None and c.tier_match

        if b_pass and not c_pass:
            items.append(RegressionItem(
                case_id=cid, change_type="regressed",
                baseline_tier=b.actual_tier, current_tier=c.actual_tier,
                baseline_passed=True, current_passed=False,
                detail=f"Was {b.actual_tier} (pass), now {c.actual_tier} (fail)",
            ))
            regressed += 1
        elif not b_pass and c_pass:
            items.append(RegressionItem(
                case_id=cid, change_type="fixed",
                baseline_tier=b.actual_tier, current_tier=c.actual_tier,
                baseline_passed=False, current_passed=True,
                detail=f"Was {b.actual_tier} (fail), now {c.actual_tier} (pass)",
            ))
            fixed += 1
        elif not b_pass and not c_pass:
            # 两次都失败，但如果 tier 变化了也记录
            if b.actual_tier != c.actual_tier:
                items.append(RegressionItem(
                    case_id=cid, change_type="regressed" if _tier_worse(b, c) else "improved",
                    baseline_tier=b.actual_tier, current_tier=c.actual_tier,
                    baseline_passed=False, current_passed=False,
                    detail=f"Both fail: {b.actual_tier} -> {c.actual_tier}",
                ))
                if _tier_worse(b, c):
                    regressed += 1
                else:
                    improved += 1

    # 计算准确率变化
    b_acc = baseline.summary.passed / baseline.summary.total_cases if baseline.summary and baseline.summary.total_cases else 0
    c_acc = current.summary.passed / current.summary.total_cases if current.summary and current.summary.total_cases else 0

    return RegressionResult(
        baseline_id=baseline.experiment_id,
        current_id=current.experiment_id,
        total_compared=len(all_ids),
        improved=improved,
        regressed=regressed,
        new_failures=new_failures,
        fixed=fixed,
        accuracy_delta=round(c_acc - b_acc, 4),
        items=items,
    )


def _tier_worse(baseline: EvalResult, current: EvalResult) -> bool:
    """判断 current 的 tier 是否比 baseline 更偏离预期。"""
    _order = {"T1": 0, "T2": 1, "T3": 2, "T4": 3}
    expected = baseline.expected_tier_range[0] if baseline.expected_tier_range else baseline.expected_tier
    e_idx = _order.get(expected, 0)
    b_dist = abs(_order.get(baseline.actual_tier, 0) - e_idx)
    c_dist = abs(_order.get(current.actual_tier, 0) - e_idx)
    return c_dist > b_dist
