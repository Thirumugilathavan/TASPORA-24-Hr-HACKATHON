"""add_coimbatore_facility_schema_and_booking_fields

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-11-13 08:00:00.000000

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
    # 1. Add new columns to facilities table
    with op.batch_alter_table("facilities", schema=None) as batch_op:
        batch_op.add_column(sa.Column("alternate_names", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("facility_category", sa.String(length=100), nullable=True, server_default="HOSPITAL"))
        batch_op.add_column(sa.Column("health_unit_district", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("block", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("locality", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("pincode", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("geographic_verification_status", sa.String(length=50), nullable=True, server_default="VERIFIED_COORDINATES"))
        batch_op.add_column(sa.Column("official_phone", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("official_email", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("official_website", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("emergency_contact", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("opd_available", sa.Boolean(), nullable=True, server_default=sa.true()))
        batch_op.add_column(sa.Column("opening_hours", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("emergency_services", sa.Boolean(), nullable=True, server_default=sa.false()))
        batch_op.add_column(sa.Column("ambulance_available", sa.Boolean(), nullable=True, server_default=sa.false()))
        batch_op.add_column(sa.Column("maternity_services", sa.Boolean(), nullable=True, server_default=sa.false()))
        batch_op.add_column(sa.Column("pharmacy_available", sa.Boolean(), nullable=True, server_default=sa.true()))
        batch_op.add_column(sa.Column("laboratory_services", sa.Boolean(), nullable=True, server_default=sa.true()))
        batch_op.add_column(sa.Column("imaging_services", sa.Boolean(), nullable=True, server_default=sa.false()))
        batch_op.add_column(sa.Column("specialties", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("appointment_booking_method", sa.String(length=50), nullable=True, server_default="WALK_IN_ONLY"))
        batch_op.add_column(sa.Column("online_booking_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("official_source_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("source_type", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("date_collected", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("last_verified_date", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("verification_status", sa.String(length=50), nullable=True, server_default="VERIFIED_OFFICIAL"))
        batch_op.add_column(sa.Column("data_completeness_score", sa.Float(), nullable=True, server_default="0.0"))

        batch_op.create_index(batch_op.f("ix_facilities_facility_category"), ["facility_category"], unique=False)
        batch_op.create_index(batch_op.f("ix_facilities_block"), ["block"], unique=False)
        batch_op.create_index(batch_op.f("ix_facilities_locality"), ["locality"], unique=False)
        batch_op.create_index(batch_op.f("ix_facilities_verification_status"), ["verification_status"], unique=False)
        batch_op.create_index(batch_op.f("ix_facilities_appointment_booking_method"), ["appointment_booking_method"], unique=False)
        batch_op.create_index("ix_facilities_district_block", ["district", "block"], unique=False)
        batch_op.create_index("ix_facilities_services", ["emergency_services", "maternity_services"], unique=False)

    # 2. Create facility_specialties table
    op.create_table(
        "facility_specialties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("specialty_name", sa.String(length=100), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_facility_specialties_facility_id"), "facility_specialties", ["facility_id"], unique=False)
    op.create_index(op.f("ix_facility_specialties_specialty_name"), "facility_specialties", ["specialty_name"], unique=False)

    # 3. Create facility_sources table
    op.create_table(
        "facility_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("date_collected", sa.String(length=50), nullable=False),
        sa.Column("verification_notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_facility_sources_facility_id"), "facility_sources", ["facility_id"], unique=False)

    # 4. Create facility_verification_history table
    op.create_table(
        "facility_verification_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("verification_status", sa.String(length=50), nullable=False),
        sa.Column("verified_by", sa.String(length=100), nullable=False),
        sa.Column("verification_date", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_facility_verification_history_facility_id"), "facility_verification_history", ["facility_id"], unique=False)

    # 5. Create facility_appointment_configurations table
    op.create_table(
        "facility_appointment_configurations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("booking_method", sa.String(length=50), nullable=False),
        sa.Column("booking_url", sa.String(length=500), nullable=True),
        sa.Column("booking_phone", sa.String(length=50), nullable=True),
        sa.Column("instructions_en", sa.String(length=500), nullable=True),
        sa.Column("instructions_ta", sa.String(length=500), nullable=True),
        sa.Column("requires_registration", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("lead_time_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("facility_id"),
    )
    op.create_index(op.f("ix_facility_appointment_configurations_facility_id"), "facility_appointment_configurations", ["facility_id"], unique=True)
    op.create_index(op.f("ix_facility_appointment_configurations_booking_method"), "facility_appointment_configurations", ["booking_method"], unique=False)


def downgrade() -> None:
    op.drop_table("facility_appointment_configurations")
    op.drop_table("facility_verification_history")
    op.drop_table("facility_sources")
    op.drop_table("facility_specialties")

    with op.batch_alter_table("facilities", schema=None) as batch_op:
        batch_op.drop_index("ix_facilities_services")
        batch_op.drop_index("ix_facilities_district_block")
        batch_op.drop_index(batch_op.f("ix_facilities_appointment_booking_method"))
        batch_op.drop_index(batch_op.f("ix_facilities_verification_status"))
        batch_op.drop_index(batch_op.f("ix_facilities_locality"))
        batch_op.drop_index(batch_op.f("ix_facilities_block"))
        batch_op.drop_index(batch_op.f("ix_facilities_facility_category"))

        batch_op.drop_column("data_completeness_score")
        batch_op.drop_column("verification_status")
        batch_op.drop_column("last_verified_date")
        batch_op.drop_column("date_collected")
        batch_op.drop_column("source_type")
        batch_op.drop_column("official_source_url")
        batch_op.drop_column("online_booking_url")
        batch_op.drop_column("appointment_booking_method")
        batch_op.drop_column("specialties")
        batch_op.drop_column("imaging_services")
        batch_op.drop_column("laboratory_services")
        batch_op.drop_column("pharmacy_available")
        batch_op.drop_column("maternity_services")
        batch_op.drop_column("ambulance_available")
        batch_op.drop_column("emergency_services")
        batch_op.drop_column("opening_hours")
        batch_op.drop_column("opd_available")
        batch_op.drop_column("emergency_contact")
        batch_op.drop_column("official_website")
        batch_op.drop_column("official_email")
        batch_op.drop_column("official_phone")
        batch_op.drop_column("geographic_verification_status")
        batch_op.drop_column("pincode")
        batch_op.drop_column("locality")
        batch_op.drop_column("block")
        batch_op.drop_column("health_unit_district")
        batch_op.drop_column("facility_category")
        batch_op.drop_column("alternate_names")
