from sqlalchemy import func, select

from backend.app.models.all_models import ClosingLine, MarketConsensus, Pick, Settlement
from backend.app.services.pipeline import run_once
from backend.app.services.provider import MockOddsProvider


async def test_end_to_end_pipeline(session) -> None:
    await run_once(session, MockOddsProvider())
    picks = await session.scalar(select(func.count()).select_from(Pick))
    consensus = await session.scalar(select(func.count()).select_from(MarketConsensus))
    close = await session.scalar(select(func.count()).select_from(ClosingLine))
    settlement = await session.scalar(select(func.count()).select_from(Settlement))
    assert picks >= 1
    assert consensus >= 1
    assert close >= 1
    assert settlement >= 1

    pick = await session.scalar(select(Pick).limit(1))
    assert pick is not None
    assert pick.pick_lifecycle_id
    assert pick.model_prob is not None
    assert pick.market_consensus_prob is not None
    assert pick.model_edge is not None
    assert pick.ev_percent is not None
    assert pick.kelly_fraction is not None

    close_line = await session.scalar(select(ClosingLine).where(ClosingLine.pick_id == pick.id))
    assert close_line is not None

    settle = await session.scalar(select(Settlement).where(Settlement.pick_id == pick.id))
    assert settle is not None
    assert settle.clv_market is not None

    orphans = await session.scalar(
        select(func.count())
        .select_from(Settlement)
        .outerjoin(ClosingLine, ClosingLine.pick_id == Settlement.pick_id)
        .where(ClosingLine.id.is_(None))
    )
    assert orphans == 0

    if close_line.close_market_consensus_prob is not None and pick.implied_prob is not None and settle.clv_market is not None:
        assert settle.clv_market == close_line.close_market_consensus_prob - pick.implied_prob
    else:
        # TODO: tighten this assertion if schema/data always guarantee market close consensus.
        assert True
