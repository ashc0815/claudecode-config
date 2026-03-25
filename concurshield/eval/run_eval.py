"""一键运行入口 — 增强版。

用法：
    python -m eval.run_eval                                    # 全部类别
    python -m eval.run_eval --categories normal tampered       # 指定类别
    python -m eval.run_eval --output eval_results              # 指定输出目录
    python -m eval.run_eval --name "v1.2 hotfix"               # 命名实验
    python -m eval.run_eval --baseline                         # 标记为 baseline
    python -m eval.run_eval --compare                          # 与 baseline 对比
    python -m eval.run_eval --slices                           # 启用切片分析
    python -m eval.run_eval --list-experiments                 # 列出历史实验
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from eval.runner import EvalRunner
from eval.metrics import compute_metrics
from eval.report import generate_markdown_report, generate_json_report
from eval.experiment import ExperimentStore
from eval.slicing import SliceAnalyzer


async def main() -> None:
    parser = argparse.ArgumentParser(description="ConcurShield 评测运行器")
    parser.add_argument(
        "--categories", nargs="+", default=None,
        help="要评测的类别 (默认全部)",
    )
    parser.add_argument(
        "--output", default="eval_results",
        help="结果输出目录 (默认 eval_results)",
    )
    parser.add_argument(
        "--name", default="",
        help="实验名称/标签",
    )
    parser.add_argument(
        "--baseline", action="store_true",
        help="标记此次运行为 baseline",
    )
    parser.add_argument(
        "--compare", action="store_true",
        help="运行后与 baseline 对比，检测回归",
    )
    parser.add_argument(
        "--slices", action="store_true",
        help="启用切片分析",
    )
    parser.add_argument(
        "--list-experiments", action="store_true",
        help="列出历史实验（不运行评测）",
    )
    args = parser.parse_args()

    store = ExperimentStore()

    # ------------------------------------------------------------------
    # 列出历史实验
    # ------------------------------------------------------------------
    if args.list_experiments:
        experiments = store.list_experiments()
        baseline_id = store.get_baseline_id()
        if not experiments:
            print("无历史实验记录。")
            return
        print(f"{'ID':<14} {'名称':<20} {'时间':<22} {'通过率':<10} {'Baseline'}")
        print("-" * 80)
        for exp in experiments:
            is_bl = "  *" if exp.experiment_id == baseline_id else ""
            pass_rate = ""
            if exp.summary:
                total = exp.summary.total_cases
                if total:
                    pass_rate = f"{exp.summary.passed}/{total} ({exp.summary.passed/total:.0%})"
            print(f"{exp.experiment_id:<14} {exp.name or '-':<20} {exp.created_at[:19]:<22} {pass_rate:<10}{is_bl}")
        return

    # ------------------------------------------------------------------
    # 运行评测
    # ------------------------------------------------------------------
    runner = EvalRunner(
        categories=args.categories,
        experiment_name=args.name,
    )
    total = len(runner.test_cases)
    cats = args.categories or "全部"
    print(f"=== ConcurShield 评测 ===")
    print(f"类别: {cats}  |  用例数: {total}")
    print(f"数据集版本: {runner.dataset.meta.version}")
    print(f"评估器: {[e.name for e in runner.evaluators]}\n")

    if total == 0:
        print("没有找到测试用例，退出。")
        return

    # 1. 运行实验
    experiment = await runner.run_experiment()

    if args.baseline:
        experiment.is_baseline = True

    # 2. 切片分析
    slice_metrics = None
    if args.slices:
        analyzer = SliceAnalyzer()
        slice_metrics = analyzer.analyze(experiment.results)
        print(f"\n切片分析: {len(slice_metrics)} 个切片")

    # 3. 回归对比
    regression = None
    if args.compare:
        regression = store.check_regression(experiment)
        if regression:
            status = "有退化!" if regression.has_regression else "无退化"
            print(f"\n回归对比: {status} (准确率变化: {regression.accuracy_delta:+.2%})")
        else:
            print("\n回归对比: 无 baseline，跳过")

    # 4. 保存实验
    store.save(experiment)
    print(f"\n实验已保存: {experiment.experiment_id}")
    if experiment.is_baseline:
        print("已标记为 baseline")

    # 5. 生成报告
    summary = experiment.summary
    results = experiment.results

    md_report = generate_markdown_report(
        summary, results,
        experiment=experiment,
        slice_metrics=slice_metrics,
        regression=regression,
    )
    json_report = generate_json_report(
        summary, results,
        experiment=experiment,
        slice_metrics=slice_metrics,
        regression=regression,
    )

    # 6. 保存文件
    out_dir = Path(args.output)
    runner.save_results(results, output_dir=args.output)

    (out_dir / "report.md").write_text(md_report, encoding="utf-8")
    (out_dir / "report.json").write_text(
        json.dumps(json_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 7. 打印摘要
    pass_rate = f"{summary.passed / summary.total_cases * 100:.1f}%" if summary.total_cases else "N/A"
    print(f"\n{'=' * 50}")
    print(f"实验 ID:   {experiment.experiment_id}")
    print(f"总用例:    {summary.total_cases}")
    print(f"通过率:    {summary.passed}/{summary.total_cases} ({pass_rate})")
    print(f"误报率:    {summary.false_positive_rate:.2%}")
    print(f"漏报率:    {summary.false_negative_rate:.2%}")
    print(f"严重漏报:  {summary.severe_miss_count}")

    if summary.score_summary:
        print(f"\n多维评分:")
        for name, stats in sorted(summary.score_summary.items()):
            print(f"  {name}: mean={stats['mean']:.2f}, pass_rate={stats['pass_rate']:.0%}")

    if regression and regression.has_regression:
        print(f"\n⚠️  检测到 {regression.regressed} 个回归!")

    print(f"{'=' * 50}")
    print(f"报告: {out_dir.resolve()}/report.md")
    print(f"实验历史: .eval_history/")


if __name__ == "__main__":
    asyncio.run(main())
