"""baseline existing database schema

Revision ID: 130d359d91dc
Revises: d76cd301cb33
Create Date: 2026-08-20 21:43:45.020944

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '130d359d91dc'
down_revision: Union[str, Sequence[str], None] = 'd76cd301cb33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
