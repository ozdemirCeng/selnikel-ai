"""documents revisions and equipment slice

Revision ID: 003_doc_rev_equip
Revises: 002_identity_org
Create Date: 2026-08-19 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_doc_rev_equip'
down_revision: Union[str, None] = '002_identity_org'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Equipment Table
    op.create_table(
        'equipment',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('equipment_type', sa.String(length=50), nullable=False),
        sa.Column('model_code', sa.String(length=100), unique=True, nullable=False),
        sa.Column('serial_number', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('department_id', sa.String(length=36), nullable=True),
        sa.Column('attributes', sa.JSON(), nullable=False, default={}),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_equipment_model_code', 'equipment', ['model_code'])
    op.create_index('idx_equipment_type', 'equipment', ['equipment_type'])

    # 2. Document Equipment (Many-to-Many)
    op.create_table(
        'document_equipment',
        sa.Column('document_id', sa.String(length=36), sa.ForeignKey('documents.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('equipment_id', sa.String(length=36), sa.ForeignKey('equipment.id', ondelete='CASCADE'), primary_key=True),
    )

    # 3. Document Revisions Table
    op.create_table(
        'document_revisions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('document_id', sa.String(length=36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('revision_code', sa.String(length=50), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False, default=1),
        sa.Column('effective_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('supersedes_revision_id', sa.String(length=36), sa.ForeignKey('document_revisions.id'), nullable=True),
        sa.Column('approval_status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('approved_by', sa.String(length=36), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('parser_name', sa.String(length=100), nullable=False, server_default='docling'),
        sa.Column('parser_version', sa.String(length=50), nullable=False, server_default='2.120.3'),
        sa.Column('source_sha256', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_revisions_doc_id', 'document_revisions', ['document_id'])
    op.create_index('idx_revisions_status', 'document_revisions', ['approval_status'])

    # 4. Document ACL Table
    op.create_table(
        'document_acl',
        sa.Column('document_id', sa.String(length=36), sa.ForeignKey('documents.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('department_id', sa.String(length=36), primary_key=True),
        sa.Column('permission', sa.String(length=50), nullable=False, server_default='read'),
    )


def downgrade() -> None:
    op.drop_table('document_acl')
    op.drop_table('document_revisions')
    op.drop_table('document_equipment')
    op.drop_table('equipment')
