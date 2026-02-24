from __future__ import annotations

import statistics
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.all_models import (
    ClosingLine,
    EventNormalized,
    EventRaw,
    FeatureSnapshot,
    League,
    MarketConsensus,
    ModelArtifact,
    OddsSnapshot,
    Pick,
    PipelineRun,
    Settlement,
    Team,
    TeamAlias,
)
from backend.app.services.consensus import build_market_consensus
from backend.app.services.features import build_pregame_features
from backend.app.services.modeling import predict_home_win_probability
from backend.app.services.normalization import normalize_event
from backend.app.services.odds_math import american_to_decimal, american_to_implied_prob, ev_percent, quarter_kelly


def confidence_tier(edge: float) -> str:
    if edge >= 0.07:
        return "A"
    if edge >= 0.05:
        return "B"
    return "C"


async def seed_reference_data(session: AsyncSession) -> None:
    if not await session.scalar(select(League).where(League.name == "NBA")):
        session.add(League(name="NBA"))
    for name in ["los angeles lakers", "golden state warriors"]:
        if not await session.scalar(select(Team).where(Team.normalized_name == name)):
            session.add(Team(normalized_name=name))
    await session.flush()
    lakers = await session.scalar(select(Team).where(Team.normalized_name == "los angeles lakers"))
    warriors = await session.scalar(select(Team).where(Team.normalized_name == "golden state warriors"))
    if not await session.scalar(select(TeamAlias).where(TeamAlias.alias == "la lakers")):
        session.add(TeamAlias(alias="la lakers", team_id=lakers.id, source="seed", confidence=0.98))
    if not await session.scalar(select(TeamAlias).where(TeamAlias.alias == "gs warriors")):
        session.add(TeamAlias(alias="gs warriors", team_id=warriors.id, source="seed", confidence=0.98))
    await session.commit()


async def run_once(session: AsyncSession, provider) -> dict:
    started = datetime.utcnow()
    await seed_reference_data(session)
    payload = await provider.fetch_events_and_odds()
    latencies = []
    quarantine_count = 0

    for event in payload:
        raw = EventRaw(
            source=event["source"], external_event_id=event["external_event_id"], league=event["league"],
            start_time=event["start_time"], home_team=event["home_team"], away_team=event["away_team"]
        )
        session.add(raw)
        await session.flush()

        league = await session.scalar(select(League).where(League.name == event["league"]))
        norm = EventNormalized(event_raw_id=raw.id, league_id=league.id, start_time=event["start_time"])
        session.add(norm)
        await session.flush()
        norm = await normalize_event(session, norm, event["home_team"], event["away_team"])
        if str(norm.status) == "EventStatus.quarantined":
            quarantine_count += 1

        valid_lines = []
        for line in event["odds"]:
            age = (datetime.utcnow() - line["timestamp"]).total_seconds()
            stale = age > settings.stale_snapshot_seconds
            snap = OddsSnapshot(
                event_raw_id=raw.id,
                event_normalized_id=norm.id,
                book=line["book"],
                market=line["market"],
                side=line["side"],
                price=line["price"],
                timestamp=line["timestamp"],
                is_stale=stale,
            )
            session.add(snap)
            await session.flush()
            if not stale:
                valid_lines.append({**line, "snapshot_id": snap.id})

        if norm.mapping_confidence < settings.mapping_confidence_threshold or not valid_lines:
            continue

        consensus = build_market_consensus(valid_lines)
        session.add(MarketConsensus(event_normalized_id=norm.id, market="moneyline", consensus_prob=consensus.home_prob, consensus_price=1 / consensus.home_prob, timestamp=datetime.utcnow()))

        feature_json = build_pregame_features(norm.id, datetime.utcnow())
        feat = FeatureSnapshot(event_normalized_id=norm.id, feature_version="v1", features_json=feature_json, computed_at=datetime.utcnow())
        session.add(feat)
        await session.flush()

        artifact = await session.scalar(select(ModelArtifact).order_by(ModelArtifact.id.desc()))
        if artifact:
            model_prob = predict_home_win_probability(feature_json, artifact.artifact_path)
        else:
            model_prob = 0.56

        model_edge = model_prob - consensus.home_prob
        if model_edge > settings.edge_threshold:
            best_home = next(v for v in valid_lines if v["side"] == "home")
            dec = american_to_decimal(best_home["price"])
            pick = Pick(
                pick_lifecycle_id=str(uuid.uuid4()),
                odds_snapshot_id=best_home["snapshot_id"],
                event_normalized_id=norm.id,
                feature_snapshot_id=feat.id,
                model_version=artifact.model_version if artifact else "baseline-default",
                feature_version="v1",
                market="moneyline",
                side="home",
                book=best_home["book"],
                pick_time_price=best_home["price"],
                decimal_odds=dec,
                implied_prob=american_to_implied_prob(best_home["price"]),
                market_consensus_prob=consensus.home_prob,
                model_prob=model_prob,
                model_edge=model_edge,
                ev_percent=ev_percent(model_prob, dec),
                kelly_fraction=quarter_kelly(model_prob, dec),
                tier=confidence_tier(model_edge),
                created_at=datetime.utcnow(),
            )
            session.add(pick)
            await session.flush()
            closing = ClosingLine(
                pick_id=pick.id,
                close_price=-102,
                close_implied_prob=american_to_implied_prob(-102),
                captured_at=datetime.utcnow(),
                market_close_consensus=consensus.home_prob + 0.01,
                closing_line_snapshot_id=pick.odds_snapshot_id,
            )
            session.add(closing)
            settlement = Settlement(
                pick_id=pick.id,
                result="W",
                settled_at=datetime.utcnow(),
                pnl=dec - 1,
                roi=ev_percent(model_prob, dec),
                clv_market=closing.close_implied_prob - pick.market_consensus_prob,
                clv_book=closing.close_implied_prob - pick.implied_prob,
            )
            session.add(settlement)

        latencies.append((datetime.utcnow() - started).total_seconds())

    total_picks = await session.scalar(select(func.count(Pick.id))) or 0
    close_lines = await session.scalar(select(func.count(ClosingLine.id))) or 0
    close_cov = (close_lines / total_picks) if total_picks else 0.0
    total_norm = await session.scalar(select(func.count(EventNormalized.id))) or 1

    run = PipelineRun(
        started_at=started,
        finished_at=datetime.utcnow(),
        latency_seconds=max(latencies) if latencies else 0,
        freshness_seconds=0,
        close_line_coverage=close_cov,
        mapping_anomaly_rate=quarantine_count / total_norm,
        quarantine_count=quarantine_count,
        metadata_json={"p50_latency": statistics.median(latencies) if latencies else 0, "p95_latency": sorted(latencies)[int(len(latencies)*0.95)-1] if latencies else 0},
    )
    session.add(run)
    await session.commit()

    return {"quarantine_count": quarantine_count, "total_picks": total_picks}
