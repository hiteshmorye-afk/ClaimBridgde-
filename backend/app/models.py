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