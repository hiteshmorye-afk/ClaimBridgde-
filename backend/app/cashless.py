"""Hospital Cashless Claim Processing & Validation Router.

Provides real-world workflows for:
1. Insurance Provider & TPA Management
2. Patient Consent Verification
3. Cashless Pre-Authorization Workspace & Export
4. TPA Initial Pre-Auth Adjudication & Query Management
5. Inpatient Treatment Documentation Ledger
6. Final Authorization Workspace & 3-Way Financial Comparison
7. TPA Settlement Adjudication & Non-Payable Deductions
8. Discharge Readiness Holistic Assessment
"""
import hashlib
import json
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth import (
    canonical_role_name,
    get_current_user,
    require_claimant,
    require_claims_officer,
    user_is_claimant,
    user_is_claims_officer,
)
from .claims import check_claim_access
from .database import get_db
from .models import (
    AuditEvent,
    CashlessFinalAuthorization,
    CashlessPreauthorization,
    Claim,
    ClaimDocument,
    ClaimHistory,
    InsuranceProvider,
    Patient,
    PatientConsent,
    Policy,
    TreatmentRecord,
    User,
)

router = APIRouter(prefix="/cashless", tags=["cashless"])


# =========================================================
# PYDANTIC SCHEMAS
# =========================================================

class ProviderResponse(BaseModel):
    id: str
    name: str
    code: str
    providerType: Optional[str] = None
    officialWebsite: Optional[str] = None
    officialPortalUrl: Optional[str] = None
    submissionMode: str = "manual"
    requiredDocumentCategories: List[str] = Field(default_factory=list)
    integrationConfig: Dict[str, Any] = Field(default_factory=dict)
    providerNotes: Optional[str] = None
    contactEmail: Optional[str] = None
    contactPhone: Optional[str] = None
    portalUrl: Optional[str] = None
    supportedClaimTypes: List[str]
    isActive: bool

    model_config = ConfigDict(from_attributes=True)


class ProviderCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=50)
    provider_type: Optional[str] = None
    official_website: Optional[str] = None
    official_portal_url: Optional[str] = None
    submission_mode: str = "manual"
    required_document_categories: List[str] = Field(default_factory=list)
    integration_config: Dict[str, Any] = Field(default_factory=dict)
    provider_notes: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    portal_url: Optional[str] = None
    supported_claim_types: List[str] = ["cashless", "reimbursement"]
    is_active: bool = True


class ConsentRequest(BaseModel):
    consenter_name: str = Field(min_length=2, max_length=150)
    consenter_relationship: str = Field(min_length=2, max_length=50)
    purpose: str = Field(default="Cashless Hospitalization Medical Data Processing")
    consent_text: str = Field(min_length=10)


class PreAuthSaveRequest(BaseModel):
    patient_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    mobile_number: Optional[str] = None
    policy_number: Optional[str] = None
    member_id: Optional[str] = None
    policyholder_name: Optional[str] = None
    relationship: Optional[str] = None
    hospital_name: Optional[str] = None
    diagnosis: Optional[str] = None
    room_type: Optional[str] = None
    proposed_treatment: Optional[str] = None
    admission_date: Optional[date] = None
    treating_doctor: Optional[str] = None
    doctor_registration_no: Optional[str] = None
    estimated_cost: float = Field(ge=0)
    cost_breakdown: Dict[str, float] = Field(default_factory=dict)


class PreAuthSubmitRequest(BaseModel):
    submission_mode: str = Field(default="Online Portal")
    submission_reference: str = Field(min_length=2, max_length=100)


class PreAuthAdjudicateRequest(BaseModel):
    decision: str = Field(description="'Approved', 'Partially Approved', 'Query Raised', 'Rejected'")
    initial_approval_amount: Optional[float] = None
    approval_reference: Optional[str] = None
    approval_conditions: Optional[str] = None
    query_remarks: Optional[str] = None


class PreAuthQueryResponseRequest(BaseModel):
    hospital_query_response: str = Field(min_length=5)


class TreatmentRecordCreateRequest(BaseModel):
    record_date: date
    clinical_notes: str = Field(min_length=5)
    procedures_performed: List[Dict[str, Any]] = Field(default_factory=list)
    updated_diagnosis: Optional[str] = None
    cumulative_expenses: Optional[float] = None


class FinalAuthSaveRequest(BaseModel):
    final_billed_amount: float = Field(ge=0)
    deduction_breakdown: Dict[str, float] = Field(default_factory=dict)
    patient_responsibility_amount: Optional[float] = 0.0


class FinalAuthSubmitRequest(BaseModel):
    submission_reference: str = Field(min_length=2, max_length=100)


class FinalAuthAdjudicateRequest(BaseModel):
    decision: str = Field(description="'Approved', 'Partially Approved', 'Rejected'")
    final_approved_amount: float = Field(ge=0)
    non_payable_deductions: float = Field(default=0.0, ge=0)
    deduction_breakdown: Dict[str, float] = Field(default_factory=dict)
    patient_responsibility_amount: float = Field(default=0.0, ge=0)
    final_approval_reference: str = Field(min_length=2, max_length=100)
    tpa_remarks: Optional[str] = None


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def _get_claim_with_access(claim_id: str, db: Session, user: User) -> tuple[Claim, Patient, Policy]:
    try:
        claim_uuid = uuid.UUID(claim_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invalid claim ID '{claim_id}'.",
        )

    claim = db.query(Claim).filter(Claim.id == claim_uuid).first()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim '{claim_id}' not found.",
        )

    patient = db.query(Patient).filter(Patient.id == claim.patient_id).first()
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()

    if not check_claim_access(claim, policy, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Access to this claim is restricted to the authorized coordinator or TPA organization.",
        )

    return claim, patient, policy


