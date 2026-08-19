"""external identities and ingestion jobs queue hardening

Revision ID: 006_ext_id_queue_hardening
Revises: 005_ingestion_jobs
Create Date: 2026-08-19 23:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006_ext_id_queue_hardening'
down_revision: Union[str, None] = '005_ingestion_jobs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create user_external_identities table for immutable OIDC subject/issuer mapping
    op.create_table(
        'user_external_identities',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('issuer', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_authenticated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('issuer', 'subject', 'tenant_id', name='uq_user_external_identity'),
    )
    op.create_index('idx_ext_ident_user_id', 'user_external_identities', ['user_id'])
    op.create_index('idx_ext_ident_iss_sub', 'user_external_identities', ['issuer', 'subject'])
    op.create_index('idx_ext_ident_tenant', 'user_external_identities', ['tenant_id'])

    # 2. Add queue hardening columns to ingestion_jobs
    op.add_column('ingestion_jobs', sa.Column('filename', sa.String(length=255), nullable=True))
    op.add_column('ingestion_jobs', sa.Column('file_path', sa.String(length=500), nullable=True))
    op.add_column('ingestion_jobs', sa.Column('department_id', sa.String(length=50), nullable=True))
    op.add_column('ingestion_jobs', sa.Column('file_size_bytes', sa.Integer(), nullable=True))
    op.add_column('ingestion_jobs', sa.Column('mime_type', sa.String(length=100), nullable=True))
    op.add_column('ingestion_jobs', sa.Column('sha256_hash', sa.String(length=64), nullable=True))
    op.add_column('ingestion_jobs', sa.Column('dead_letter', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('ingestion_jobs', sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ingestion_jobs', sa.Column('chunks_count', sa.Integer(), nullable=True))
    op.create_index('idx_jobs_dead_letter', 'ingestion_jobs', ['dead_letter'])


def downgrade() -> None:
    op.drop_index('idx_jobs_dead_letter', table_name='ingestion_jobs')
    op.drop_column('ingestion_jobs', 'chunks_count')
    op.drop_column('ingestion_jobs', 'next_attempt_at')
    op.drop_column('ingestion_jobs', 'dead_letter')
    op.drop_column('ingestion_jobs', 'sha256_hash')
    op.drop_column('ingestion_jobs', 'mime_type')
    op.drop_column('ingestion_jobs', 'file_size_bytes')
    op.drop_column('ingestion_jobs', 'department_id')
    op.drop_column('ingestion_jobs', 'file_path')
    op.drop_column('ingestion_jobs', 'filename')

    op.drop_index('idx_ext_ident_tenant', table_name='user_external_identities')
    op.drop_index('idx_ext_ident_iss_sub', table_name='user_external_identities')
    op.drop_index('idx_ext_ident_user_id', table_name='user_external_identities')
    op.drop_table('user_external_identities')
