from __future__ import annotations

import statistics
import uuid
import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.all_models import (
    ClosingLine,
    EventNormalized,
    EventRaw,
    EventStatus,
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

logger = logging.getLogger(__name__)


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


def _select_closing_snapshot(valid_lines: list[dict], pick: Pick, event_start_time: datetime) -> dict | None:
    window_start = event_start_time - timedelta(minutes=settings.close_capture_window_minutes)
    candidates = [
        line
        for line in valid_lines
        if line["book"] == pick.book and line["side"] == pick.side and window_start <= line["timestamp"] <= event_start_time
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda row: row["timestamp"])


async def run_once(session: AsyncSession, provider) -> dict:
    started = datetime.utcnow()
    await seed_reference_data(session)
    payload = await provider.fetch_events_and_odds()
    latencies = []
    quarantine_count = 0
    events_processed = 0
    picks_emitted = 0
    block_reasons: dict[str, int] = {}

    for event in payload:
        events_processed += 1
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
        if norm.status == EventStatus.quarantined:
            quarantine_count += 1
        logger.info(
            "event_normalized",
            extra={
                "event_raw_id": raw.id,
                "event_normalized_id": norm.id,
                "mapping_confidence": norm.mapping_confidence,
                "quarantine_reason": norm.quarantine_reason,
            },
        )

        valid_lines = []
        for line in event["odds"]:
            age = (datetime.utcnow() - line["timestamp"]).total_seconds()
            stale = age > settings.stale_snapshot_max_age_seconds
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
                valid_lines.append({**line, "snapshot_id": snap.id, "is_stale": stale})

        if norm.mapping_confidence < settings.mapping_confidence_threshold:
            reason = "LOW_MAPPING_CONFIDENCE"
            block_reasons[reason] = block_reasons.get(reason, 0) + 1
            continue
        if not valid_lines:
            reason = "NO_FRESH_ODDS"
            block_reasons[reason] = block_reasons.get(reason, 0) + 1
            continue

        consensus_decision = build_market_consensus(valid_lines)
        stale_dropped_count = len(event["odds"]) - len(valid_lines)
        logger.info(
            "consensus_gate",
            extra={
                "event_normalized_id": norm.id,
                "books_count": len({line['book'] for line in valid_lines}),
                "stale_dropped_count": stale_dropped_count,
                "consensus_missing_reason": consensus_decision.missing_reason,
            },
        )
        if consensus_decision.result is None:
            norm.status = EventStatus.quarantined
            norm.quarantine_reason = consensus_decision.missing_reason
            quarantine_count += 1
            reason = consensus_decision.missing_reason or "CONSENSUS_UNAVAILABLE"
            block_reasons[reason] = block_reasons.get(reason, 0) + 1
            continue

        consensus = consensus_decision.result
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
        logger.info(
            "edge_gate",
            extra={
                "event_normalized_id": norm.id,
                "model_prob": model_prob,
                "market_prob": consensus.home_prob,
                "model_edge": model_edge,
                "edge_threshold": settings.edge_threshold,
            },
        )
        if model_edge > settings.edge_threshold:
            best_home = next((v for v in valid_lines if v["side"] == "home"), None)
            if best_home is None:
                reason = "NO_HOME_SIDE_LINE"
                block_reasons[reason] = block_reasons.get(reason, 0) + 1
                logger.info("pick_blocked", extra={"event_normalized_id": norm.id, "reason": reason})
                continue
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
            picks_emitted += 1
            logger.info(
                "pick_emitted",
                extra={
                    "event_normalized_id": norm.id,
                    "pick_id": pick.id,
                    "lifecycle_id": pick.pick_lifecycle_id,
                },
            )

            close_pick_book = _select_closing_snapshot(valid_lines, pick, event["start_time"])
            close_market_consensus_prob = None
            close_market = build_market_consensus(
                [line for line in valid_lines if (event["start_time"] - timedelta(minutes=settings.close_capture_window_minutes)) <= line["timestamp"] <= event["start_time"]],
                min_books=settings.consensus_min_books,
            )
            if close_market.result:
                close_market_consensus_prob = close_market.result.home_prob

            if close_pick_book:
                close_book_implied_prob = american_to_implied_prob(close_pick_book["price"])
                closing = ClosingLine(
                    pick_id=pick.id,
                    close_price=close_pick_book["price"],
                    close_implied_prob=close_book_implied_prob,
                    captured_at=close_pick_book["timestamp"],
                    market_close_consensus=close_market_consensus_prob,
                    closing_line_snapshot_id=close_pick_book["snapshot_id"],
                    close_book_price=close_pick_book["price"],
                    close_book_implied_prob=close_book_implied_prob,
                    close_market_consensus_prob=close_market_consensus_prob,
                )
                session.add(closing)
                clv_book = close_book_implied_prob - pick.implied_prob
                clv_market = None
                if close_market_consensus_prob is not None:
                    clv_market = close_market_consensus_prob - pick.implied_prob
                settlement = Settlement(
                    pick_id=pick.id,
                    result="W",
                    settled_at=datetime.utcnow(),
                    pnl=dec - 1,
                    roi=ev_percent(model_prob, dec),
                    clv_market=clv_market,
                    clv_book=clv_book,
                    settlement_source="simulated",
                )
                session.add(settlement)
        else:
            reason = "EDGE_BELOW_THRESHOLD"
            block_reasons[reason] = block_reasons.get(reason, 0) + 1
            logger.info("pick_blocked", extra={"event_normalized_id": norm.id, "reason": reason})

        latencies.append((datetime.utcnow() - started).total_seconds())

    total_picks = await session.scalar(select(func.count()).select_from(Pick)) or 0
    close_lines = await session.scalar(select(func.count()).select_from(ClosingLine)) or 0
    close_cov = (close_lines / total_picks) if total_picks else 0.0
    total_norm = await session.scalar(select(func.count()).select_from(EventNormalized)) or 1

    run = PipelineRun(
        started_at=started,
        finished_at=datetime.utcnow(),
        latency_seconds=max(latencies) if latencies else 0,
        freshness_seconds=0,
        close_line_coverage=close_cov,
        mapping_anomaly_rate=quarantine_count / total_norm,
        quarantine_count=quarantine_count,
        metadata_json={
            "p50_latency": statistics.median(latencies) if latencies else 0,
            "p95_latency": sorted(latencies)[int(len(latencies) * 0.95) - 1] if latencies else 0,
            "events_processed": events_processed,
            "picks_emitted": picks_emitted,
            "block_reasons": block_reasons,
        },
    )
    session.add(run)
    await session.commit()

    response = {
        "quarantine_count": quarantine_count,
        "total_picks": total_picks,
        "events_processed": events_processed,
        "picks_emitted_this_run": picks_emitted,
        "block_reasons": block_reasons,
    }
    if picks_emitted == 0:
        response["no_picks_reason"] = max(block_reasons, key=block_reasons.get) if block_reasons else "NO_ELIGIBLE_EVENTS"
    return response