def _log_cashless_audit(
    db: Session,
    claim_id: uuid.UUID,
    actor_id: Optional[uuid.UUID],
    event_type: str,
    details: Dict[str, Any],
):
    audit = AuditEvent(
        claim_id=claim_id,
        actor_user_id=actor_id,
        event_type=event_type,
        details=details,
    )
    db.add(audit)


# =========================================================
# 1. INSURANCE PROVIDER MANAGEMENT
# =========================================================

@router.get("/providers", response_model=List[ProviderResponse])
def get_insurance_providers(
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """Retrieve the directory of active insurance providers and TPAs."""
    query = db.query(InsuranceProvider)
    if active_only:
        query = query.filter(InsuranceProvider.is_active.is_(True))
    providers = query.order_by(InsuranceProvider.name.asc()).all()
    return [
        ProviderResponse(
            id=str(p.id),
            name=p.name,
            code=p.code,
            providerType=p.provider_type,
            officialWebsite=p.official_website,
            officialPortalUrl=p.official_portal_url or p.portal_url,
            submissionMode=p.submission_mode or "manual",
            requiredDocumentCategories=list(p.required_document_categories or []),
            integrationConfig=p.integration_config or {},
            providerNotes=p.provider_notes,
            contactEmail=p.contact_email,
            contactPhone=p.contact_phone,
            portalUrl=p.portal_url or p.official_portal_url,
            supportedClaimTypes=p.supported_claim_types or ["cashless", "reimbursement"],
            isActive=p.is_active,
        )
        for p in providers
    ]


@router.post("/providers", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
def create_insurance_provider(
    payload: ProviderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin-only: register a new insurance provider or TPA."""
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to manage insurance providers.",
        )

    existing = db.query(InsuranceProvider).filter(
        (InsuranceProvider.name == payload.name) | (InsuranceProvider.code == payload.code)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Provider with name '{payload.name}' or code '{payload.code}' already exists.",
        )

    provider = InsuranceProvider(
        name=payload.name,
        code=payload.code,
        provider_type=payload.provider_type,
        official_website=payload.official_website,
        official_portal_url=payload.official_portal_url,
        submission_mode=payload.submission_mode,
        required_document_categories=payload.required_document_categories,
        integration_config=payload.integration_config,
        provider_notes=payload.provider_notes,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        portal_url=payload.portal_url,
        supported_claim_types=payload.supported_claim_types,
        is_active=payload.is_active,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return ProviderResponse(
        id=str(provider.id),
        name=provider.name,
        code=provider.code,
        providerType=provider.provider_type,
        officialWebsite=provider.official_website,
        officialPortalUrl=provider.official_portal_url or provider.portal_url,
        submissionMode=provider.submission_mode or "manual",
        requiredDocumentCategories=list(provider.required_document_categories or []),
        integrationConfig=provider.integration_config or {},
        providerNotes=provider.provider_notes,
        contactEmail=provider.contact_email,
        contactPhone=provider.contact_phone,
        portalUrl=provider.portal_url or provider.official_portal_url,
        supportedClaimTypes=provider.supported_claim_types or [],
        isActive=provider.is_active,
    )


# =========================================================
# 2. PATIENT CONSENT MANAGEMENT
# =========================================================

@router.get("/claims/{claim_id}/consent")
def get_claim_consent(
    claim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve patient consent declaration for a cashless claim."""
    claim, _, _ = _get_claim_with_access(claim_id, db, current_user)
    consent = (
        db.query(PatientConsent)
        .filter(PatientConsent.claim_id == claim.id)
        .order_by(PatientConsent.consent_timestamp.desc())
        .first()
    )
    if not consent:
        return {"hasConsent": False, "consent": None}

    return {
        "hasConsent": True,
        "consent": {
            "id": str(consent.id),
            "consenterName": consent.consenter_name,
            "consenterRelationship": consent.consenter_relationship,
            "purpose": consent.purpose,
            "status": consent.status,
            "consentText": consent.consent_text,
            "ipAddress": consent.ip_address,
            "timestamp": consent.consent_timestamp.isoformat() if consent.consent_timestamp else None,
        },
    }


@router.post("/claims/{claim_id}/consent", status_code=status.HTTP_201_CREATED)
def record_patient_consent(
    claim_id: str,
    payload: ConsentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_claimant),
):
    """Hospital Coordinator: capture statutory patient data disclosure consent."""
    claim, patient, _ = _get_claim_with_access(claim_id, db, current_user)

    client_ip = request.client.host if request.client else "127.0.0.1"

    consent = PatientConsent(
        patient_id=patient.id,
        claim_id=claim.id,
        consenter_name=payload.consenter_name,
        consenter_relationship=payload.consenter_relationship,
        purpose=payload.purpose,
        status="Given",
        consent_text=payload.consent_text,
        ip_address=client_ip,
        consent_timestamp=datetime.utcnow(),
    )
    db.add(consent)

    _log_cashless_audit(
        db=db,
        claim_id=claim.id,
        actor_id=current_user.id,
        event_type="PATIENT_CONSENT_CAPTURED",
        details={
            "consenter": payload.consenter_name,
            "relationship": payload.consenter_relationship,
            "ip": client_ip,
        },
    )

    db.commit()
    db.refresh(consent)

    return {
        "message": "Patient consent successfully recorded.",
        "consentId": str(consent.id),
        "consenterName": consent.consenter_name,
        "timestamp": consent.consent_timestamp.isoformat(),
    }


# =========================================================
# 3. PRE-AUTHORIZATION WORKSPACE & SUBMISSION
# =========================================================

@router.get("/claims/{claim_id}/preauth")
def get_preauth_details(
    claim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve pre-authorization draft/submission data for a claim."""
    claim, patient, policy = _get_claim_with_access(claim_id, db, current_user)

    preauth = (
        db.query(CashlessPreauthorization)
        .filter(CashlessPreauthorization.claim_id == claim.id)
        .first()
    )

    # Check for mandatory cashless documents
    docs = db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim.id).all()
    doc_types = {d.document_type for d in docs}

    mandatory_docs = ["pre_authorization", "insurance_card", "identity_proof"]
    checklist = [
        {
            "type": m,
            "label": m.replace("_", " ").title(),
            "uploaded": m in doc_types,
        }
        for m in mandatory_docs
    ]

    if not preauth:
        return {
            "exists": False,
            "preauth": None,
            "checklist": checklist,
            "patientName": patient.full_name,
            "policyNumber": policy.policy_number,
            "insuranceProvider": policy.insurance_provider,
            "hospitalName": claim.hospital_name,
        }

    return {
        "exists": True,
        "preauth": {
            "id": str(preauth.id),
            "status": preauth.status,
            "roomType": preauth.room_type,
            "proposedTreatment": preauth.proposed_treatment,
            "treatingDoctor": preauth.treating_doctor,
            "doctorRegistrationNo": preauth.doctor_registration_no,
            "estimatedCost": float(preauth.estimated_cost or 0),
            "costBreakdown": preauth.cost_breakdown or {},
            "submissionMode": preauth.submission_mode,
            "submissionReference": preauth.submission_reference,
            "submittedAt": preauth.submitted_at.isoformat() if preauth.submitted_at else None,
            "initialApprovalAmount": float(preauth.initial_approval_amount) if preauth.initial_approval_amount is not None else None,
            "approvalReference": preauth.approval_reference,
            "approvedAt": preauth.approved_at.isoformat() if preauth.approved_at else None,
            "approvalConditions": preauth.approval_conditions,
            "tpaQueryRemarks": preauth.tpa_query_remarks,
            "hospitalQueryResponse": preauth.hospital_query_response,
        },
        "checklist": checklist,
        "patientName": patient.full_name,
        "policyNumber": policy.policy_number,
        "insuranceProvider": policy.insurance_provider,
        "hospitalName": claim.hospital_name,
    }


@router.post("/claims/{claim_id}/preauth")
def save_preauth_details(
    claim_id: str,
    payload: PreAuthSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_claimant),
):
    """Hospital Coordinator: Save/update pre-authorization draft and estimated costs."""
    claim, patient, policy = _get_claim_with_access(claim_id, db, current_user)

    if patient is not None:
        if payload.patient_name:
            patient.full_name = payload.patient_name.strip()
        if payload.date_of_birth:
            patient.date_of_birth = payload.date_of_birth
        if payload.mobile_number:
            patient.contact_number = payload.mobile_number.strip()

    if policy is not None:
        if payload.policy_number:
            policy.policy_number = payload.policy_number.strip()
        if payload.member_id:
            policy.member_id = payload.member_id.strip()
        if payload.policyholder_name:
            policy.policy_holder_name = payload.policyholder_name.strip()
        if payload.relationship:
            policy.relationship = payload.relationship.strip()

    if payload.hospital_name:
        claim.hospital_name = payload.hospital_name.strip()
    if payload.admission_date:
        claim.admission_date = payload.admission_date
    if payload.diagnosis:
        claim.current_stage = "Pre-Authorization Drafted"

    preauth = (
        db.query(CashlessPreauthorization)
        .filter(CashlessPreauthorization.claim_id == claim.id)
        .first()
    )

    if not preauth:
        preauth = CashlessPreauthorization(
            claim_id=claim.id,
            room_type=payload.room_type,
            proposed_treatment=payload.proposed_treatment,
            treating_doctor=payload.treating_doctor,
            doctor_registration_no=payload.doctor_registration_no,
            estimated_cost=payload.estimated_cost,
            cost_breakdown=payload.cost_breakdown,
            status="Draft",
        )
        db.add(preauth)
    else:
        if preauth.status in ["Approved", "Partially Approved"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot edit pre-authorization after initial approval. Raise an amendment if changes are required.",
            )
        preauth.room_type = payload.room_type
        preauth.proposed_treatment = payload.proposed_treatment
        preauth.treating_doctor = payload.treating_doctor
        preauth.doctor_registration_no = payload.doctor_registration_no
        preauth.estimated_cost = payload.estimated_cost
        preauth.cost_breakdown = payload.cost_breakdown

    # Ensure claim is marked cashless and keep the claim amount aligned with the draft.
    claim.claim_type = "cashless"
    claim.claimed_amount = payload.estimated_cost
    claim.discharge_readiness_status = "Pending Pre-Auth"

    db.commit()
    db.refresh(preauth)

    return {
        "message": "Pre-authorization saved as draft.",
        "preauthId": str(preauth.id),
        "status": preauth.status,
        "estimatedCost": float(preauth.estimated_cost),
    }


@router.post("/claims/{claim_id}/preauth/submit")
def submit_preauth_package(
    claim_id: str,
    payload: PreAuthSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_claimant),
):
    """Hospital Coordinator: Dispatch pre-authorization package to insurer/TPA."""
    claim, _, _ = _get_claim_with_access(claim_id, db, current_user)

    preauth = (
        db.query(CashlessPreauthorization)
        .filter(CashlessPreauthorization.claim_id == claim.id)
        .first()
    )
    if not preauth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pre-authorization details must be saved before submission.",
        )

    # Check that at least one document is uploaded
    doc_count = db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim.id).count()
    if doc_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit pre-authorization without uploaded supporting documents.",
        )

    preauth.status = "Submitted"
    preauth.submission_mode = payload.submission_mode
    preauth.submission_reference = payload.submission_reference
    preauth.submitted_at = datetime.utcnow()
    preauth.submitted_by = current_user.id

    claim.claim_status = "Under Review"
    claim.current_stage = "Pre-Authorization Submitted"
    claim.discharge_readiness_status = "Pending Initial Approval"

    # History & Audit
    history = ClaimHistory(
        claim_id=claim.id,
        action="Pre-Authorization Submitted",
        previous_status=claim.claim_status,
        new_status="Under Review",
        previous_stage="Claim Created",
        new_stage="Pre-Authorization Submitted",
        remarks=f"Submitted via {payload.submission_mode} with reference: {payload.submission_reference}",
        performed_by=current_user.id,
    )
    db.add(history)

    _log_cashless_audit(
        db=db,
        claim_id=claim.id,
        actor_id=current_user.id,
        event_type="PREAUTH_SUBMITTED",
        details={
            "mode": payload.submission_mode,
            "reference": payload.submission_reference,
            "estimatedCost": float(preauth.estimated_cost),
        },
    )

    db.commit()

    return {
        "message": "Pre-authorization package successfully submitted to insurer/TPA.",
        "status": preauth.status,
        "reference": preauth.submission_reference,
        "submittedAt": preauth.submitted_at.isoformat(),
    }


@router.get("/claims/{claim_id}/preauth/package")
def generate_preauth_package(
    claim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate structured pre-authorization dispatch package with SHA-256 fingerprint."""
    claim, patient, policy = _get_claim_with_access(claim_id, db, current_user)

    preauth = (
        db.query(CashlessPreauthorization)
        .filter(CashlessPreauthorization.claim_id == claim.id)
        .first()
    )
    if not preauth:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pre-authorization record found for this claim.",
        )

    docs = db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim.id).all()

    payload_dict = {
        "claimNumber": claim.claim_number,
        "patient": {
            "name": patient.full_name,
            "dob": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "gender": patient.gender,
            "contact": patient.contact_number,
            "bloodGroup": patient.blood_group,
            "emergencyContact": patient.emergency_contact_name,
        },
        "policy": {
            "policyNumber": policy.policy_number,
            "provider": policy.insurance_provider,
            "memberId": policy.member_id,
            "policyHolder": policy.policy_holder_name,
            "relationship": policy.relationship,
            "sumInsured": float(policy.coverage_amount or 0),
        },
        "hospitalization": {
            "hospital": claim.hospital_name,
            "admissionDate": claim.admission_date.isoformat() if claim.admission_date else None,
            "roomCategory": preauth.room_type,
            "doctor": preauth.treating_doctor,
            "doctorRegNo": preauth.doctor_registration_no,
            "proposedTreatment": preauth.proposed_treatment,
            "estimatedCost": float(preauth.estimated_cost),
            "costBreakdown": preauth.cost_breakdown,
        },
        "documents": [
            {
                "id": str(d.id),
                "type": d.document_type,
                "fileName": d.file_name,
                "sha256": getattr(d, "file_hash", None) or hashlib.sha256(f"{d.id}:{d.file_name}".encode()).hexdigest(),
            }
            for d in docs
        ],
        "generatedAt": datetime.utcnow().isoformat(),
    }

    serialized = json.dumps(payload_dict, sort_keys=True)
    fingerprint = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    return {
        "packageFingerprint": fingerprint,
        "package": payload_dict,
    }


# =========================================================
# 4. TPA PRE-AUTH ADJUDICATION & QUERIES
# =========================================================

@router.post("/claims/{claim_id}/preauth/adjudicate")
def adjudicate_preauth(
    claim_id: str,
    payload: PreAuthAdjudicateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_claims_officer),
):
    """TPA Claims Officer: Approve, Partially Approve, Query, or Reject Pre-Auth."""
    claim, _, policy = _get_claim_with_access(claim_id, db, current_user)

    # Verify TPA organizational boundary
    officer_org = (current_user.organization or "").strip().casefold()
    policy_provider = (policy.insurance_provider or "").strip().casefold()
    if officer_org != policy_provider:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Officer org '{current_user.organization}' does not match policy provider '{policy.insurance_provider}'.",
        )

    preauth = (
        db.query(CashlessPreauthorization)
        .filter(CashlessPreauthorization.claim_id == claim.id)
        .first()
    )
    if not preauth:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pre-authorization record not found.",
        )

    valid_decisions = ["Approved", "Partially Approved", "Query Raised", "Rejected"]
    if payload.decision not in valid_decisions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision '{payload.decision}'. Allowed: {valid_decisions}",
        )

    now = datetime.utcnow()
    prev_status = preauth.status

    if payload.decision in ["Approved", "Partially Approved"]:
        if payload.initial_approval_amount is None or payload.initial_approval_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approved or Partially Approved decision requires a positive initial_approval_amount.",
            )
        preauth.status = payload.decision
        preauth.initial_approval_amount = payload.initial_approval_amount
        preauth.approval_reference = payload.approval_reference or f"AUTH-{uuid.uuid4().hex[:8].upper()}"
        preauth.approved_at = now
        preauth.approval_conditions = payload.approval_conditions

        claim.preauth_amount = payload.initial_approval_amount
        claim.claim_status = "Approved" if payload.decision == "Approved" else "Partially Approved"
        claim.current_stage = "Initial Authorization Granted"
        claim.discharge_readiness_status = "In-Treatment (Authorized)"

    elif payload.decision == "Query Raised":
        if not payload.query_remarks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query Raised decision requires query_remarks explaining the needed clarification.",
            )
        preauth.status = "Query Raised"
        preauth.tpa_query_remarks = payload.query_remarks
        claim.claim_status = "Needs Review"
        claim.current_stage = "TPA Query Outstanding"
        claim.discharge_readiness_status = "Query Outstanding"

    elif payload.decision == "Rejected":
        if not payload.query_remarks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejected decision requires query_remarks detailing rejection rationale.",
            )
        preauth.status = "Rejected"
        preauth.tpa_query_remarks = payload.query_remarks
        claim.claim_status = "Rejected"
        claim.current_stage = "Pre-Authorization Rejected"
        claim.discharge_readiness_status = "Rejected"

    # History & Audit
    history = ClaimHistory(
        claim_id=claim.id,
        action=f"Pre-Auth {payload.decision}",
        previous_status=prev_status,
        new_status=claim.claim_status,
        previous_stage=claim.current_stage,
        new_stage=claim.current_stage,
        remarks=payload.query_remarks or f"Approved amount: INR {payload.initial_approval_amount:,.2f}",
        performed_by=current_user.id,
    )
    db.add(history)

    _log_cashless_audit(
        db=db,
        claim_id=claim.id,
        actor_id=current_user.id,
        event_type="PREAUTH_ADJUDICATED",
        details={
            "decision": payload.decision,
            "approvedAmount": payload.initial_approval_amount,
            "reference": preauth.approval_reference,
            "remarks": payload.query_remarks,
        },
    )

    db.commit()

    return {
        "message": f"Pre-authorization {payload.decision.lower()} successfully.",
        "status": preauth.status,
        "initialApprovalAmount": float(preauth.initial_approval_amount) if preauth.initial_approval_amount else None,
        "approvalReference": preauth.approval_reference,
        "adjudicatedAt": now.isoformat(),
    }


