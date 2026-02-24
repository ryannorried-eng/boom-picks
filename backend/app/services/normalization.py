from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.all_models import EventNormalized, EventStatus, Team, TeamAlias


@dataclass
class Resolution:
    team_id: int | None
    confidence: float
    exact_alias_match: bool
    multiple_candidates: bool


async def resolve_team(session: AsyncSession, raw_name: str) -> Resolution:
    normalized = raw_name.lower()
    aliases = (await session.scalars(select(TeamAlias).where(TeamAlias.alias == normalized))).all()
    if len(aliases) > 1:
        return Resolution(team_id=None, confidence=0.0, exact_alias_match=False, multiple_candidates=True)
    if len(aliases) == 1:
        alias = aliases[0]
        return Resolution(team_id=alias.team_id, confidence=1.0, exact_alias_match=True, multiple_candidates=False)

    team = await session.scalar(select(Team).where(Team.normalized_name == normalized))
    if team:
        return Resolution(team_id=team.id, confidence=1.0, exact_alias_match=True, multiple_candidates=False)
    return Resolution(team_id=None, confidence=0.0, exact_alias_match=False, multiple_candidates=False)


def _time_confidence(event_start_time: datetime) -> tuple[float, str | None]:
    now = datetime.utcnow()
    diff_minutes = abs((event_start_time - now).total_seconds()) / 60
    if diff_minutes <= settings.mapping_time_tolerance_minutes:
        return 1.0, None
    if diff_minutes <= (settings.mapping_time_tolerance_minutes * 4):
        return 0.8, "TIME_MISMATCH"
    return 0.0, "TIME_MISMATCH"


async def normalize_event(session: AsyncSession, event_normalized: EventNormalized, home_name: str, away_name: str) -> EventNormalized:
    home = await resolve_team(session, home_name)
    away = await resolve_team(session, away_name)

    event_normalized.home_team_id = home.team_id
    event_normalized.away_team_id = away.team_id

    if home.multiple_candidates or away.multiple_candidates:
        event_normalized.mapping_confidence = 0.0
        event_normalized.status = EventStatus.quarantined
        event_normalized.quarantine_reason = "MULTIPLE_CANDIDATES"
        return event_normalized

    if not home.team_id or not away.team_id:
        event_normalized.mapping_confidence = 0.0
        event_normalized.status = EventStatus.quarantined
        event_normalized.quarantine_reason = "NO_ALIAS_MATCH"
        return event_normalized

    time_confidence, time_reason = _time_confidence(event_normalized.start_time)
    confidence = 1.0 if time_confidence == 1.0 else 0.8
    event_normalized.mapping_confidence = confidence

    if confidence < settings.mapping_confidence_threshold:
        event_normalized.status = EventStatus.quarantined
        event_normalized.quarantine_reason = time_reason or "LOW_MAPPING_CONFIDENCE"
    else:
        event_normalized.status = EventStatus.scheduled
        event_normalized.quarantine_reason = None
    return event_normalized
