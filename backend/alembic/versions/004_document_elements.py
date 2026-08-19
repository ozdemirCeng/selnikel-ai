"""document elements hierarchical schema

Revision ID: 004_doc_elements
Revises: 003_doc_rev_equip
Create Date: 2026-08-19 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_doc_elements'
down_revision: Union[str, None] = '003_doc_rev_equip'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_elements',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('document_id', sa.String(length=36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('revision_id', sa.String(length=36), sa.ForeignKey('document_revisions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_id', sa.String(length=36), sa.ForeignKey('document_elements.id'), nullable=True),
        sa.Column('element_type', sa.String(length=50), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False, default=1),
        sa.Column('page_start', sa.Integer(), nullable=False, default=1),
        sa.Column('page_end', sa.Integer(), nullable=False, default=1),
        sa.Column('section_path', sa.JSON(), nullable=False, default=[]),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('structured_content', sa.JSON(), nullable=False, default={}),
        sa.Column('bounding_boxes', sa.JSON(), nullable=False, default=[]),
        sa.Column('equipment_ids', sa.JSON(), nullable=False, default=[]),
        sa.Column('standard_references', sa.JSON(), nullable=False, default=[]),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_elements_doc_id', 'document_elements', ['document_id'])
    op.create_index('idx_elements_rev_id', 'document_elements', ['revision_id'])
    op.create_index('idx_elements_type', 'document_elements', ['element_type'])


def downgrade() -> None:
    op.drop_table('document_elements')