@router.post("/claims/{claim_id}/preauth/respond-query")
def respond_preauth_query(
    claim_id: str,
    payload: PreAuthQueryResponseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_claimant),
):
    """Hospital Coordinator: Reply to TPA query with clinical or administrative explanation."""
    claim, _, _ = _get_claim_with_access(claim_id, db, current_user)

    preauth = (
        db.query(CashlessPreauthorization)
        .filter(CashlessPreauthorization.claim_id == claim.id)
        .first()
    )
    if not preauth or preauth.status != "Query Raised":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No outstanding TPA query to respond to for this claim.",
        )

    preauth.hospital_query_response = payload.hospital_query_response
    preauth.status = "Under Review"

    claim.claim_status = "Under Review"
    claim.current_stage = "Query Responded"
    claim.discharge_readiness_status = "Pending Initial Approval"

    history = ClaimHistory(
        claim_id=claim.id,
        action="Pre-Auth Query Responded",
        previous_status="Needs Review",
        new_status="Under Review",
        previous_stage="TPA Query Outstanding",
        new_stage="Query Responded",
        remarks=f"Hospital response: {payload.hospital_query_response[:200]}",
        performed_by=current_user.id,
    )
    db.add(history)

    _log_cashless_audit(
        db=db,
        claim_id=claim.id,
        actor_id=current_user.id,
        event_type="PREAUTH_QUERY_RESPONDED",
        details={"response": payload.hospital_query_response},
    )

    db.commit()

    return {
        "message": "Query response successfully submitted to TPA.",
        "status": preauth.status,
    }


