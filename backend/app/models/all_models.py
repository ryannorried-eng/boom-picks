from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class EventStatus(str, enum.Enum):
    scheduled = "scheduled"
    quarantined = "quarantined"
    settled = "settled"


class PickStatus(str, enum.Enum):
    open = "open"
    settled = "settled"


class ResultType(str, enum.Enum):
    W = "W"
    L = "L"
    P = "P"


class League(Base):
    __tablename__ = "leagues"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    normalized_name: Mapped[str] = mapped_column(String(80), unique=True)


class TeamAlias(Base):
    __tablename__ = "team_aliases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alias: Mapped[str] = mapped_column(String(120), unique=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    source: Mapped[str] = mapped_column(String(40), default="manual")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)


class EventRaw(Base):
    __tablename__ = "events_raw"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(50))
    external_event_id: Mapped[str] = mapped_column(String(100))
    league: Mapped[str] = mapped_column(String(20))
    start_time: Mapped[datetime] = mapped_column(DateTime)
    home_team: Mapped[str] = mapped_column(String(100))
    away_team: Mapped[str] = mapped_column(String(100))


class EventNormalized(Base):
    __tablename__ = "events_normalized"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_raw_id: Mapped[int] = mapped_column(ForeignKey("events_raw.id"))
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime)
    home_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    away_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    mapping_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus), default=EventStatus.scheduled)
    quarantine_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    __table_args__ = (UniqueConstraint("league_id", "start_time", "home_team_id", "away_team_id", name="uq_event_recon"),)


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_raw_id: Mapped[int] = mapped_column(ForeignKey("events_raw.id"))
    event_normalized_id: Mapped[int | None] = mapped_column(ForeignKey("events_normalized.id"), nullable=True)
    book: Mapped[str] = mapped_column(String(40))
    market: Mapped[str] = mapped_column(String(20), default="moneyline")
    side: Mapped[str] = mapped_column(String(10))
    price: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)


class MarketConsensus(Base):
    __tablename__ = "market_consensus"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_normalized_id: Mapped[int] = mapped_column(ForeignKey("events_normalized.id"))
    market: Mapped[str] = mapped_column(String(20), default="moneyline")
    consensus_prob: Mapped[float] = mapped_column(Float)
    consensus_price: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime)


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_normalized_id: Mapped[int] = mapped_column(ForeignKey("events_normalized.id"))
    feature_version: Mapped[str] = mapped_column(String(20))
    features_json: Mapped[dict] = mapped_column(JSON)
    computed_at: Mapped[datetime] = mapped_column(DateTime)


class ModelArtifact(Base):
    __tablename__ = "model_artifacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_version: Mapped[str] = mapped_column(String(40), unique=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime)
    training_window: Mapped[str] = mapped_column(String(120))
    metrics_json: Mapped[dict] = mapped_column(JSON)
    artifact_path: Mapped[str] = mapped_column(String(255))


class Pick(Base):
    __tablename__ = "picks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pick_lifecycle_id: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid.uuid4()), index=True)
    odds_snapshot_id: Mapped[int] = mapped_column(ForeignKey("odds_snapshots.id"))
    event_normalized_id: Mapped[int] = mapped_column(ForeignKey("events_normalized.id"))
    feature_snapshot_id: Mapped[int] = mapped_column(ForeignKey("feature_snapshots.id"))
    model_version: Mapped[str] = mapped_column(String(40))
    feature_version: Mapped[str] = mapped_column(String(20))
    market: Mapped[str] = mapped_column(String(20))
    side: Mapped[str] = mapped_column(String(10))
    book: Mapped[str] = mapped_column(String(40))
    pick_time_price: Mapped[int] = mapped_column(Integer)
    decimal_odds: Mapped[float] = mapped_column(Float)
    implied_prob: Mapped[float] = mapped_column(Float)
    market_consensus_prob: Mapped[float] = mapped_column(Float)
    model_prob: Mapped[float] = mapped_column(Float)
    model_edge: Mapped[float] = mapped_column(Float)
    ev_percent: Mapped[float] = mapped_column(Float)
    kelly_fraction: Mapped[float] = mapped_column(Float)
    tier: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[PickStatus] = mapped_column(Enum(PickStatus), default=PickStatus.open)


class ClosingLine(Base):
    __tablename__ = "closing_lines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pick_id: Mapped[int] = mapped_column(ForeignKey("picks.id"), unique=True)
    close_price: Mapped[int] = mapped_column(Integer)
    close_implied_prob: Mapped[float] = mapped_column(Float)
    captured_at: Mapped[datetime] = mapped_column(DateTime)
    market_close_consensus: Mapped[float | None] = mapped_column(Float, nullable=True)
    closing_line_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("odds_snapshots.id"), nullable=True)
    close_book_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    close_book_implied_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    close_market_consensus_prob: Mapped[float | None] = mapped_column(Float, nullable=True)


class Settlement(Base):
    __tablename__ = "settlements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pick_id: Mapped[int] = mapped_column(ForeignKey("picks.id"), unique=True)
    result: Mapped[ResultType] = mapped_column(Enum(ResultType))
    settled_at: Mapped[datetime] = mapped_column(DateTime)
    pnl: Mapped[float] = mapped_column(Float)
    roi: Mapped[float] = mapped_column(Float)
    clv_market: Mapped[float | None] = mapped_column(Float, nullable=True)
    clv_book: Mapped[float | None] = mapped_column(Float, nullable=True)
    settlement_source: Mapped[str] = mapped_column(String(20), default="simulated")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime] = mapped_column(DateTime)
    latency_seconds: Mapped[float] = mapped_column(Float)
    freshness_seconds: Mapped[float] = mapped_column(Float)
    close_line_coverage: Mapped[float] = mapped_column(Float)
    mapping_anomaly_rate: Mapped[float] = mapped_column(Float)
    quarantine_count: Mapped[int] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSON)
