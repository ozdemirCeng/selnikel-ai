"""ingestion jobs asynchronous worker table

Revision ID: 005_ingestion_jobs
Revises: 004_doc_elements
Create Date: 2026-08-19 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '005_ingestion_jobs'
down_revision: Union[str, None] = '004_doc_elements'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ingestion_jobs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('document_id', sa.String(length=36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('revision_id', sa.String(length=36), sa.ForeignKey('document_revisions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='queued'),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('attempt', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('worker_lease_id', sa.String(length=100), nullable=True),
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_jobs_state', 'ingestion_jobs', ['state'])
    op.create_index('idx_jobs_doc_id', 'ingestion_jobs', ['document_id'])


def downgrade() -> None:
    op.drop_table('ingestion_jobs')
