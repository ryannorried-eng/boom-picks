from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.all_models import EventNormalized, EventStatus, Team, TeamAlias


@dataclass
class Resolution:
    team_id: int | None
    confidence: float


async def resolve_team(session: AsyncSession, raw_name: str) -> Resolution:
    alias = await session.scalar(select(TeamAlias).where(TeamAlias.alias == raw_name.lower()))
    if alias:
        return Resolution(team_id=alias.team_id, confidence=alias.confidence)

    team = await session.scalar(select(Team).where(Team.normalized_name == raw_name.lower()))
    if team:
        return Resolution(team_id=team.id, confidence=1.0)
    return Resolution(team_id=None, confidence=0.0)


async def normalize_event(session: AsyncSession, event_normalized: EventNormalized, home_name: str, away_name: str) -> EventNormalized:
    home = await resolve_team(session, home_name)
    away = await resolve_team(session, away_name)
    confidence = min(home.confidence, away.confidence)
    event_normalized.home_team_id = home.team_id
    event_normalized.away_team_id = away.team_id
    event_normalized.mapping_confidence = confidence
    if confidence < settings.mapping_confidence_threshold:
        event_normalized.status = EventStatus.quarantined
        event_normalized.quarantine_reason = "low_mapping_confidence"
    else:
        event_normalized.status = EventStatus.scheduled
    return event_normalized
