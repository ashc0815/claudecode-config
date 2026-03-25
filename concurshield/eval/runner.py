"""批量运行器 — 运行评测用例并收集结果。"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import List, Optional

from eval.models import TestCase, EvalResult, load_all_test_cases

# pipeline 尚未实现时优雅降级
try:
    from concurshield.pipeline import analyze_receipt
except ImportError:
    analyze_receipt = None  # type: ignore[assignment]


class EvalRunner:
    """评测运行器。"""

    # 类别运行顺序：normal 先跑（建立哈希库），duplicates 其次，其他随后
    _CATEGORY_ORDER = ["normal", "duplicates"]

    def __init__(self, categories: Optional[List[str]] = None):
        self.test_cases = load_all_test_cases(categories)

    # ------------------------------------------------------------------
    # 单个用例
    # ------------------------------------------------------------------

    async def run_single(self, test_case: TestCase) -> EvalResult:
        """运行单个测试用例并返回 EvalResult。"""
        result = EvalResult(
            case_id=test_case.case_id,
            category=test_case.category,
            expected_tier=test_case.expected_tier,
            expected_tier_range=list(test_case.expected_tier_range),
        )

        # 1. 检查 image_path
        if not Path(test_case.image_path).exists():
            result.error = f"Image not found: {test_case.image_path}"
            return result

        # 2. pipeline 可用性检查
        if analyze_receipt is None:
            result.error = "concurshield.pipeline.analyze_receipt not available"
            return result

        # 3. 调用 pipeline
        start = time.monotonic()
        try:
            report = await analyze_receipt(test_case.image_path)
        except Exception as exc:
            result.duration_ms = int((time.monotonic() - start) * 1000)
            result.error = f"{type(exc).__name__}: {exc}"
            return result

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # 4. 从 ForensicReport 提取字段
        actual_tier: str = getattr(report, "tier", "")
        actual_score: float = float(getattr(report, "score", 0.0))
        actual_signals: List[str] = [
            s if isinstance(s, str) else getattr(s, "signal_id", str(s))
            for s in getattr(report, "signals", [])
        ]
        api_calls: int = int(getattr(report, "api_calls", 0))

        # 5. tier_match / signals_match
        tier_match = actual_tier in test_case.expected_tier_range
        expected_set = set(test_case.expected_signals)
        actual_set = set(actual_signals)
        signals_match = expected_set.issubset(actual_set) if expected_set else True

        # 6. 误报: normal 被判为非 T1
        is_false_positive = (
            test_case.category == "normal" and actual_tier != "T1"
        )

        # 7. 漏报: 非 normal、非盲区被判为 T1
        is_false_negative = (
            test_case.category != "normal"
            and actual_tier == "T1"
            and not test_case.is_known_blind_spot
        )

        # 8. 严重漏报: 期望含 T4 但实际仅 T1/T2
        is_severe_miss = (
            "T4" in test_case.expected_tier_range
            and actual_tier in ("T1", "T2")
        )

        # 组装结果
        result.actual_tier = actual_tier
        result.actual_score = actual_score
        result.actual_signals = actual_signals
        result.tier_match = tier_match
        result.signals_match = signals_match
        result.is_false_positive = is_false_positive
        result.is_false_negative = is_false_negative
        result.is_severe_miss = is_severe_miss
        result.api_calls = api_calls
        result.duration_ms = elapsed_ms
        result.full_report = (
            report.model_dump() if hasattr(report, "model_dump") else
            report.dict() if hasattr(report, "dict") else
            {"raw": str(report)}
        )

        return result

    # ------------------------------------------------------------------
    # 批量运行
    # ------------------------------------------------------------------

    async def run_all(self) -> List[EvalResult]:
        """按正确顺序运行所有用例并打印进度。"""
        ordered = self._order_test_cases(self.test_cases)
        total = len(ordered)
        results: List[EvalResult] = []

        for idx, tc in enumerate(ordered, 1):
            result = await self.run_single(tc)
            results.append(result)
            self._print_progress(idx, total, tc, result)

        return results

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    def save_results(
        self, results: List[EvalResult], output_dir: str = "eval_results"
    ) -> Path:
        """保存结果到 eval_results/ 目录。"""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        per_case_dir = out / "per_case"
        per_case_dir.mkdir(exist_ok=True)

        # results.json — 全部
        all_data = [r.model_dump() for r in results]
        (out / "results.json").write_text(
            json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # per_case/<case_id>.json
        for r in results:
            fp = per_case_dir / f"{r.case_id}.json"
            fp.write_text(
                json.dumps(r.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return out

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @classmethod
    def _order_test_cases(cls, cases: List[TestCase]) -> List[TestCase]:
        """按类别顺序排序: normal → duplicates → 其他。"""
        buckets: dict[str, List[TestCase]] = {}
        for tc in cases:
            buckets.setdefault(tc.category, []).append(tc)

        ordered: List[TestCase] = []
        # 先按优先类别
        for cat in cls._CATEGORY_ORDER:
            ordered.extend(buckets.pop(cat, []))
        # 其余按字母序
        for cat in sorted(buckets):
            ordered.extend(buckets[cat])
        return ordered

    @staticmethod
    def _print_progress(
        idx: int, total: int, tc: TestCase, result: EvalResult
    ) -> None:
        """打印单条进度。"""
        expected_range = "-".join(tc.expected_tier_range)

        if result.error:
            status = "⚠️ ERROR"
        elif result.is_false_negative:
            status = "❌ FALSE_NEGATIVE"
        elif result.is_false_positive:
            status = "❌ FALSE_POSITIVE"
        elif result.is_severe_miss:
            status = "❌ SEVERE_MISS"
        elif result.tier_match:
            status = "✅"
        else:
            status = "❌"

        print(
            f"[{idx}/{total}] {tc.case_id}: "
            f"{result.actual_tier or 'N/A'} "
            f"(expected {expected_range}) {status}"
        )
