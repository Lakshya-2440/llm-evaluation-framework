from __future__ import annotations

import asyncio
import uuid
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.db import Database
from app.schemas import (
    BenchmarkDataset,
    ComparisonItem,
    EvalRunCreated,
    EvalRunDetail,
    EvalRunListItem,
    EvalRunRequest,
    EvalRunStatus,
    ReportFormat,
)
from app.services.attack_library import list_attack_catalog
from app.services.datasets import BENCHMARKS
from app.services.engine import EvaluationEngine
from app.services.model_clients import HuggingFaceChatClient
from app.services.reports import csv_export, executive_markdown, json_export, simple_pdf_bytes, summarize_run, technical_markdown

settings = get_settings()
db = Database(settings.database_path)
client = HuggingFaceChatClient(settings)
engine = EvaluationEngine(db, client, settings.max_parallelism)

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    db.init()


def require_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "ok": True,
        "app": settings.app_name,
        "hf_configured": bool(settings.hf_token),
        "database": str(settings.database_path),
    }


@app.get("/catalog/attacks")
def attack_catalog(_: Annotated[None, Depends(require_api_key)]) -> dict[str, object]:
    return list_attack_catalog()


@app.get("/datasets", response_model=list[BenchmarkDataset])
def datasets(_: Annotated[None, Depends(require_api_key)]) -> list[BenchmarkDataset]:
    return BENCHMARKS


@app.post("/eval/run", response_model=EvalRunCreated)
async def create_eval_run(
    request: EvalRunRequest,
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(require_api_key)],
) -> EvalRunCreated:
    run_id = str(uuid.uuid4())
    target_model = request.target_model or settings.default_target_model
    attacker_model = request.attacker_model or settings.default_attacker_model
    judge_model = request.judge_model or settings.default_judge_model
    config = request.model_dump()
    config.update(
        {
            "target_model": target_model,
            "attacker_model": attacker_model,
            "judge_model": judge_model,
        }
    )
    db.create_run(
        {
            "id": run_id,
            "target_model": target_model,
            "attacker_model": attacker_model,
            "judge_model": judge_model,
            "attack_suite_id": request.attack_suite_id,
            "config": config,
        }
    )
    background_tasks.add_task(lambda: asyncio.run(engine.run(run_id)))
    return EvalRunCreated(id=run_id, status="queued")


@app.get("/eval/run", response_model=list[EvalRunListItem])
def list_eval_runs(
    _: Annotated[None, Depends(require_api_key)],
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, object]]:
    return db.list_runs(limit=limit)


@app.get("/eval/run/{run_id}/status", response_model=EvalRunStatus)
def get_eval_status(run_id: str, _: Annotated[None, Depends(require_api_key)]) -> dict[str, object]:
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")
    return run


@app.get("/eval/run/{run_id}", response_model=EvalRunDetail)
def get_eval_detail(run_id: str, _: Annotated[None, Depends(require_api_key)]) -> dict[str, object]:
    run = db.get_run_detail(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")
    return run


@app.get("/eval/compare", response_model=list[ComparisonItem])
def compare_runs(
    _: Annotated[None, Depends(require_api_key)],
    run_ids: str = Query(description="Comma-separated eval run IDs."),
) -> list[ComparisonItem]:
    items: list[ComparisonItem] = []
    for run_id in [value.strip() for value in run_ids.split(",") if value.strip()]:
        detail = db.get_run_detail(run_id)
        if not detail:
            continue
        summary = detail.get("summary") or summarize_run(detail)
        items.append(
            ComparisonItem(
                run_id=run_id,
                target_model=detail["target_model"],
                status=detail["status"],
                pass_rate=summary["pass_rate"],
                average_risk=summary["average_risk"],
                category_pass_rates=summary["category_pass_rates"],
                n_attacks=summary["n_attacks"],
            )
        )
    return items


@app.get("/eval/run/{run_id}/report")
def get_report(
    run_id: str,
    _: Annotated[None, Depends(require_api_key)],
    format: ReportFormat = Query(default="technical"),
) -> Response:
    detail = db.get_run_detail(run_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")
    if not detail.get("summary"):
        detail["summary"] = summarize_run(detail)

    if format == "json":
        return Response(json_export(detail), media_type="application/json")
    if format == "csv":
        return Response(csv_export(detail), media_type="text/csv")
    if format == "executive":
        return Response(executive_markdown(detail), media_type="text/markdown")
    if format == "pdf":
        markdown = executive_markdown(detail)
        return Response(
            simple_pdf_bytes(f"LLM Eval Report {run_id}", markdown),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="llm-eval-{run_id}.pdf"'},
        )
    return Response(technical_markdown(detail), media_type="text/markdown")
