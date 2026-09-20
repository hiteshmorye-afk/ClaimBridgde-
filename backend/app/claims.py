import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db
from .models import Claim, Patient, Policy, ClaimDocument


router = APIRouter(
    prefix="/claims",
    tags=["Claims"],
)


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class CreateClaimRequest(BaseModel):
    id: Optional[str] = None

    patientName: str
    patientAge: int = 0

    hospital: str = ""

    policyNumber: str
    insuranceProvider: str

    diagnosis: str = ""

    admissionDate: Optional[str] = None
    dischargeDate: Optional[str] = None

    claimedAmount: float = 0.0

    status: str = "Under Analysis"
    stage: str = "01 Secure Document Intake"

    readiness: float = 0.0
    ocrConfidence: float = 0.0
    medicalRisk: float = 0.0
    medicalConfidence: float = 0.0
    policyConfidence: float = 0.0
    validationReadiness: float = 0.0
    overallConfidence: float = 0.0


class UpdateClaimStatusRequest(BaseModel):
    action: str
    note: Optional[str] = None


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def parse_date(value: Optional[str]) -> Optional[date]:
    """
    Convert YYYY-MM-DD string into Python date.
    """
    if not value:
        return None

    try:
        return date.fromisoformat(value)

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid date format: {value}. "
                "Expected YYYY-MM-DD."
            ),
        )


def generate_claim_number() -> str:
    """
    Generate a unique ClaimBridge claim number.
    Example:
    CLM-2026-A1B2C3
    """
    return (
        f"CLM-{date.today().year}-"
        f"{uuid.uuid4().hex[:6].upper()}"
    )


def serialize_claim(
    claim: Claim,
    patient: Patient,
    policy: Policy,
    documents: list[ClaimDocument],
):
    """
    Convert database claim records into the
    frontend ClaimApiData format.
    """

    return {
        "id": str(claim.id),

        "patientName": patient.full_name,

        # Patient age is not currently stored in the
        # existing Patient model.
        "patientAge": 0,

        "hospital": "",

        "policyNumber": policy.policy_number,

        "insuranceProvider": (
            policy.insurance_provider
        ),

        "diagnosis": "",

        "admissionDate": (
            claim.admission_date.isoformat()
            if claim.admission_date
            else ""
        ),

        "dischargeDate": (
            claim.discharge_date.isoformat()
            if claim.discharge_date
            else ""
        ),

        "claimedAmount": float(
            claim.claimed_amount or 0
        ),

        "status": claim.claim_status,

        "stage": claim.current_stage,

        "readiness": float(
            claim.readiness_score or 0
        ),

        # These AI fields will be connected to the
        # existing AI pipeline in the next stage.
        "ocrConfidence": 0.0,

        "medicalRisk": 0.0,

        "medicalConfidence": 0.0,

        "policyConfidence": 0.0,

        "validationReadiness": 0.0,

        "overallConfidence": 0.0,

        "documents": [
            {
                "category": document.document_type,

                "fileName": document.file_name,

                "status": (
                    "Processing"
                    if document.processing_status
                    in {
                        "Pending",
                        "Processing",
                    }
                    else "Verified"
                ),
            }

            for document in documents
        ],

        "findings": [],
    }


# =========================================================
# GET ALL CLAIMS
# =========================================================

@router.get("")
def get_claims(
    db: Session = Depends(get_db),
):
    """
    Return all claims from PostgreSQL.
    """

    claims = (
        db.query(Claim)
        .order_by(Claim.created_at.desc())
        .all()
    )

    result = []

    for claim in claims:

        patient = (
            db.query(Patient)
            .filter(
                Patient.id == claim.patient_id
            )
            .first()
        )

        policy = (
            db.query(Policy)
            .filter(
                Policy.id == claim.policy_id
            )
            .first()
        )

        if not patient or not policy:
            continue

        documents = (
            db.query(ClaimDocument)
            .filter(
                ClaimDocument.claim_id == claim.id
            )
            .all()
        )

        result.append(
            serialize_claim(
                claim=claim,
                patient=patient,
                policy=policy,
                documents=documents,
            )
        )

    return result


# =========================================================
# GET SINGLE CLAIM
# =========================================================

