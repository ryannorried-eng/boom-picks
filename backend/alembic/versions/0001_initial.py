"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-02-24
"""

from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('leagues', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('name', sa.String(50), unique=True))
    op.create_table('teams', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('normalized_name', sa.String(80), unique=True))
    op.create_table('team_aliases', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('alias', sa.String(120), unique=True), sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id')), sa.Column('source', sa.String(40)), sa.Column('confidence', sa.Float()))
    op.create_table('events_raw', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('source', sa.String(50)), sa.Column('external_event_id', sa.String(100)), sa.Column('league', sa.String(20)), sa.Column('start_time', sa.DateTime()), sa.Column('home_team', sa.String(100)), sa.Column('away_team', sa.String(100)))
    op.create_table('events_normalized', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('event_raw_id', sa.Integer(), sa.ForeignKey('events_raw.id')), sa.Column('league_id', sa.Integer(), sa.ForeignKey('leagues.id')), sa.Column('start_time', sa.DateTime()), sa.Column('home_team_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=True), sa.Column('away_team_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=True), sa.Column('mapping_confidence', sa.Float()), sa.Column('status', sa.String(20)), sa.Column('quarantine_reason', sa.String(255), nullable=True))
    op.create_unique_constraint('uq_event_recon', 'events_normalized', ['league_id', 'start_time', 'home_team_id', 'away_team_id'])
    op.create_table('odds_snapshots', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('event_raw_id', sa.Integer(), sa.ForeignKey('events_raw.id')), sa.Column('event_normalized_id', sa.Integer(), sa.ForeignKey('events_normalized.id'), nullable=True), sa.Column('book', sa.String(40)), sa.Column('market', sa.String(20)), sa.Column('side', sa.String(10)), sa.Column('price', sa.Integer()), sa.Column('timestamp', sa.DateTime()), sa.Column('is_stale', sa.Boolean()))
    op.create_table('market_consensus', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('event_normalized_id', sa.Integer(), sa.ForeignKey('events_normalized.id')), sa.Column('market', sa.String(20)), sa.Column('consensus_prob', sa.Float()), sa.Column('consensus_price', sa.Float()), sa.Column('timestamp', sa.DateTime()))
    op.create_table('feature_snapshots', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('event_normalized_id', sa.Integer(), sa.ForeignKey('events_normalized.id')), sa.Column('feature_version', sa.String(20)), sa.Column('features_json', sa.JSON()), sa.Column('computed_at', sa.DateTime()))
    op.create_table('model_artifacts', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('model_version', sa.String(40), unique=True), sa.Column('trained_at', sa.DateTime()), sa.Column('training_window', sa.String(120)), sa.Column('metrics_json', sa.JSON()), sa.Column('artifact_path', sa.String(255)))
    op.create_table('picks', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('pick_lifecycle_id', sa.String(36), index=True), sa.Column('odds_snapshot_id', sa.Integer(), sa.ForeignKey('odds_snapshots.id')), sa.Column('event_normalized_id', sa.Integer(), sa.ForeignKey('events_normalized.id')), sa.Column('feature_snapshot_id', sa.Integer(), sa.ForeignKey('feature_snapshots.id')), sa.Column('model_version', sa.String(40)), sa.Column('feature_version', sa.String(20)), sa.Column('market', sa.String(20)), sa.Column('side', sa.String(10)), sa.Column('book', sa.String(40)), sa.Column('pick_time_price', sa.Integer()), sa.Column('decimal_odds', sa.Float()), sa.Column('implied_prob', sa.Float()), sa.Column('market_consensus_prob', sa.Float()), sa.Column('model_prob', sa.Float()), sa.Column('model_edge', sa.Float()), sa.Column('ev_percent', sa.Float()), sa.Column('kelly_fraction', sa.Float()), sa.Column('tier', sa.String(20)), sa.Column('created_at', sa.DateTime()), sa.Column('status', sa.String(20)))
    op.create_table('closing_lines', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('pick_id', sa.Integer(), sa.ForeignKey('picks.id'), unique=True), sa.Column('close_price', sa.Integer()), sa.Column('close_implied_prob', sa.Float()), sa.Column('captured_at', sa.DateTime()), sa.Column('market_close_consensus', sa.Float(), nullable=True), sa.Column('closing_line_snapshot_id', sa.Integer(), sa.ForeignKey('odds_snapshots.id'), nullable=True))
    op.create_table('settlements', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('pick_id', sa.Integer(), sa.ForeignKey('picks.id'), unique=True), sa.Column('result', sa.String(2)), sa.Column('settled_at', sa.DateTime()), sa.Column('pnl', sa.Float()), sa.Column('roi', sa.Float()), sa.Column('clv_market', sa.Float()), sa.Column('clv_book', sa.Float()))
    op.create_table('pipeline_runs', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('started_at', sa.DateTime()), sa.Column('finished_at', sa.DateTime()), sa.Column('latency_seconds', sa.Float()), sa.Column('freshness_seconds', sa.Float()), sa.Column('close_line_coverage', sa.Float()), sa.Column('mapping_anomaly_rate', sa.Float()), sa.Column('quarantine_count', sa.Integer()), sa.Column('metadata_json', sa.JSON()))


def downgrade() -> None:
    for table in ['pipeline_runs','settlements','closing_lines','picks','model_artifacts','feature_snapshots','market_consensus','odds_snapshots','events_normalized','events_raw','team_aliases','teams','leagues']:
        op.drop_table(table)
