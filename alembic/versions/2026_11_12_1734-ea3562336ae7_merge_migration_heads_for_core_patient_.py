"""merge migration heads for core, patient, and facility modules

Revision ID: ea3562336ae7
Revises: b7f407bac8b8, f974ef109542, ca882bcbb941
Create Date: 2026-11-12 17:34:52.371848

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ea3562336ae7'
down_revision: Union[str, None] = ('b7f407bac8b8', 'f974ef109542', 'ca882bcbb941')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
