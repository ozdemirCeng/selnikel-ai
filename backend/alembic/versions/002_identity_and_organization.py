"""identity and organization core slice

Revision ID: 002_identity_org
Revises: 001_baseline
Create Date: 2026-08-19 13:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_identity_org'
down_revision: Union[str, None] = '001_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Permissions
    op.create_table(
        'permissions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('code', sa.String(length=100), unique=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_permissions_code', 'permissions', ['code'])

    # 2. Roles
    op.create_table(
        'roles',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('code', sa.String(length=50), unique=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_roles_code', 'roles', ['code'])

    # 3. Role Permissions (Many-to-Many)
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.String(length=36), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('permission_id', sa.String(length=36), sa.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    )

    # 4. Departments
    op.create_table(
        'departments',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('code', sa.String(length=50), unique=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_departments_code', 'departments', ['code'])

    # 5. Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('email', sa.String(length=255), unique=True, nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_users_email', 'users', ['email'])

    # 6. User Roles (Many-to-Many)
    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role_id', sa.String(length=36), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    )

    # 7. Department Memberships (Many-to-Many)
    op.create_table(
        'department_memberships',
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('department_id', sa.String(length=36), sa.ForeignKey('departments.id', ondelete='CASCADE'), primary_key=True),
    )

    # 8. Audit Events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('actor_id', sa.String(length=36), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=36), nullable=True),
        sa.Column('request_id', sa.String(length=36), nullable=False),
        sa.Column('ip_hash', sa.String(length=64), nullable=True),
        sa.Column('result', sa.String(length=50), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_audit_created_at', 'audit_events', ['created_at'])
    op.create_index('idx_audit_actor_id', 'audit_events', ['actor_id'])
    op.create_index('idx_audit_action', 'audit_events', ['action'])


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('department_memberships')
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('departments')
    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')
