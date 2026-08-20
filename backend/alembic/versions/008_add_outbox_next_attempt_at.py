"""add outbox next_attempt_at column and index

Revision ID: 008_add_outbox_next_attempt_at
Revises: 007_revision_fsm_and_outbox
Create Date: 2026-08-20 23:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '008_add_outbox_next_attempt_at'
down_revision: Union[str, None] = '007_revision_fsm_and_outbox'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('outbox_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_outbox_events_next_attempt_at', ['next_attempt_at'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('outbox_events', schema=None) as batch_op:
        batch_op.drop_index('ix_outbox_events_next_attempt_at')
        batch_op.drop_column('next_attempt_at')