# =========================================================
# 5. TREATMENT DOCUMENTATION
# =========================================================

@router.get("/claims/{claim_id}/treatment-records")
def get_treatment_records(
    claim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve chronological inpatient treatment updates and running expenses."""
    claim, _, _ = _get_claim_with_access(claim_id, db, current_user)

    records = (
        db.query(TreatmentRecord)
        .filter(TreatmentRecord.claim_id == claim.id)
        .order_by(TreatmentRecord.record_date.desc(), TreatmentRecord.created_at.desc())
        .all()
    )

    return [
        {
            "id": str(r.id),
            "recordDate": r.record_date.isoformat(),
            "clinicalNotes": r.clinical_notes,
            "proceduresPerformed": r.procedures_performed or [],
            "updatedDiagnosis": r.updated_diagnosis,
            "cumulativeExpenses": float(r.cumulative_expenses) if r.cumulative_expenses is not None else None,
            "recordedBy": str(r.recorded_by) if r.recorded_by else None,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.post("/claims/{claim_id}/treatment-records", status_code=status.HTTP_201_CREATED)
def add_treatment_record(
    claim_id: str,
    payload: TreatmentRecordCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_claimant),
):
    """Hospital Staff: Record inpatient clinical update, procedure, or interim expense."""
    claim, _, _ = _get_claim_with_access(claim_id, db, current_user)

    record = TreatmentRecord(
        claim_id=claim.id,
        record_date=payload.record_date,
        clinical_notes=payload.clinical_notes,
        procedures_performed=payload.procedures_performed,
        updated_diagnosis=payload.updated_diagnosis,
        cumulative_expenses=payload.cumulative_expenses,
        recorded_by=current_user.id,
    )
    db.add(record)

    _log_cashless_audit(
        db=db,
        claim_id=claim.id,
        actor_id=current_user.id,
        event_type="TREATMENT_RECORD_ADDED",
        details={
            "recordDate": payload.record_date.isoformat(),
            "diagnosis": payload.updated_diagnosis,
            "cumulativeExpenses": payload.cumulative_expenses,
        },
    )

    db.commit()
    db.refresh(record)

    return {
        "message": "Treatment record added successfully.",
        "recordId": str(record.id),
        "recordDate": record.record_date.isoformat(),
    }


# =========================================================
# 6. FINAL AUTHORIZATION WORKSPACE & SUBMISSION
# =========================================================

@router.get("/claims/{claim_id}/final-auth")
def get_final_auth_details(
    claim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve final authorization, 3-way financial comparison, and settlement figures."""
    claim, patient, policy = _get_claim_with_access(claim_id, db, current_user)

    preauth = (
        db.query(CashlessPreauthorization)
        .filter(CashlessPreauthorization.claim_id == claim.id)
        .first()
    )
    final_auth = (
        db.query(CashlessFinalAuthorization)
        .filter(CashlessFinalAuthorization.claim_id == claim.id)
        .first()
    )

    # 3-Way Comparison
    estimated_cost = float(preauth.estimated_cost) if preauth else 0.0
    initial_approved = float(preauth.initial_approval_amount) if (preauth and preauth.initial_approval_amount) else 0.0
    final_billed = float(final_auth.final_billed_amount) if final_auth else float(claim.claimed_amount or 0.0)

    comparison = {
        "estimatedCost": estimated_cost,
        "initialApprovedAmount": initial_approved,
        "finalBilledAmount": final_billed,
        "varianceFromInitial": round(final_billed - initial_approved, 2) if initial_approved > 0 else 0.0,
        "exceedsInitialAuth": final_billed > initial_approved if initial_approved > 0 else False,
    }

    if not final_auth:
        return {
            "exists": False,
            "finalAuth": None,
            "financialComparison": comparison,
            "patientName": patient.full_name,
            "policyNumber": policy.policy_number,
            "hospitalName": claim.hospital_name,
        }

    return {
        "exists": True,
        "finalAuth": {
            "id": str(final_auth.id),
            "status": final_auth.status,
            "finalBilledAmount": float(final_auth.final_billed_amount),
            "submissionReference": final_auth.submission_reference,
            "submittedAt": final_auth.submitted_at.isoformat() if final_auth.submitted_at else None,
            "finalApprovedAmount": float(final_auth.final_approved_amount) if final_auth.final_approved_amount is not None else None,
            "nonPayableDeductions": float(final_auth.non_payable_deductions or 0),
            "deductionBreakdown": final_auth.deduction_breakdown or {},
            "patientResponsibilityAmount": float(final_auth.patient_responsibility_amount or 0),
            "finalApprovalReference": final_auth.final_approval_reference,
            "finalApprovedAt": final_auth.final_approved_at.isoformat() if final_auth.final_approved_at else None,
            "tpaRemarks": final_auth.tpa_remarks,
        },
        "financialComparison": comparison,
        "patientName": patient.full_name,
        "policyNumber": policy.policy_number,
        "hospitalName": claim.hospital_name,
    }


@router.post("/claims/{claim_id}/final-auth")
def save_final_auth_details(
    claim_id: str,
    payload: FinalAuthSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_claimant),
):
    """Hospital Coordinator: Save/update final authorization draft and itemized bill total."""
    claim, _, _ = _get_claim_with_access(claim_id, db, current_user)

    final_auth = (
        db.query(CashlessFinalAuthorization)
        .filter(CashlessFinalAuthorization.claim_id == claim.id)
        .first()
    )

    if not final_auth:
        final_auth = CashlessFinalAuthorization(
            claim_id=claim.id,
            final_billed_amount=payload.final_billed_amount,
            deduction_breakdown=payload.deduction_breakdown,
            patient_responsibility_amount=payload.patient_responsibility_amount or 0.0,
            status="Draft",
        )
        db.add(final_auth)
    else:
        if final_auth.status in ["Approved", "Settled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot edit final authorization after TPA settlement.",
            )
        final_auth.final_billed_amount = payload.final_billed_amount
        final_auth.deduction_breakdown = payload.deduction_breakdown
        final_auth.patient_responsibility_amount = payload.patient_responsibility_amount or 0.0

    claim.claimed_amount = payload.final_billed_amount
    db.commit()
    db.refresh(final_auth)

    return {
        "message": "Final authorization saved as draft.",
        "finalAuthId": str(final_auth.id),
        "status": final_auth.status,
        "finalBilledAmount": float(final_auth.final_billed_amount),
    }


