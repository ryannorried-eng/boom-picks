from sqlalchemy import func, select

from backend.app.models.all_models import ClosingLine, MarketConsensus, Pick, Settlement
from backend.app.services.pipeline import run_once
from backend.app.services.provider import MockOddsProvider


async def test_end_to_end_pipeline(session) -> None:
    await run_once(session, MockOddsProvider())
    picks = await session.scalar(select(func.count(Pick.id)))
    consensus = await session.scalar(select(func.count(MarketConsensus.id)))
    close = await session.scalar(select(func.count(ClosingLine.id)))
    settlement = await session.scalar(select(func.count(Settlement.id)))
    assert picks >= 1
    assert consensus >= 1
    assert close >= 1
    assert settlement >= 1
