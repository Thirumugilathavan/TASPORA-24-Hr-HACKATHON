"""add_subdistrict_and_indexes_to_villages

Revision ID: e7f1a23b4c5d
Revises: a4377b10ad92
Create Date: 2026-11-12 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f1a23b4c5d'
down_revision: Union[str, None] = 'a4377b10ad92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("villages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("subdistrict", sa.String(length=255), nullable=True, server_default=""))
        batch_op.create_index(batch_op.f("ix_villages_subdistrict"), ["subdistrict"], unique=False)
        batch_op.create_index(batch_op.f("ix_villages_state"), ["state"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("villages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_villages_state"))
        batch_op.drop_index(batch_op.f("ix_villages_subdistrict"))
        batch_op.drop_column("subdistrict")