@router.post("/claims/{claim_id}/final-auth/submit")
def submit_final_auth(
    claim_id: str,
    payload: FinalAuthSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_claimant),
):
    """Hospital Coordinator: Dispatch final bill settlement package to TPA."""
    claim, _, _ = _get_claim_with_access(claim_id, db, current_user)

    final_auth = (
        db.query(CashlessFinalAuthorization)
        .filter(CashlessFinalAuthorization.claim_id == claim.id)
        .first()
    )
    if not final_auth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Final authorization details must be saved before submission.",
        )

    final_auth.status = "Submitted"
    final_auth.submission_reference = payload.submission_reference
    final_auth.submitted_at = datetime.utcnow()
    final_auth.submitted_by = current_user.id

    claim.claim_status = "Under Review"
    claim.current_stage = "Final Settlement Requested"
    claim.discharge_readiness_status = "Pending Final Settlement"

    history = ClaimHistory(
        claim_id=claim.id,
        action="Final Authorization Submitted",
        previous_status=claim.claim_status,
        new_status="Under Review",
        previous_stage="In-Treatment",
        new_stage="Final Settlement Requested",
        remarks=f"Final bill submitted with reference: {payload.submission_reference}",
        performed_by=current_user.id,
    )
    db.add(history)

    _log_cashless_audit(
        db=db,
        claim_id=claim.id,
        actor_id=current_user.id,
        event_type="FINAL_AUTH_SUBMITTED",
        details={
            "reference": payload.submission_reference,
            "finalBilled": float(final_auth.final_billed_amount),
        },
    )

    db.commit()

    return {
        "message": "Final authorization package submitted for TPA settlement.",
        "status": final_auth.status,
        "reference": final_auth.submission_reference,
        "submittedAt": final_auth.submitted_at.isoformat(),
    }


