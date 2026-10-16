"""Add verified accounts, OTP challenges, amendments, and audit events.

Revision ID: b7d2f4c9a610
Revises: e4a71b89c321
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b7d2f4c9a610"
down_revision: Union[str, Sequence[str], None] = "e4a71b89c321"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("account_status", sa.String(length=40), nullable=True))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("phone_verified_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("organization_verified_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("provisioned_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_users_provisioned_by_users",
        "users",
        "users",
        ["provisioned_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "otp_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("recipient_hash", sa.String(length=64), nullable=False),
        sa.Column("requester_hash", sa.String(length=64), nullable=True),
        sa.Column("code_digest", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_otp_challenges_recipient_created",
        "otp_challenges",
        ["recipient_hash", "created_at"],
    )
    op.create_index(
        "ix_otp_challenges_user_created",
        "otp_challenges",
        ["user_id", "created_at"],
    )

    op.create_table(
        "claim_amendments",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("original_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'Pending'"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_claim_amendments_claim_status", "claim_amendments", ["claim_id", "status"])

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_claim_created", "audit_events", ["claim_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_claim_created", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_claim_amendments_claim_status", table_name="claim_amendments")
    op.drop_table("claim_amendments")
    op.drop_index("ix_otp_challenges_user_created", table_name="otp_challenges")
    op.drop_index("ix_otp_challenges_recipient_created", table_name="otp_challenges")
    op.drop_table("otp_challenges")
    op.drop_constraint("fk_users_provisioned_by_users", "users", type_="foreignkey")
    op.drop_column("users", "provisioned_by")
    op.drop_column("users", "organization_verified_at")
    op.drop_column("users", "phone_verified_at")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "account_status")
    op.drop_column("users", "phone")
