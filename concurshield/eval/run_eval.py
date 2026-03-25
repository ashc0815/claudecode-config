"""一键运行入口。

用法：
    python -m eval.run_eval                                # 全部类别
    python -m eval.run_eval --categories normal tampered   # 指定类别
    python -m eval.run_eval --output eval_results          # 指定输出目录
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from eval.runner import EvalRunner
from eval.metrics import compute_metrics
from eval.report import generate_markdown_report, generate_json_report


async def main() -> None:
    parser = argparse.ArgumentParser(description="ConcurShield 评测运行器")
    parser.add_argument(
        "--categories",
        nargs="+",
        default=None,
        help="要评测的类别 (默认全部)",
    )
    parser.add_argument(
        "--output",
        default="eval_results",
        help="结果输出目录 (默认 eval_results)",
    )
    args = parser.parse_args()

    # 1. 初始化
    runner = EvalRunner(categories=args.categories)
    total = len(runner.test_cases)
    cats = args.categories or "全部"
    print(f"=== ConcurShield 评测 ===")
    print(f"类别: {cats}  |  用例数: {total}\n")

    if total == 0:
        print("没有找到测试用例，退出。")
        return

    # 2. 运行
    results = await runner.run_all()

    # 3. 计算指标
    summary = compute_metrics(results)

    # 4. 生成报告
    md_report = generate_markdown_report(summary, results)
    json_report = generate_json_report(summary, results)

    # 5. 保存
    out_dir = Path(args.output)
    runner.save_results(results, output_dir=args.output)

    (out_dir / "report.md").write_text(md_report, encoding="utf-8")
    (out_dir / "report.json").write_text(
        json.dumps(json_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 6. 打印摘要
    pass_rate = f"{summary.passed / summary.total_cases * 100:.1f}%" if summary.total_cases else "N/A"
    print(f"\n{'=' * 40}")
    print(f"总用例:   {summary.total_cases}")
    print(f"通过率:   {summary.passed}/{summary.total_cases} ({pass_rate})")
    print(f"误报率:   {summary.false_positive_rate:.2%}")
    print(f"漏报率:   {summary.false_negative_rate:.2%}")
    print(f"严重漏报: {summary.severe_miss_count}")
    print(f"{'=' * 40}")
    print(f"报告已保存至: {out_dir.resolve()}")
    print(f"  - report.md")
    print(f"  - report.json")
    print(f"  - results.json")
    print(f"  - per_case/")


if __name__ == "__main__":
    asyncio.run(main())
