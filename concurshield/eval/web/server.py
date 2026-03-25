"""ConcurShield 评测仪表盘 — FastAPI 服务端。

启动方式：
    python -m eval.web.server                   # 默认 0.0.0.0:8501
    python eval/web/server.py                   # 同上

API 路由：
    GET  /api/experiments              历史实验列表
    GET  /api/experiment/{id}          单个实验完整数据
    GET  /api/latest                   最新一次实验
    POST /api/run                      启动后台评测
    GET  /api/run/{run_id}/status      评测运行状态
    GET  /api/dataset                  测试用例集（按类别分组）
    GET  /api/compare/{id1}/{id2}      两次实验回归对比
"""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from eval.experiment import ExperimentStore, compare_experiments
from eval.metrics import compute_metrics
from eval.models import (
    EvalResult,
    Experiment,
    load_all_test_cases,
)
from eval.runner import EvalRunner

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="ConcurShield Eval Dashboard", version="1.0.0")

# 挂载静态文件
_STATIC_DIR = Path(__file__).parent / "static"
_STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/")
async def root():
    """根路由重定向到仪表盘首页。"""
    return RedirectResponse(url="/static/index.html")


# ---------------------------------------------------------------------------
# 辅助：安全序列化
# ---------------------------------------------------------------------------

def _jsonify(data: Any) -> JSONResponse:
    """JSONResponse 包装，处理 datetime 等不可序列化类型。"""
    payload = json.loads(json.dumps(data, ensure_ascii=False, default=str))
    return JSONResponse(payload)


# ---------------------------------------------------------------------------
# 后台评测运行状态存储
# ---------------------------------------------------------------------------

_runs: Dict[str, Dict[str, Any]] = {}


class RunRequest(BaseModel):
    categories: Optional[List[str]] = None
    name: str = ""
    case_ids: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# GET /api/experiments
# ---------------------------------------------------------------------------

@app.get("/api/experiments")
async def list_experiments():
    """返回所有历史实验的 JSON 列表。"""
    store = ExperimentStore()
    experiments = store.list_experiments()
    baseline_id = store.get_baseline_id()
    return _jsonify([
        {
            **_experiment_brief(exp),
            "is_baseline": exp.experiment_id == baseline_id,
        }
        for exp in experiments
    ])


def _experiment_brief(exp: Experiment) -> dict:
    """实验的简要信息（不含 results 以节省带宽）。"""
    return {
        "experiment_id": exp.experiment_id,
        "name": exp.name,
        "created_at": exp.created_at,
        "git_commit": exp.git_commit,
        "dataset_version": exp.dataset.version,
        "tags": exp.tags,
        "is_baseline": exp.is_baseline,
        "summary": exp.summary.model_dump() if exp.summary else None,
    }


# ---------------------------------------------------------------------------
# GET /api/experiment/{experiment_id}
# ---------------------------------------------------------------------------

