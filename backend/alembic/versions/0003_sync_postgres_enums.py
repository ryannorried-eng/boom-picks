"""sync postgres enum columns with SQLAlchemy models

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    eventstatus = postgresql.ENUM('scheduled', 'quarantined', 'settled', name='eventstatus')
    pickstatus = postgresql.ENUM('open', 'settled', name='pickstatus')
    resulttype = postgresql.ENUM('W', 'L', 'P', name='resulttype')

    eventstatus.create(bind, checkfirst=True)
    pickstatus.create(bind, checkfirst=True)
    resulttype.create(bind, checkfirst=True)

    op.execute("""
        UPDATE events_normalized
        SET status = 'scheduled'
        WHERE status IS NULL OR status NOT IN ('scheduled', 'quarantined', 'settled')
    """)
    op.execute("""
        UPDATE picks
        SET status = 'open'
        WHERE status IS NULL OR status NOT IN ('open', 'settled')
    """)
    op.execute("""
        UPDATE settlements
        SET result = 'P'
        WHERE result IS NULL OR result NOT IN ('W', 'L', 'P')
    """)

    op.execute("ALTER TABLE events_normalized ALTER COLUMN status TYPE eventstatus USING status::eventstatus")
    op.execute("ALTER TABLE picks ALTER COLUMN status TYPE pickstatus USING status::pickstatus")
    op.execute("ALTER TABLE settlements ALTER COLUMN result TYPE resulttype USING result::resulttype")

    op.alter_column('events_normalized', 'status', server_default='scheduled', existing_type=eventstatus)
    op.alter_column('picks', 'status', server_default='open', existing_type=pickstatus)


def downgrade() -> None:
    op.alter_column('events_normalized', 'status', server_default=None)
    op.alter_column('picks', 'status', server_default=None)

    op.execute("ALTER TABLE events_normalized ALTER COLUMN status TYPE VARCHAR(20) USING status::text")
    op.execute("ALTER TABLE picks ALTER COLUMN status TYPE VARCHAR(20) USING status::text")
    op.execute("ALTER TABLE settlements ALTER COLUMN result TYPE VARCHAR(2) USING result::text")

    postgresql.ENUM(name='eventstatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='pickstatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='resulttype').drop(op.get_bind(), checkfirst=True)