@router.get("/{claim_id}")
def get_claim(
    claim_id: str,
    db: Session = Depends(get_db),
):
    """
    Return one claim using its UUID.
    """

    try:
        claim_uuid = uuid.UUID(claim_id)

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid claim ID.",
        )

    claim = (
        db.query(Claim)
        .filter(
            Claim.id == claim_uuid
        )
        .first()
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    patient = (
        db.query(Patient)
        .filter(
            Patient.id == claim.patient_id
        )
        .first()
    )

    policy = (
        db.query(Policy)
        .filter(
            Policy.id == claim.policy_id
        )
        .first()
    )

    documents = (
        db.query(ClaimDocument)
        .filter(
            ClaimDocument.claim_id == claim.id
        )
        .all()
    )

    if not patient or not policy:
        raise HTTPException(
            status_code=500,
            detail=(
                "Claim relationships are incomplete."
            ),
        )

    return serialize_claim(
        claim=claim,
        patient=patient,
        policy=policy,
        documents=documents,
    )


# =========================================================
# CREATE CLAIM
# =========================================================

@router.post("")
def create_claim(
    claim_data: CreateClaimRequest,
    db: Session = Depends(get_db),
):
    """
    Create:

        Patient
            ↓
        Policy
            ↓
        Claim

    The Claim is linked to the Patient and Policy
    using the existing database relationships.
    """

    try:

        # -------------------------------------------------
        # STEP 1 — FIND OR CREATE PATIENT
        # -------------------------------------------------

        patient = (
            db.query(Patient)
            .filter(
                Patient.full_name
                == claim_data.patientName
            )
            .first()
        )

        if not patient:

            patient = Patient(
                full_name=claim_data.patientName,
            )

            db.add(patient)

            # Generate patient UUID before creating Claim.
            db.flush()

        # -------------------------------------------------
        # STEP 2 — FIND OR CREATE POLICY
        # -------------------------------------------------

        policy = (
            db.query(Policy)
            .filter(
                Policy.policy_number
                == claim_data.policyNumber
            )
            .first()
        )

        if not policy:

            policy = Policy(
                policy_number=(
                    claim_data.policyNumber
                ),

                insurance_provider=(
                    claim_data.insuranceProvider
                ),
            )

            db.add(policy)

            # Generate policy UUID before creating Claim.
            db.flush()

        # -------------------------------------------------
        # STEP 3 — CREATE CLAIM
        # -------------------------------------------------

        claim = Claim(
            claim_number=generate_claim_number(),

            patient_id=patient.id,

            policy_id=policy.id,

            admission_date=parse_date(
                claim_data.admissionDate
            ),

            discharge_date=parse_date(
                claim_data.dischargeDate
            ),

            claimed_amount=Decimal(
                str(
                    claim_data.claimedAmount
                    or 0
                )
            ),

            claim_status=(
                claim_data.status
                or "Under Analysis"
            ),

            current_stage=(
                claim_data.stage
                or "01 Secure Document Intake"
            ),

            readiness_score=Decimal(
                str(
                    claim_data.readiness
                    or 0
                )
            ),
        )

        db.add(claim)

        # -------------------------------------------------
        # STEP 4 — COMMIT TRANSACTION
        # -------------------------------------------------

        db.commit()

        db.refresh(claim)

        # -------------------------------------------------
        # STEP 5 — RETURN REAL DATABASE ID
        # -------------------------------------------------

        return {
            "id": str(claim.id),

            "claimNumber": (
                claim.claim_number
            ),

            "patientName": (
                patient.full_name
            ),

            "policyNumber": (
                policy.policy_number
            ),

            "insuranceProvider": (
                policy.insurance_provider
            ),

            "status": (
                claim.claim_status
            ),

            "stage": (
                claim.current_stage
            ),

            "readiness": float(
                claim.readiness_score or 0
            ),

            "message": (
                "Claim created successfully."
            ),
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                f"Claim creation failed: {str(exc)}"
            ),
        )


# =========================================================
# UPDATE CLAIM STATUS
# =========================================================

@router.patch("/{claim_id}/status")
def update_claim_status(
    claim_id: str,
    status_data: UpdateClaimStatusRequest,
    db: Session = Depends(get_db),
):
    """
    Update the workflow status of a claim.
    """

    try:
        claim_uuid = uuid.UUID(claim_id)

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid claim ID.",
        )

    claim = (
        db.query(Claim)
        .filter(
            Claim.id == claim_uuid
        )
        .first()
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    # -----------------------------------------------------
    # MAP FRONTEND ACTION TO DATABASE STATUS
    # -----------------------------------------------------

    action_map = {
        "Approve": "Approved",
        "Reject": "Rejected",
        "RequestInfo": "Needs Review",
        "Escalate": "Needs Review",
    }

    new_status = action_map.get(
        status_data.action
    )

    if not new_status:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported action. "
                "Use Approve, Reject, "
                "RequestInfo, or Escalate."
            ),
        )

    previous_status = claim.claim_status

    # -----------------------------------------------------
    # UPDATE STATUS
    # -----------------------------------------------------

    claim.claim_status = new_status

    # All explicit reviewer decisions reach
    # the Final Decision stage.
    if status_data.action in {
        "Approve",
        "Reject",
        "RequestInfo",
        "Escalate",
    }:

        claim.current_stage = (
            "11 Final Decision"
        )

    db.commit()

    db.refresh(claim)

    # -----------------------------------------------------
    # RETURN RESULT
    # -----------------------------------------------------

    return {
        "success": True,

        "claimId": str(
            claim.id
        ),

        "previousStatus": (
            previous_status
        ),

        "newStatus": (
            claim.claim_status
        ),

        "action": (
            status_data.action
        ),

        "note": (
            status_data.note
        ),
    }