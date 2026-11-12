"""expand_facilities_for_nic_dataset

Revision ID: b8c9d0e1f2a3
Revises: e7f1a23b4c5d
Create Date: 2026-11-12 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'e7f1a23b4c5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("facilities", schema=None) as batch_op:
        batch_op.add_column(sa.Column("district", sa.String(length=255), nullable=True, server_default=""))
        batch_op.add_column(sa.Column("state", sa.String(length=100), nullable=True, server_default=""))
        batch_op.add_column(sa.Column("subdistrict", sa.String(length=255), nullable=True, server_default=""))
        batch_op.add_column(sa.Column("ownership", sa.String(length=100), nullable=True, server_default="Government"))
        batch_op.add_column(sa.Column("source", sa.String(length=50), nullable=True, server_default="nic"))
        batch_op.add_column(sa.Column("source_id", sa.String(length=100), nullable=True))
        batch_op.alter_column("village_id", existing_type=sa.Uuid(), nullable=True)
        batch_op.create_index(batch_op.f("ix_facilities_district"), ["district"], unique=False)
        batch_op.create_index(batch_op.f("ix_facilities_state"), ["state"], unique=False)
        batch_op.create_index(batch_op.f("ix_facilities_source_id"), ["source_id"], unique=False)
        batch_op.create_index("ix_facilities_coords", ["latitude", "longitude"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("facilities", schema=None) as batch_op:
        batch_op.drop_index("ix_facilities_coords")
        batch_op.drop_index(batch_op.f("ix_facilities_source_id"))
        batch_op.drop_index(batch_op.f("ix_facilities_state"))
        batch_op.drop_index(batch_op.f("ix_facilities_district"))
        batch_op.drop_column("source_id")
        batch_op.drop_column("source")
        batch_op.drop_column("ownership")
        batch_op.drop_column("subdistrict")
        batch_op.drop_column("state")
        batch_op.drop_column("district")
