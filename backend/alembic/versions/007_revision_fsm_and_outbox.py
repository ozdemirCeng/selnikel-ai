"""revision fsm, partial unique index and outbox events

Revision ID: 007_revision_fsm_and_outbox
Revises: 006_ext_id_queue_hardening
Create Date: 2026-08-20 22:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '007_revision_fsm_and_outbox'
down_revision: Union[str, None] = '006_ext_id_queue_hardening'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create outbox_events table for transactional outbox pattern
    op.create_table(
        'outbox_events',
        sa.Column('event_id', sa.String(length=36), primary_key=True),
        sa.Column('aggregate_type', sa.String(length=100), nullable=False, index=True),
        sa.Column('aggregate_id', sa.String(length=36), nullable=False, index=True),
        sa.Column('event_type', sa.String(length=100), nullable=False, index=True),
        sa.Column('idempotency_key', sa.String(length=128), unique=True, nullable=False, index=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False, index=True),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_retries', sa.Integer(), server_default='5', nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # 2. Add obsoleted_at to document_revisions table
    with op.batch_alter_table('document_revisions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('obsoleted_at', sa.DateTime(timezone=True), nullable=True))
        # 3. Create physical partial unique index guaranteeing at most 1 approved revision per document_id
        batch_op.create_index(
            'uq_document_single_approved_revision',
            ['document_id'],
            unique=True,
            postgresql_where=sa.text("approval_status = 'approved'"),
            sqlite_where=sa.text("approval_status = 'approved'"),
        )


def downgrade() -> None:
    with op.batch_alter_table('document_revisions', schema=None) as batch_op:
        batch_op.drop_index('uq_document_single_approved_revision')
        batch_op.drop_column('obsoleted_at')

    op.drop_table('outbox_events')