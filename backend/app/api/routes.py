from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from datetime import datetime

from backend.app.models.all_models import ModelArtifact, Pick, PipelineRun, Settlement
from backend.app.schemas.pick import PickOut
from backend.app.services.modeling import train_baseline_model
from backend.app.services.pipeline import run_once
from backend.app.services.provider import MockOddsProvider

router = APIRouter()


@router.get('/health')
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    latest = await db.scalar(select(PipelineRun).order_by(PipelineRun.id.desc()))
    return {"status": "ok", "latest_pipeline_run": latest.id if latest else None}


@router.get('/picks/today', response_model=list[PickOut])
async def picks_today(db: AsyncSession = Depends(get_db)) -> list[PickOut]:
    rows = (await db.scalars(select(Pick).where(func.date(Pick.created_at) == date.today()))).all()
    return [PickOut.model_validate(r, from_attributes=True) for r in rows]


@router.get('/picks/{pick_id}', response_model=PickOut)
async def pick_by_id(pick_id: int, db: AsyncSession = Depends(get_db)) -> PickOut:
    row = await db.get(Pick, pick_id)
    return PickOut.model_validate(row, from_attributes=True)


@router.get('/metrics/clv')
async def clv_metrics(db: AsyncSession = Depends(get_db)) -> dict:
    settlements = (await db.scalars(select(Settlement))).all()
    if not settlements:
        return {"aggregate_clv_market": 0.0, "aggregate_clv_book": 0.0, "count": 0}
    return {
        "aggregate_clv_market": sum(s.clv_market for s in settlements) / len(settlements),
        "aggregate_clv_book": sum(s.clv_book for s in settlements) / len(settlements),
        "count": len(settlements),
    }


@router.post('/admin/retrain')
async def retrain(db: AsyncSession = Depends(get_db)) -> dict:
    samples = [
        {"team_win_loss_home_away": 0.6, "recent_form_last_n": 0.6, "head_to_head": 0.5, "rest_days_density": 0.0, "off_def_efficiency": 1.0, "home_court_advantage": 1.0},
        {"team_win_loss_home_away": 0.4, "recent_form_last_n": 0.4, "head_to_head": 0.5, "rest_days_density": -1.0, "off_def_efficiency": -1.0, "home_court_advantage": 1.0},
    ]
    labels = [1, 0]
    model_version = f"model-{int(datetime.utcnow().timestamp())}"
    artifact_path, metrics = train_baseline_model(samples, labels, model_version)
    db.add(ModelArtifact(model_version=model_version, trained_at=datetime.utcnow(), training_window="seed", metrics_json=metrics, artifact_path=artifact_path))
    await db.commit()
    return {"artifact_path": artifact_path, "metrics": metrics, "model_version": model_version}


@router.post('/admin/run-once')
async def admin_run_once(db: AsyncSession = Depends(get_db)) -> dict:
    return await run_once(db, MockOddsProvider())
