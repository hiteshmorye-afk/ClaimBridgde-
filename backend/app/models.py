import uuid

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Date,
    Text,
    Numeric,
    ForeignKey,
    Integer,
    Boolean,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    full_name = Column(
        String(150),
        nullable=False,
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
    )

    role = Column(
        String(50),
        nullable=False,
    )

    phone = Column(
        String(20),
        nullable=True,
    )

    account_status = Column(
        String(40),
        nullable=True,
    )

    email_verified_at = Column(
        DateTime,
        nullable=True,
    )

    phone_verified_at = Column(
        DateTime,
        nullable=True,
    )

    organization_verified_at = Column(
        DateTime,
        nullable=True,
    )

    provisioned_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    organization = Column(
        String(150),
        nullable=True,
    )

    portal = Column(
        String(50),
        server_default=text("'Hospital'"),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )

    password_hash = Column(
        String(255),
        nullable=True,
    )

    designation = Column(
        String(100),
        nullable=True,
    )

    employee_id = Column(
        String(50),
        nullable=True,
    )

    last_login_at = Column(
        DateTime,
        nullable=True,
    )

    is_active = Column(
        Boolean,
        server_default=text("true"),
        nullable=False,
        default=True,
    )


class Patient(Base):
    __tablename__ = "patients"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    full_name = Column(
        String(150),
        nullable=False,
    )

    date_of_birth = Column(Date, nullable=True)

    gender = Column(
        String(20),
        nullable=True,
    )

    contact_number = Column(
        String(20),
        nullable=True,
    )

    emergency_contact_name = Column(
        String(100),
        nullable=True,
    )

    emergency_contact_phone = Column(
        String(20),
        nullable=True,
    )

    blood_group = Column(
        String(10),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class Policy(Base):
    __tablename__ = "policies"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    provider_id = Column(
        UUID(as_uuid=True),
        ForeignKey("insurance_providers.id", ondelete="SET NULL"),
        nullable=True,
    )

    policy_number = Column(
        String(100),
        unique=True,
        nullable=False,
    )

    insurance_provider = Column(
        String(150),
        nullable=False,
    )

    policy_type = Column(
        String(100),
        nullable=True,
    )

    coverage_amount = Column(
        Numeric(12, 2),
        nullable=True,
    )

    policy_start_date = Column(
        Date,
        nullable=True,
    )

    policy_end_date = Column(
        Date,
        nullable=True,
    )

    member_id = Column(
        String(100),
        nullable=True,
    )

    policy_holder_name = Column(
        String(150),
        nullable=True,
    )

    relationship = Column(
        String(50),
        nullable=True,
    )

    tpa_name = Column(
        String(150),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class Claim(Base):
    __tablename__ = "claims"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    claim_number = Column(
        String(50),
        unique=True,
        nullable=False,
    )

    patient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )

    policy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("policies.id"),
        nullable=False,
    )

    hospital_name = Column(
        String(150),
        nullable=True,
    )

    admission_date = Column(Date, nullable=True)

    discharge_date = Column(Date, nullable=True)

    claimed_amount = Column(
        Numeric(12, 2),
        nullable=False,
    )

    claim_status = Column(
        String(50),
        server_default=text("'Under Analysis'"),
    )

    current_stage = Column(
        String(100),
        server_default=text("'Claim Created'"),
    )

    readiness_score = Column(
        Numeric(5, 2),
        server_default=text("0"),
    )

    claim_type = Column(
        String(30),
        server_default=text("'reimbursement'"),
        nullable=True,
    )

    preauth_amount = Column(
        Numeric(12, 2),
        nullable=True,
    )

    final_approved_amount = Column(
        Numeric(12, 2),
        nullable=True,
    )

    patient_responsibility = Column(
        Numeric(12, 2),
        nullable=True,
    )

    discharge_readiness_status = Column(
        String(40),
        server_default=text("'Pending Pre-Auth'"),
        nullable=True,
    )

    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )

    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class ClaimDocument(Base):
    __tablename__ = "claim_documents"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    claim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )

    document_type = Column(
        String(100),
        nullable=False,
    )

    file_name = Column(
        String(255),
        nullable=False,
    )

    file_path = Column(
        Text,
        nullable=True,
    )

    processing_status = Column(
        String(50),
        server_default=text("'Pending'"),
    )

    uploaded_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claim_documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    extracted_text = Column(
        Text,
        nullable=True,
    )

    extracted_data = Column(
        JSONB,
        nullable=True,
    )

    ocr_confidence = Column(
        Numeric(5, 2),
        nullable=True,
    )

    extraction_status = Column(
        String(50),
        server_default=text("'Pending'"),
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )

    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class MedicalAnalysis(Base):
    __tablename__ = "medical_analysis"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    claim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claim_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    diagnosis = Column(
        Text,
        nullable=True,
    )

    procedure = Column(
        Text,
        nullable=True,
    )

    analysis_result = Column(
        JSONB,
        nullable=True,
    )

    confidence_score = Column(
        Numeric(5, 2),
        nullable=True,
    )

    risk_score = Column(
        Numeric(5, 2),
        nullable=True,
    )

    processing_status = Column(
        String(50),
        server_default=text("'Pending'"),
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )

    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    claim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claim_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    analysis_type = Column(
        String(100),
        nullable=False,
    )

    model_name = Column(
        String(100),
        nullable=True,
    )

    input_data = Column(
        JSONB,
        nullable=True,
    )

    analysis_result = Column(
        JSONB,
        nullable=True,
    )

    confidence_score = Column(
        Numeric(5, 2),
        nullable=True,
    )

    risk_score = Column(
        Numeric(5, 2),
        nullable=True,
    )

    processing_status = Column(
        String(50),
        server_default=text("'Pending'"),
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class ClaimHistory(Base):
    __tablename__ = "claim_history"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    claim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )

    previous_status = Column(
        String(50),
        nullable=True,
    )

    new_status = Column(
        String(50),
        nullable=False,
    )

    previous_stage = Column(
        String(100),
        nullable=True,
    )

    new_stage = Column(
        String(100),
        nullable=True,
    )

    action = Column(
        String(100),
        nullable=False,
    )

    remarks = Column(
        Text,
        nullable=True,
    )

    performed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class OtpChallenge(Base):
    __tablename__ = "otp_challenges"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    purpose = Column(
        String(40),
        nullable=False,
    )

    recipient_hash = Column(
        String(64),
        nullable=False,
    )

    requester_hash = Column(
        String(64),
        nullable=True,
    )

    code_digest = Column(
        String(64),
        nullable=False,
    )

    attempts = Column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    expires_at = Column(
        DateTime,
        nullable=False,
    )

    consumed_at = Column(
        DateTime,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class ClaimAmendment(Base):
    __tablename__ = "claim_amendments"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    claim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )

    requested_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    requested_changes = Column(
        JSONB,
        nullable=False,
    )

    original_values = Column(
        JSONB,
        nullable=False,
    )

    reason = Column(
        Text,
        nullable=False,
    )

    review_note = Column(
        Text,
        nullable=True,
    )

    status = Column(
        String(30),
        nullable=False,
        server_default=text("'Pending'"),
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )

    reviewed_at = Column(
        DateTime,
        nullable=True,
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    event_type = Column(
        String(100),
        nullable=False,
    )

    actor_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    claim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="SET NULL"),
        nullable=True,
    )

    details = Column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    claim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )

    readiness_score = Column(
        Numeric(5, 2),
        nullable=True,
    )

    verification_status = Column(
        String(50),
        server_default=text("'Pending'"),
    )

    missing_documents = Column(
        JSONB,
        nullable=True,
    )

    mismatches = Column(
        JSONB,
        nullable=True,
    )

    risk_indicators = Column(
        JSONB,
        nullable=True,
    )

    verification_summary = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )

    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )

