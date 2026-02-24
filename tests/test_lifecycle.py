from backend.app.models.all_models import Pick
from backend.app.services.pipeline import run_once
from backend.app.services.provider import MockOddsProvider
from sqlalchemy import select


async def test_pick_lifecycle_linkage(session) -> None:
    await run_once(session, MockOddsProvider())
    pick = await session.scalar(select(Pick).limit(1))
    assert pick is not None
    assert pick.pick_lifecycle_id
    assert pick.odds_snapshot_id
    assert pick.feature_snapshot_id
    assert pick.event_normalized_id
    assert pick.model_version
    assert pick.feature_version