@app.get("/api/experiment/{experiment_id}")
async def get_experiment(experiment_id: str):
    """加载指定实验的完整数据（含 results, summary, scores）。"""
    store = ExperimentStore()
    try:
        exp = store.load(experiment_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    return _jsonify(exp.model_dump())


# ---------------------------------------------------------------------------
# GET /api/latest
# ---------------------------------------------------------------------------

@app.get("/api/latest")
async def get_latest():
    """返回最新一次实验的数据。"""
    store = ExperimentStore()
    experiments = store.list_experiments()
    if not experiments:
        raise HTTPException(status_code=404, detail="No experiments found")
    # 按 created_at 倒序，取第一个
    latest = max(experiments, key=lambda e: e.created_at)
    # 轻量列表里 results 被清空了，重新完整加载
    exp = store.load(latest.experiment_id)
    return _jsonify(exp.model_dump())


# ---------------------------------------------------------------------------
# POST /api/run
# ---------------------------------------------------------------------------

@app.post("/api/run")
async def start_run(req: RunRequest):
    """在后台线程启动评测运行，立即返回 run_id。"""
    run_id = uuid.uuid4().hex[:12]

    _runs[run_id] = {
        "status": "starting",
        "progress": 0.0,
        "current_case": "",
        "completed": 0,
        "total": 0,
        "results_so_far": [],
        "experiment_id": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_eval_in_thread,
        args=(run_id, req.categories, req.name, req.case_ids),
        daemon=True,
    )
    thread.start()

    return _jsonify({"status": "started", "run_id": run_id})


def _run_eval_in_thread(
    run_id: str,
    categories: Optional[List[str]],
    name: str,
    case_ids: Optional[List[str]] = None,
) -> None:
    """在独立线程中运行评测，逐用例更新 _runs 状态。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_eval_async(run_id, categories, name, case_ids))
    except Exception as exc:
        _runs[run_id]["status"] = "error"
        _runs[run_id]["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        loop.close()


async def _run_eval_async(
    run_id: str,
    categories: Optional[List[str]],
    name: str,
    case_ids: Optional[List[str]] = None,
) -> None:
    """执行评测的 async 核心逻辑。"""
    runner = EvalRunner(categories=categories, experiment_name=name)
    ordered = runner._order_test_cases(runner.test_cases)
    # 如果指定了 case_ids，只跑这些用例
    if case_ids:
        id_set = set(case_ids)
        ordered = [tc for tc in ordered if tc.case_id in id_set]
    total = len(ordered)

    state = _runs[run_id]
    state["status"] = "running"
    state["total"] = total

    results: List[EvalResult] = []
    for idx, tc in enumerate(ordered, 1):
        state["current_case"] = tc.case_id
        result = await runner.run_single(tc)
        results.append(result)
        state["completed"] = idx
        state["progress"] = round(idx / total, 4) if total else 1.0
        state["results_so_far"].append(result.model_dump())

    # 计算汇总
    summary = compute_metrics(results)

    # 组装 Experiment
    exp = Experiment(
        name=name,
        dataset=runner.dataset.meta,
        config={},
        summary=summary,
        results=results,
    )
    from eval.experiment import ExperimentStore as _ES
    exp.git_commit = _ES._get_git_commit()

    # 保存
    store = ExperimentStore()
    store.save(exp)

    state["status"] = "completed"
    state["experiment_id"] = exp.experiment_id
    state["current_case"] = ""


# ---------------------------------------------------------------------------
# GET /api/run/{run_id}/status
# ---------------------------------------------------------------------------

@app.get("/api/run/{run_id}/status")
async def get_run_status(run_id: str):
    """返回当前运行状态。

    运行中：
        {"status": "running", "progress": 0.4, "current_case": "TAMPER_001",
         "completed": 4, "total": 10, "results_so_far": [...]}

    完成后：
        {"status": "completed", "experiment_id": "xxx", ...完整结果}
    """
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    state = _runs[run_id]
    resp: Dict[str, Any] = {
        "status": state["status"],
        "progress": state["progress"],
        "current_case": state["current_case"],
        "completed": state["completed"],
        "total": state["total"],
    }

    if state["status"] == "completed":
        resp["experiment_id"] = state["experiment_id"]
        # 完成后附带完整结果
        resp["results_so_far"] = state["results_so_far"]
    elif state["status"] == "running":
        resp["results_so_far"] = state["results_so_far"]
    elif state["status"] == "error":
        resp["error"] = state["error"]

    return _jsonify(resp)


# ---------------------------------------------------------------------------
# GET /api/dataset
# ---------------------------------------------------------------------------

@app.get("/api/dataset")
async def get_dataset():
    """返回所有测试用例，按类别分组，每个用例附带 image_exists。"""
    cases = load_all_test_cases()
    grouped: Dict[str, list] = {}
    for tc in cases:
        entry = tc.model_dump()
        entry["image_exists"] = Path(tc.image_path).exists()
        grouped.setdefault(tc.category, []).append(entry)
    return _jsonify({
        "total": len(cases),
        "categories": sorted(grouped.keys()),
        "by_category": grouped,
    })


# ---------------------------------------------------------------------------
# GET /api/compare/{exp_id_1}/{exp_id_2}
# ---------------------------------------------------------------------------

@app.get("/api/compare/{exp_id_1}/{exp_id_2}")
async def compare_experiments_api(exp_id_1: str, exp_id_2: str):
    """对比两次实验，返回 regression 信息和 delta 数据。"""
    store = ExperimentStore()
    try:
        exp1 = store.load(exp_id_1)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Experiment {exp_id_1} not found")
    try:
        exp2 = store.load(exp_id_2)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Experiment {exp_id_2} not found")

    regression = compare_experiments(exp1, exp2)

    # 额外计算 per-score delta
    score_delta: Dict[str, float] = {}
    if exp1.summary and exp2.summary:
        s1 = exp1.summary.score_summary
        s2 = exp2.summary.score_summary
        all_dims = set(s1.keys()) | set(s2.keys())
        for dim in all_dims:
            m1 = s1.get(dim, {}).get("mean", 0)
            m2 = s2.get(dim, {}).get("mean", 0)
            score_delta[dim] = round(m2 - m1, 4)

    return _jsonify({
        "regression": regression.model_dump(),
        "score_delta": score_delta,
        "exp1_summary": exp1.summary.model_dump() if exp1.summary else None,
        "exp2_summary": exp2.summary.model_dump() if exp2.summary else None,
    })


# ---------------------------------------------------------------------------
# 启动入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)
