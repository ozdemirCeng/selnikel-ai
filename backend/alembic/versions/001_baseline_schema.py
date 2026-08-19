"""baseline existing documents chunks and query logs

Revision ID: 001_baseline
Revises: 
Create Date: 2026-08-19 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_baseline'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Documents Table
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False, unique=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False, default='engineering'),
        sa.Column('document_type', sa.String(length=100), nullable=False, default='technical_specification'),
        sa.Column('language', sa.String(length=10), nullable=False, default='tr'),
        sa.Column('total_pages', sa.Integer(), nullable=False, default=1),
        sa.Column('total_chunks', sa.Integer(), nullable=False, default=0),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('metadata', sa.JSON(), nullable=False, default={}),
        sa.Column('status', sa.String(length=50), nullable=False, default='ready'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_documents_file_hash', 'documents', ['file_hash'])
    op.create_index('idx_documents_department', 'documents', ['department'])

    # 2. Document Chunks Table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('document_id', sa.String(length=36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False, default=1),
        sa.Column('section', sa.String(length=255), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False, default=0),
        sa.Column('is_table', sa.Boolean(), nullable=False, default=False),
        sa.Column('structured_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_chunks_document_id', 'document_chunks', ['document_id'])

    # 3. Query Logs Table
    op.create_table(
        'query_logs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('top_k', sa.Integer(), nullable=False, default=5),
        sa.Column('department_filter', sa.String(length=100), nullable=True),
        sa.Column('retrieved_chunks_count', sa.Integer(), nullable=False, default=0),
        sa.Column('retrieval_latency_ms', sa.Float(), nullable=False, default=0.0),
        sa.Column('generation_latency_ms', sa.Float(), nullable=False, default=0.0),
        sa.Column('total_latency_ms', sa.Float(), nullable=False, default=0.0),
        sa.Column('citations_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('query_logs')
    op.drop_table('document_chunks')
    op.drop_table('documents')
