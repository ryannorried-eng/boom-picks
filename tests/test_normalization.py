from datetime import datetime

from sqlalchemy import select

from backend.app.models.all_models import EventNormalized, EventRaw, League, Team, TeamAlias
from backend.app.services.normalization import normalize_event


async def test_deterministic_alias_mapping(session) -> None:
    league = League(name='NBA')
    lakers = Team(normalized_name='los angeles lakers')
    warriors = Team(normalized_name='golden state warriors')
    session.add_all([league, lakers, warriors])
    await session.flush()
    session.add_all([
        TeamAlias(alias='la lakers', team_id=lakers.id, source='test', confidence=0.99),
        TeamAlias(alias='gs warriors', team_id=warriors.id, source='test', confidence=0.99),
    ])
    raw = EventRaw(source='x', external_event_id='1', league='NBA', start_time=datetime.utcnow(), home_team='la lakers', away_team='gs warriors')
    session.add(raw)
    await session.flush()
    norm = EventNormalized(event_raw_id=raw.id, league_id=league.id, start_time=raw.start_time)
    session.add(norm)
    await session.flush()

    await normalize_event(session, norm, raw.home_team, raw.away_team)
    assert norm.mapping_confidence == 1.0
    assert norm.quarantine_reason is None
    assert norm.home_team_id == lakers.id


async def test_quarantine_on_unknown_team(session) -> None:
    league = League(name='NBA')
    session.add(league)
    await session.flush()
    raw = EventRaw(source='x', external_event_id='2', league='NBA', start_time=datetime.utcnow(), home_team='unknown', away_team='unknown2')
    session.add(raw)
    await session.flush()
    norm = EventNormalized(event_raw_id=raw.id, league_id=league.id, start_time=raw.start_time)
    session.add(norm)
    await session.flush()
    await normalize_event(session, norm, raw.home_team, raw.away_team)
    assert norm.quarantine_reason == 'NO_ALIAS_MATCH'
