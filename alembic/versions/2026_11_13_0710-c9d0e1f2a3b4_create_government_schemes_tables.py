"""create_government_schemes_tables

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-11-13 07:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create government_schemes table
    op.create_table(
        'government_schemes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('slug', sa.String(length=120), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('name_ta', sa.String(length=300), nullable=False),
        sa.Column('short_description', sa.Text(), nullable=False),
        sa.Column('short_description_ta', sa.Text(), nullable=False),
        sa.Column('detailed_description', sa.Text(), nullable=False),
        sa.Column('detailed_description_ta', sa.Text(), nullable=False),
        sa.Column('department', sa.String(length=255), nullable=False),
        sa.Column('department_ta', sa.String(length=255), nullable=False),
        sa.Column('level', sa.String(length=50), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('districts', sa.JSON(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('target_beneficiaries', sa.JSON(), nullable=False),
        sa.Column('target_beneficiaries_ta', sa.JSON(), nullable=False),
        sa.Column('benefit_type', sa.String(length=100), nullable=False),
        sa.Column('benefit_amount_desc', sa.String(length=255), nullable=False),
        sa.Column('benefit_amount_desc_ta', sa.String(length=255), nullable=False),
        sa.Column('benefit_frequency', sa.String(length=100), nullable=False),
        sa.Column('eligibility_rules', sa.JSON(), nullable=False),
        sa.Column('required_documents', sa.JSON(), nullable=False),
        sa.Column('application_mode', sa.String(length=100), nullable=False),
        sa.Column('application_process', sa.Text(), nullable=False),
        sa.Column('application_process_ta', sa.Text(), nullable=False),
        sa.Column('official_portal_url', sa.String(length=500), nullable=False),
        sa.Column('official_source_url', sa.String(length=500), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('application_status', sa.String(length=50), nullable=False),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verification_status', sa.String(length=50), nullable=False),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_government_schemes_slug', 'government_schemes', ['slug'], unique=True)
    op.create_index('ix_government_schemes_name', 'government_schemes', ['name'], unique=False)
    op.create_index('ix_government_schemes_category', 'government_schemes', ['category'], unique=False)
    op.create_index('ix_government_schemes_level', 'government_schemes', ['level'], unique=False)
    op.create_index('ix_government_schemes_state', 'government_schemes', ['state'], unique=False)
    op.create_index('ix_government_schemes_is_active', 'government_schemes', ['is_active'], unique=False)

    # 2. Create user_scheme_profiles table
    op.create_table(
        'user_scheme_profiles',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('consent_given', sa.Boolean(), nullable=False),
        sa.Column('consent_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('step_progress', sa.Integer(), nullable=False),
        sa.Column('profile_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_scheme_profiles_user_id', 'user_scheme_profiles', ['user_id'], unique=True)

    # 3. Create saved_user_schemes table
    op.create_table(
        'saved_user_schemes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('scheme_id', sa.Uuid(), nullable=False),
        sa.Column('saved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scheme_id'], ['government_schemes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'scheme_id', name='uq_user_saved_scheme'),
    )
    op.create_index('ix_saved_schemes_user_id', 'saved_user_schemes', ['user_id'], unique=False)

    # 4. Create scheme_audit_logs table
    op.create_table(
        'scheme_audit_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('scheme_id', sa.Uuid(), nullable=False),
        sa.Column('admin_user_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('changes_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['scheme_id'], ['government_schemes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_scheme_audit_logs_scheme_id', 'scheme_audit_logs', ['scheme_id'], unique=False)


def downgrade() -> None:
    op.drop_table('scheme_audit_logs')
    op.drop_table('saved_user_schemes')
    op.drop_table('user_scheme_profiles')
    op.drop_table('government_schemes')