class InsuranceProvider(Base):
    __tablename__ = "insurance_providers"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    name = Column(
        String(150),
        unique=True,
        nullable=False,
    )

    code = Column(
        String(50),
        unique=True,
        nullable=False,
    )

    provider_type = Column(
        String(50),
        nullable=True,
    )

    official_website = Column(
        String(255),
        nullable=True,
    )

    official_portal_url = Column(
        String(255),
        nullable=True,
    )

    submission_mode = Column(
        String(50),
        nullable=False,
        server_default=text("'manual'"),
    )

    supported_claim_types = Column(
        JSONB,
        nullable=False,
        server_default=text("\'[\"cashless\", \"reimbursement\"]\'::jsonb"),
    )

    required_document_categories = Column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    integration_config = Column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    provider_notes = Column(
        Text,
        nullable=True,
    )

    contact_email = Column(
        String(255),
        nullable=True,
    )

    contact_phone = Column(
        String(50),
        nullable=True,
    )

    portal_url = Column(
        String(255),
        nullable=True,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class PatientConsent(Base):
    __tablename__ = "patient_consents"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    patient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )

    claim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )

    consenter_name = Column(
        String(150),
        nullable=False,
    )

    consenter_relationship = Column(
        String(50),
        nullable=False,
    )

    purpose = Column(
        String(100),
        nullable=False,
    )

    status = Column(
        String(30),
        nullable=False,
        server_default=text("'Given'"),
    )

    consent_text = Column(
        Text,
        nullable=False,
    )

    ip_address = Column(
        String(50),
        nullable=True,
    )

    consent_timestamp = Column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class CashlessPreauthorization(Base):
    __tablename__ = "cashless_preauthorizations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    claim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    room_type = Column(
        String(50),
        nullable=True,
    )

    proposed_treatment = Column(
        Text,
        nullable=True,
    )

    treating_doctor = Column(
        String(150),
        nullable=True,
    )

    doctor_registration_no = Column(
        String(100),
        nullable=True,
    )

    estimated_cost = Column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0.00"),
    )

    cost_breakdown = Column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    status = Column(
        String(40),
        nullable=False,
        server_default=text("'Draft'"),
    )

    submission_mode = Column(
        String(40),
        nullable=True,
    )

    submission_reference = Column(
        String(100),
        nullable=True,
    )

    submitted_at = Column(
        DateTime,
        nullable=True,
    )

    submitted_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    initial_approval_amount = Column(
        Numeric(12, 2),
        nullable=True,
    )

    approval_reference = Column(
        String(100),
        nullable=True,
    )

    approved_at = Column(
        DateTime,
        nullable=True,
    )

    approval_conditions = Column(
        Text,
        nullable=True,
    )

    approval_letter_doc_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claim_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    tpa_query_remarks = Column(
        Text,
        nullable=True,
    )

    hospital_query_response = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )

    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class TreatmentRecord(Base):
    __tablename__ = "treatment_records"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    claim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )

    record_date = Column(
        Date,
        nullable=False,
    )

    clinical_notes = Column(
        Text,
        nullable=False,
    )

    procedures_performed = Column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    updated_diagnosis = Column(
        String(255),
        nullable=True,
    )

    cumulative_expenses = Column(
        Numeric(12, 2),
        nullable=True,
    )

    recorded_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class CashlessFinalAuthorization(Base):
    __tablename__ = "cashless_final_authorizations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    claim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    final_billed_amount = Column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0.00"),
    )

    status = Column(
        String(40),
        nullable=False,
        server_default=text("'Draft'"),
    )

    submission_reference = Column(
        String(100),
        nullable=True,
    )

    submitted_at = Column(
        DateTime,
        nullable=True,
    )

    submitted_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    final_approved_amount = Column(
        Numeric(12, 2),
        nullable=True,
    )

    non_payable_deductions = Column(
        Numeric(12, 2),
        nullable=True,
        server_default=text("0.00"),
    )

    deduction_breakdown = Column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    patient_responsibility_amount = Column(
        Numeric(12, 2),
        nullable=True,
        server_default=text("0.00"),
    )

    settlement_letter_doc_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claim_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    final_approval_reference = Column(
        String(100),
        nullable=True,
    )

    final_approved_at = Column(
        DateTime,
        nullable=True,
    )

    tpa_remarks = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )

    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    name = Column(
        String(150),
        unique=True,
        nullable=False,
        index=True,
    )

    org_type = Column(
        String(50),
        nullable=False,
    )

    registration_identifier = Column(
        String(100),
        nullable=True,
    )

    contact_email = Column(
        String(255),
        nullable=True,
    )

    contact_phone = Column(
        String(50),
        nullable=True,
    )

    is_active = Column(
        Boolean,
        server_default=text("true"),
        nullable=False,
        default=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    email = Column(
        String(255),
        nullable=False,
        index=True,
    )

    role = Column(
        String(50),
        nullable=False,
    )

    organization_name = Column(
        String(150),
        nullable=False,
    )

    token_hash = Column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    invited_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    status = Column(
        String(30),
        server_default=text("'pending'"),
        nullable=False,
        default="pending",
    )

    expires_at = Column(
        DateTime,
        nullable=False,
    )

    accepted_at = Column(
        DateTime,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )
