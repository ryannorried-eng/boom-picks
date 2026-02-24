"""add hardening fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-24
"""

from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('closing_lines', sa.Column('close_book_price', sa.Integer(), nullable=True))
    op.add_column('closing_lines', sa.Column('close_book_implied_prob', sa.Float(), nullable=True))
    op.add_column('closing_lines', sa.Column('close_market_consensus_prob', sa.Float(), nullable=True))
    op.add_column('settlements', sa.Column('settlement_source', sa.String(length=20), nullable=False, server_default='simulated'))


def downgrade() -> None:
    op.drop_column('settlements', 'settlement_source')
    op.drop_column('closing_lines', 'close_market_consensus_prob')
    op.drop_column('closing_lines', 'close_book_implied_prob')
    op.drop_column('closing_lines', 'close_book_price')
