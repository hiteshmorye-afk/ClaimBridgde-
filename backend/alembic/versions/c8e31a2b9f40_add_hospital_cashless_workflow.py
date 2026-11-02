"""Add hospital cashless insurance claim workflow tables and fields.

Revision ID: c8e31a2b9f40
Revises: b7d2f4c9a610
Create Date: 2026-11-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c8e31a2b9f40"
down_revision: Union[str, Sequence[str], None] = "b7d2f4c9a610"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Nullable columns on existing tables
    # Claims
    op.add_column("claims", sa.Column("claim_type", sa.String(length=30), server_default=sa.text("'reimbursement'"), nullable=True))
    op.add_column("claims", sa.Column("preauth_amount", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("claims", sa.Column("final_approved_amount", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("claims", sa.Column("patient_responsibility", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("claims", sa.Column("discharge_readiness_status", sa.String(length=40), server_default=sa.text("'Pending Pre-Auth'"), nullable=True))

    # Policies
    op.add_column("policies", sa.Column("member_id", sa.String(length=100), nullable=True))
    op.add_column("policies", sa.Column("policy_holder_name", sa.String(length=150), nullable=True))
    op.add_column("policies", sa.Column("relationship", sa.String(length=50), nullable=True))
    op.add_column("policies", sa.Column("tpa_name", sa.String(length=150), nullable=True))

    # Patients
    op.add_column("patients", sa.Column("emergency_contact_name", sa.String(length=100), nullable=True))
    op.add_column("patients", sa.Column("emergency_contact_phone", sa.String(length=20), nullable=True))
    op.add_column("patients", sa.Column("blood_group", sa.String(length=10), nullable=True))

    # 2. Insurance Providers Table
    op.create_table(
        "insurance_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("portal_url", sa.String(length=255), nullable=True),
        sa.Column("supported_claim_types", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[\"cashless\", \"reimbursement\"]'::jsonb"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_insurance_providers_is_active", "insurance_providers", ["is_active"])

    # 3. Patient Consents Table
    op.create_table(
        "patient_consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consenter_name", sa.String(length=150), nullable=False),
        sa.Column("consenter_relationship", sa.String(length=50), nullable=False),
        sa.Column("purpose", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'Given'"), nullable=False),
        sa.Column("consent_text", sa.Text(), nullable=False),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("consent_timestamp", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_consents_claim_id", "patient_consents", ["claim_id"])

    # 4. Cashless Preauthorizations Table
    op.create_table(
        "cashless_preauthorizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_type", sa.String(length=50), nullable=True),
        sa.Column("proposed_treatment", sa.Text(), nullable=True),
        sa.Column("treating_doctor", sa.String(length=150), nullable=True),
        sa.Column("doctor_registration_no", sa.String(length=100), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=12, scale=2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("cost_breakdown", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.String(length=40), server_default=sa.text("'Draft'"), nullable=False),
        sa.Column("submission_mode", sa.String(length=40), nullable=True),
        sa.Column("submission_reference", sa.String(length=100), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("initial_approval_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("approval_reference", sa.String(length=100), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approval_conditions", sa.Text(), nullable=True),
        sa.Column("approval_letter_doc_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tpa_query_remarks", sa.Text(), nullable=True),
        sa.Column("hospital_query_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approval_letter_doc_id"], ["claim_documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_id"),
    )
    op.create_index("ix_cashless_preauth_claim", "cashless_preauthorizations", ["claim_id"])
    op.create_index("ix_cashless_preauth_status", "cashless_preauthorizations", ["status"])

    # 5. Treatment Records Table
    op.create_table(
        "treatment_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column("clinical_notes", sa.Text(), nullable=False),
        sa.Column("procedures_performed", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("updated_diagnosis", sa.String(length=255), nullable=True),
        sa.Column("cumulative_expenses", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_treatment_records_claim_date", "treatment_records", ["claim_id", "record_date"])

    # 6. Cashless Final Authorizations Table
    op.create_table(
        "cashless_final_authorizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("final_billed_amount", sa.Numeric(precision=12, scale=2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("status", sa.String(length=40), server_default=sa.text("'Draft'"), nullable=False),
        sa.Column("submission_reference", sa.String(length=100), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("final_approved_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("non_payable_deductions", sa.Numeric(precision=12, scale=2), server_default=sa.text("0.00"), nullable=True),
        sa.Column("deduction_breakdown", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("patient_responsibility_amount", sa.Numeric(precision=12, scale=2), server_default=sa.text("0.00"), nullable=True),
        sa.Column("settlement_letter_doc_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("final_approval_reference", sa.String(length=100), nullable=True),
        sa.Column("final_approved_at", sa.DateTime(), nullable=True),
        sa.Column("tpa_remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_letter_doc_id"], ["claim_documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_id"),
    )
    op.create_index("ix_cashless_final_auth_claim", "cashless_final_authorizations", ["claim_id"])


def downgrade() -> None:
    op.drop_index("ix_cashless_final_auth_claim", table_name="cashless_final_authorizations")
    op.drop_table("cashless_final_authorizations")

    op.drop_index("ix_treatment_records_claim_date", table_name="treatment_records")
    op.drop_table("treatment_records")

    op.drop_index("ix_cashless_preauth_status", table_name="cashless_preauthorizations")
    op.drop_index("ix_cashless_preauth_claim", table_name="cashless_preauthorizations")
    op.drop_table("cashless_preauthorizations")

    op.drop_index("ix_patient_consents_claim_id", table_name="patient_consents")
    op.drop_table("patient_consents")

    op.drop_index("ix_insurance_providers_is_active", table_name="insurance_providers")
    op.drop_table("insurance_providers")

    op.drop_column("patients", "blood_group")
    op.drop_column("patients", "emergency_contact_phone")
    op.drop_column("patients", "emergency_contact_name")

    op.drop_column("policies", "tpa_name")
    op.drop_column("policies", "relationship")
    op.drop_column("policies", "policy_holder_name")
    op.drop_column("policies", "member_id")

    op.drop_column("claims", "discharge_readiness_status")
    op.drop_column("claims", "patient_responsibility")
    op.drop_column("claims", "final_approved_amount")
    op.drop_column("claims", "preauth_amount")
    op.drop_column("claims", "claim_type")
