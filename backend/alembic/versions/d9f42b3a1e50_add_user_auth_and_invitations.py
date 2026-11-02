"""Add production user authentication, organizations, and invitations tables.

Revision ID: d9f42b3a1e50
Revises: c8e31a2b9f40
Create Date: 2026-11-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d9f42b3a1e50"
down_revision: Union[str, Sequence[str], None] = "c8e31a2b9f40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add columns to users table
    op.add_column("users", sa.Column("designation", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("employee_id", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))

    # 2. Create organizations table
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("org_type", sa.String(length=50), nullable=False),
        sa.Column("registration_identifier", sa.String(length=100), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_organizations_name"),
    )
    op.create_index(op.f("ix_organizations_name"), "organizations", ["name"], unique=True)

    # 3. Create organization_invitations table
    op.create_table(
        "organization_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("organization_name", sa.String(length=150), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_organization_invitations_token_hash"),
    )
    op.create_index(op.f("ix_organization_invitations_email"), "organization_invitations", ["email"], unique=False)
    op.create_index(op.f("ix_organization_invitations_token_hash"), "organization_invitations", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_organization_invitations_token_hash"), table_name="organization_invitations")
    op.drop_index(op.f("ix_organization_invitations_email"), table_name="organization_invitations")
    op.drop_table("organization_invitations")

    op.drop_index(op.f("ix_organizations_name"), table_name="organizations")
    op.drop_table("organizations")

    op.drop_column("users", "is_active")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "employee_id")
    op.drop_column("users", "designation")
