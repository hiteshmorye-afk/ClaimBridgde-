"""Extend insurance provider registry with official portal metadata and claim linkage.

Revision ID: fd8d27c5f31e
Revises: d9f42b3a1e50
Create Date: 2026-11-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "fd8d27c5f31e"
down_revision: Union[str, Sequence[str], None] = "d9f42b3a1e50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("policies", sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_policies_provider_id_insurance_providers",
        "policies",
        "insurance_providers",
        ["provider_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("insurance_providers", sa.Column("provider_type", sa.String(length=50), nullable=True))
    op.add_column("insurance_providers", sa.Column("official_website", sa.String(length=255), nullable=True))
    op.add_column("insurance_providers", sa.Column("official_portal_url", sa.String(length=255), nullable=True))
    op.add_column("insurance_providers", sa.Column("submission_mode", sa.String(length=50), server_default=sa.text("'manual'"), nullable=False))
    op.add_column("insurance_providers", sa.Column("required_document_categories", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.add_column("insurance_providers", sa.Column("integration_config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.add_column("insurance_providers", sa.Column("provider_notes", sa.Text(), nullable=True))

    op.execute(
        "UPDATE insurance_providers SET provider_type = 'Insurer' WHERE provider_type IS NULL"
    )
    op.execute(
        "UPDATE insurance_providers SET submission_mode = 'manual' WHERE submission_mode IS NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_policies_provider_id_insurance_providers", "policies", type_="foreignkey")
    op.drop_column("policies", "provider_id")

    for column_name in [
        "provider_notes",
        "integration_config",
        "required_document_categories",
        "submission_mode",
        "official_portal_url",
        "official_website",
        "provider_type",
    ]:
        op.drop_column("insurance_providers", column_name)