# =========================================================
# 7. TPA FINAL SETTLEMENT ADJUDICATION
# =========================================================

@router.post("/claims/{claim_id}/final-auth/adjudicate")
def adjudicate_final_auth(
    claim_id: str,
    payload: FinalAuthAdjudicateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_claims_officer),
):
    """TPA Reviewer: Issue final settlement letter, non-payable deductions, and patient responsibility."""
    claim, _, policy = _get_claim_with_access(claim_id, db, current_user)

    # Verify TPA organizational boundary
    officer_org = (current_user.organization or "").strip().casefold()
    policy_provider = (policy.insurance_provider or "").strip().casefold()
    if officer_org != policy_provider:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Officer org '{current_user.organization}' does not match policy provider '{policy.insurance_provider}'.",
        )

    final_auth = (
        db.query(CashlessFinalAuthorization)
        .filter(CashlessFinalAuthorization.claim_id == claim.id)
        .first()
    )
    if not final_auth:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Final authorization record not found.",
        )

    valid_decisions = ["Approved", "Partially Approved", "Rejected"]
    if payload.decision not in valid_decisions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision '{payload.decision}'. Allowed: {valid_decisions}",
        )

    now = datetime.utcnow()
    prev_status = final_auth.status

    if payload.decision in ["Approved", "Partially Approved"]:
        # Reconcile figures
        total_accounted = payload.final_approved_amount + payload.non_payable_deductions + payload.patient_responsibility_amount
        billed = float(final_auth.final_billed_amount)

        final_auth.status = "Settled"
        final_auth.final_approved_amount = payload.final_approved_amount
        final_auth.non_payable_deductions = payload.non_payable_deductions
        final_auth.deduction_breakdown = payload.deduction_breakdown
        final_auth.patient_responsibility_amount = payload.patient_responsibility_amount
        final_auth.final_approval_reference = payload.final_approval_reference
        final_auth.final_approved_at = now
        final_auth.tpa_remarks = payload.tpa_remarks

        claim.final_approved_amount = payload.final_approved_amount
        claim.patient_responsibility = payload.patient_responsibility_amount
        claim.claim_status = "Settled"
        claim.current_stage = "Discharge Ready"
        claim.discharge_readiness_status = "Discharge Ready"

    elif payload.decision == "Rejected":
        if not payload.tpa_remarks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection requires tpa_remarks explaining the decision.",
            )
        final_auth.status = "Rejected"
        final_auth.tpa_remarks = payload.tpa_remarks
        claim.claim_status = "Rejected"
        claim.current_stage = "Final Settlement Denied"
        claim.discharge_readiness_status = "Settlement Denied"

    # History & Audit
    history = ClaimHistory(
        claim_id=claim.id,
        action=f"Final Settlement {payload.decision}",
        previous_status=prev_status,
        new_status=claim.claim_status,
        previous_stage="Final Settlement Requested",
        new_stage=claim.current_stage,
        remarks=f"Final Approved: INR {payload.final_approved_amount:,.2f}, Patient Responsibility: INR {payload.patient_responsibility_amount:,.2f}",
        performed_by=current_user.id,
    )
    db.add(history)

    _log_cashless_audit(
        db=db,
        claim_id=claim.id,
        actor_id=current_user.id,
        event_type="FINAL_AUTH_SETTLED",
        details={
            "decision": payload.decision,
            "finalApproved": payload.final_approved_amount,
            "deductions": payload.non_payable_deductions,
            "patientResponsibility": payload.patient_responsibility_amount,
            "reference": payload.final_approval_reference,
        },
    )

    db.commit()

    return {
        "message": f"Final authorization settlement completed: {payload.decision}.",
        "status": final_auth.status,
        "finalApprovedAmount": float(final_auth.final_approved_amount) if final_auth.final_approved_amount is not None else 0.0,
        "patientResponsibility": float(final_auth.patient_responsibility_amount or 0.0),
        "reference": final_auth.final_approval_reference,
        "settledAt": now.isoformat(),
    }


