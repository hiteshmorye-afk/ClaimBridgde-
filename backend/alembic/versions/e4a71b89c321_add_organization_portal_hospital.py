"""Add organization and portal to users, and hospital_name to claims

Revision ID: e4a71b89c321
Revises: f8f2306b2de3
Create Date: 2026-10-15 01:46:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4a71b89c321'
down_revision: Union[str, Sequence[str], None] = 'f8f2306b2de3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add organization and portal to users
    op.add_column('users', sa.Column('organization', sa.String(length=150), nullable=True))
    op.add_column('users', sa.Column('portal', sa.String(length=50), server_default='Hospital', nullable=True))

    # 2. Add hospital_name to claims
    op.add_column('claims', sa.Column('hospital_name', sa.String(length=150), nullable=True))


def downgrade() -> None:
    op.drop_column('claims', 'hospital_name')
    op.drop_column('users', 'portal')
    op.drop_column('users', 'organization')
