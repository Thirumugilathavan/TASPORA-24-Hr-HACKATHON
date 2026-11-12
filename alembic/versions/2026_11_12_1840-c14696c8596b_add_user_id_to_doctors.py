"""add_user_id_to_doctors

Revision ID: c14696c8596b
Revises: ea3562336ae7
Create Date: 2026-11-12 18:40:04.351497

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c14696c8596b'
down_revision: Union[str, None] = 'ea3562336ae7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("doctors", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_doctors_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint("uq_doctors_user_id", ["user_id"])
        batch_op.create_index(batch_op.f("ix_doctors_user_id"), ["user_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("doctors", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_doctors_user_id"))
        batch_op.drop_constraint("uq_doctors_user_id", type_="unique")
        batch_op.drop_constraint("fk_doctors_user_id_users", type_="foreignkey")
        batch_op.drop_column("user_id")