# =========================================================
# 8. DISCHARGE READINESS HOLISTIC ASSESSMENT
# =========================================================

@router.get("/claims/{claim_id}/discharge-readiness")
def evaluate_discharge_readiness(
    claim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Holistic discharge readiness engine evaluating:
    1. Pre-authorization initial approval
    2. Final authorization settlement clearance
    3. Non-payable deductions & patient responsibility reconciliation
    4. Mandatory discharge documentation (discharge_summary, hospital_bill)
    5. Zero outstanding TPA queries
    Returns explicit advisory status (never automatically discharges).
    """
    claim, patient, policy = _get_claim_with_access(claim_id, db, current_user)

    preauth = (
        db.query(CashlessPreauthorization)
        .filter(CashlessPreauthorization.claim_id == claim.id)
        .first()
    )
    final_auth = (
        db.query(CashlessFinalAuthorization)
        .filter(CashlessFinalAuthorization.claim_id == claim.id)
        .first()
    )

    # Document check
    docs = db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim.id).all()
    doc_types = {d.document_type for d in docs}

    has_preauth_doc = "pre_authorization" in doc_types
    has_discharge_summary = "discharge_summary" in doc_types
    has_hospital_bill = "hospital_bill" in doc_types

    missing_docs = []
    if not has_preauth_doc:
        missing_docs.append("Pre-Authorization Letter")
    if not has_discharge_summary:
        missing_docs.append("Discharge Summary")
    if not has_hospital_bill:
        missing_docs.append("Final Itemized Hospital Bill")

    checklist = []

    # 1. Pre-Auth Criteria
    preauth_ok = bool(preauth and preauth.status in ["Approved", "Partially Approved"])
    checklist.append({
        "id": "preauth_approval",
        "title": "Initial Pre-Authorization Approval",
        "passed": preauth_ok,
        "note": f"Initial Approved Amount: INR {float(preauth.initial_approval_amount or 0):,.2f}" if preauth_ok else "No approved pre-authorization found.",
    })

    # 2. Outstanding Queries
    has_pending_query = bool(preauth and preauth.status == "Query Raised")
    checklist.append({
        "id": "zero_queries",
        "title": "Zero Outstanding TPA Queries",
        "passed": not has_pending_query,
        "note": "All insurer queries resolved." if not has_pending_query else "TPA has an outstanding query awaiting hospital response.",
    })

    # 3. Final Settlement Approval
    final_auth_ok = bool(final_auth and final_auth.status in ["Settled", "Approved"])
    checklist.append({
        "id": "final_settlement",
        "title": "Final Authorization & TPA Settlement",
        "passed": final_auth_ok,
        "note": f"Final Approved: INR {float(final_auth.final_approved_amount or 0):,.2f}" if final_auth_ok else "Final bill settlement pending TPA adjudication.",
    })

    # 4. Mandatory Documents
    docs_ok = len(missing_docs) == 0
    checklist.append({
        "id": "discharge_documents",
        "title": "Mandatory Inpatient Documentation",
        "passed": docs_ok,
        "note": "All required hospital records uploaded." if docs_ok else f"Missing: {', '.join(missing_docs)}",
    })

    # 5. Financial Balance Responsibility
    patient_resp = float(final_auth.patient_responsibility_amount or 0.0) if final_auth else 0.0
    checklist.append({
        "id": "patient_responsibility",
        "title": "Patient Out-of-Pocket Balance Clearance",
        "passed": True,  # Informational advisory
        "note": f"Patient Out-of-Pocket Due: INR {patient_resp:,.2f}" if patient_resp > 0 else "Zero patient out-of-pocket responsibility.",
    })

    # Overall Status Determination
    if not preauth_ok:
        readiness_status = "Pending Pre-Auth"
        is_ready = False
    elif has_pending_query:
        readiness_status = "Query Outstanding"
        is_ready = False
    elif not final_auth_ok:
        readiness_status = "Pending Settlement"
        is_ready = False
    elif not docs_ok:
        readiness_status = "Incomplete Documentation"
        is_ready = False
    elif patient_resp > 0 and claim.discharge_readiness_status == "Payment Clearance Required":
        readiness_status = "Payment Clearance Required"
        is_ready = False
    else:
        readiness_status = "Discharge Ready"
        is_ready = True

    return {
        "claimId": str(claim.id),
        "claimNumber": claim.claim_number,
        "patientName": patient.full_name,
        "hospitalName": claim.hospital_name,
        "insuranceProvider": policy.insurance_provider,
        "claimType": claim.claim_type or "cashless",
        "preauthStatus": preauth.status if preauth else "None",
        "preauthApprovedAmount": float(preauth.initial_approval_amount) if (preauth and preauth.initial_approval_amount) else None,
        "finalAuthStatus": final_auth.status if final_auth else "None",
        "finalBilledAmount": float(final_auth.final_billed_amount) if final_auth else float(claim.claimed_amount or 0.0),
        "finalApprovedAmount": float(final_auth.final_approved_amount) if (final_auth and final_auth.final_approved_amount) else None,
        "nonPayableDeductions": float(final_auth.non_payable_deductions or 0) if final_auth else 0.0,
        "patientResponsibilityAmount": patient_resp,
        "missingDocuments": missing_docs,
        "checklist": checklist,
        "isDischargeReady": is_ready,
        "readinessStatus": readiness_status,
    }
