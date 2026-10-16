import json
import math
import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .auth import (
    require_claimant,
    require_claims_officer,
    require_document_reader,
)
from .database import get_db
from .models import (
    AIAnalysis,
    AuditEvent,
    Claim,
    ClaimAmendment,
    ClaimDocument,
    ClaimHistory,
    DocumentExtraction,
    MedicalAnalysis,
    Patient,
    Policy,
    User,
    VerificationResult,
)

router = APIRouter(
    prefix="/claims",
    tags=["Claims"],
)


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class CreateClaimRequest(BaseModel):
    patientName: str
    patientAge: int = 0

    hospital: str = ""

    policyNumber: str
    insuranceProvider: str

    diagnosis: str = ""
    diagnosisCode: Optional[str] = None
    diagnosisCodeSystem: Optional[str] = "ICD-10"
    clinicalNotes: Optional[str] = None

    admissionDate: Optional[str] = None
    dischargeDate: Optional[str] = None

    claimedAmount: float = 0.0


class UpdateClaimStatusRequest(BaseModel):
    action: Literal["Approve", "Reject", "RequestInfo", "Escalate"]
    note: str
    destination: Optional[str] = None
    policyReference: Optional[str] = None
    requestedDocuments: Optional[List[str]] = None


class RequestInfoRequest(BaseModel):
    message: str
    requestedDocuments: Optional[List[str]] = None


class HospitalResponseRequest(BaseModel):
    notes: str
    submittedDocuments: Optional[List[str]] = None


class ClaimAmendmentRequest(BaseModel):
    changes: Dict[str, Any]
    reason: str


class ClaimAmendmentDecisionRequest(BaseModel):
    decision: Literal["Approve", "Reject"]
    note: str


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def parse_date(value: Optional[str]) -> Optional[date]:
    """Convert YYYY-MM-DD string into Python date."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {value}. Expected YYYY-MM-DD.",
        )


def generate_claim_number() -> str:
    """Generate a unique ClaimBridge claim number. Example: CLM-2026-A1B2C3"""
    return f"CLM-{date.today().year}-{uuid.uuid4().hex[:6].upper()}"


def check_claim_access(claim: Claim, policy: Policy, user: Optional[User]) -> bool:
    """
    Verify organization-scoped access:
    - Claimant: can only access claims they submitted
    - Claims officer: can only access claims for their authorized TPA organization
    - Unauthenticated: allowed only when no user context is active (handled by route dependency)
    """
    if not user:
        return False

    if user.role == "claimant":
        return claim.created_by == user.id

    if user.role == "claims_officer":
        user_org = (user.organization or "").strip().casefold()
        insurer = (policy.insurance_provider or "").strip().casefold()
        return bool(user_org and insurer and user_org == insurer)

    return False


def apply_claim_scope(query, user: User):
    """Apply the authenticated user's exact ownership or TPA organization boundary."""
    if user.role == "claimant":
        return query.filter(Claim.created_by == user.id)
    if user.role == "claims_officer" and (user.organization or "").strip():
        return query.filter(
            func.lower(func.trim(Policy.insurance_provider))
            == (user.organization or "").strip().lower()
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Your account has no authorized claim organization.",
    )


def _get_claim_by_identifier(db: Session, claim_id: str) -> Claim:
    try:
        claim_uuid = uuid.UUID(claim_id)
        claim = db.query(Claim).filter(Claim.id == claim_uuid).first()
    except ValueError:
        claim = None
    if not claim:
        claim = db.query(Claim).filter(
            Claim.claim_number.ilike(claim_id.strip())
        ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")
    return claim


# =========================================================
# SERIALIZATION FUNCTION
# =========================================================

def serialize_claim(
    claim: Claim,
    patient: Patient,
    policy: Policy,
    documents: list[ClaimDocument],
    db: Optional[Session] = None,
    detailed: bool = True,
) -> Dict[str, Any]:
    """
    Convert database claim records into comprehensive frontend ClaimApiData
    with real AI scores, 13 pipeline stages, document inventory,
    field-level validation, and persisted history audit trail.
    """
    ocr_confidence = 0.0
    medical_risk = 0.0
    medical_confidence = 0.0
    policy_confidence = 0.0
    validation_readiness = 0.0
    overall_confidence = 0.0
    confidence_calculated = False
    readiness_calculated = False

    diagnosis = ""
    diagnosis_code = ""
    diagnosis_code_system = "ICD-10"
    clinical_notes = ""
    procedure = ""
    hospital = claim.hospital_name or ""
    patient_age = 0
    findings: List[Dict[str, Any]] = []
    missing_docs: List[str] = []
    mismatches: List[str] = []
    risk_indicators: List[str] = []
    policy_status = "Under Review"
    retrieved_clauses: List[Dict[str, Any]] = []
    relevant_exclusions: List[str] = []
    doc_extractions_map: Dict[str, Any] = {}

    if patient.date_of_birth:
        patient_age = max(0, date.today().year - patient.date_of_birth.year)

    if not detailed:
        claim_readiness_val = float(claim.readiness_score or 0)
        route_decision = "Human Review Required"
        return {
            "id": str(claim.id),
            "claimNumber": claim.claim_number,
            "patientName": patient.full_name,
            "patientAge": patient_age if patient_age > 0 else None,
            "hospital": claim.hospital_name or "—",
            "policyNumber": policy.policy_number,
            "insuranceProvider": policy.insurance_provider,
            "diagnosis": "—",
            "diagnosisCode": "—",
            "diagnosisCodeSystem": "ICD-10",
            "clinicalNotes": "",
            "admissionDate": claim.admission_date.isoformat() if claim.admission_date else "—",
            "dischargeDate": claim.discharge_date.isoformat() if claim.discharge_date else "—",
            "claimedAmount": float(claim.claimed_amount or 0),
            "currency": "INR",
            "status": claim.claim_status,
            "stage": claim.current_stage,
            "readiness": claim_readiness_val,
            "ocrConfidence": claim_readiness_val if claim_readiness_val > 0 else None,
            "medicalRisk": 25.0,
            "medicalConfidence": claim_readiness_val if claim_readiness_val > 0 else None,
            "policyConfidence": claim_readiness_val if claim_readiness_val > 0 else None,
            "validationReadiness": claim_readiness_val if claim_readiness_val > 0 else None,
            "overallConfidence": claim_readiness_val if claim_readiness_val > 0 else None,
            "routeDecision": route_decision,
            "routeReasons": [],
            "createdAt": claim.created_at.isoformat() if claim.created_at else None,
            "updatedAt": claim.updated_at.isoformat() if claim.updated_at else None,
            "documents": [],
            "pipelineStages": [],
            "fieldValidationTable": [],
            "medicalEvidence": {},
            "policyEvidence": {},
            "readinessBreakdown": None,
            "confidenceDetails": {
                "overallConfidence": claim_readiness_val if claim_readiness_val > 0 else None,
                "confidenceLevel": "High" if claim_readiness_val >= 85 else ("Medium" if claim_readiness_val >= 70 else "Low"),
                "routeDecision": route_decision,
                "routeReasons": [],
                "componentScores": {},
                "thresholds": {"autoProcessing": 85.0, "readiness": 80.0},
            },
            "history": [],
            "auditEvents": [],
            "findings": [],
        }

    if db:
        # 1. Medical Analysis
        med_analysis = (
            db.query(MedicalAnalysis)
            .filter(MedicalAnalysis.claim_id == claim.id)
            .order_by(MedicalAnalysis.created_at.desc())
            .first()
        )
        if med_analysis:
            diagnosis = med_analysis.diagnosis or ""
            procedure = med_analysis.procedure or ""
            if med_analysis.confidence_score is not None:
                medical_confidence = float(med_analysis.confidence_score)
                confidence_calculated = True
            if med_analysis.risk_score is not None:
                medical_risk = float(med_analysis.risk_score)

        # 2. Verification Result
        verification = (
            db.query(VerificationResult)
            .filter(VerificationResult.claim_id == claim.id)
            .order_by(VerificationResult.created_at.desc())
            .first()
        )
        if verification:
            if verification.readiness_score is not None:
                validation_readiness = float(verification.readiness_score)
                readiness_calculated = True

            if verification.missing_documents and isinstance(verification.missing_documents, list):
                missing_docs = verification.missing_documents
            if verification.mismatches and isinstance(verification.mismatches, list):
                mismatches = verification.mismatches
            if verification.risk_indicators and isinstance(verification.risk_indicators, list):
                risk_indicators = verification.risk_indicators

            if verification.verification_summary:
                try:
                    summary_obj = json.loads(verification.verification_summary)
                    if isinstance(summary_obj, dict):
                        pol = summary_obj.get("policy_intelligence", {})
                        if pol.get("policy_status"):
                            policy_status = pol.get("policy_status")
                            relevant_exclusions = pol.get("relevant_exclusions", [])
                            retrieved_clauses = pol.get("relevant_clauses", pol.get("retrieved_clauses", []))
                            findings.append({
                                "label": "Policy Assessment",
                                "detail": f"Status: {policy_status}. Relevant exclusions: {len(relevant_exclusions)}.",
                                "severity": "ok" if policy_status == "Potentially Covered" else "warn",
                            })
                        med = summary_obj.get("medical_intelligence", {})
                        if med.get("processing_status"):
                            diag_text = med.get("diagnosis") or "Document analysis completed"
                            findings.append({
                                "label": "Medical Intelligence",
                                "detail": f"Documented diagnosis: {diag_text} (Risk Score: {med.get('risk_score', 0)}/100).",
                                "severity": "ok" if (med.get("risk_score", 0) or 0) <= 30 else "warn",
                            })
                        readiness_data = summary_obj.get("claim_readiness", {})
                        if readiness_data.get("readiness_status"):
                            findings.append({
                                "label": "Readiness Assessment",
                                "detail": f"Score: {readiness_data.get('readiness_score', 0)}% — {readiness_data.get('readiness_status')}.",
                                "severity": "ok" if (readiness_data.get("readiness_score", 0) or 0) >= 80 else "warn",
                            })
                except Exception:
                    pass

        # 3. AI Analysis records
        ai_analyses = (
            db.query(AIAnalysis)
            .filter(AIAnalysis.claim_id == claim.id)
            .all()
        )
        for ai in ai_analyses:
            atype = (ai.analysis_type or "").lower()
            score = float(ai.confidence_score or 0.0)
            if "ocr" in atype:
                ocr_confidence = score
            elif "medical" in atype and not medical_confidence:
                medical_confidence = score
            elif "policy" in atype:
                policy_confidence = score
                if isinstance(ai.analysis_result, dict):
                    if ai.analysis_result.get("policy_status"):
                        policy_status = ai.analysis_result.get("policy_status")
                    if ai.analysis_result.get("relevant_clauses"):
                        retrieved_clauses = ai.analysis_result.get("relevant_clauses")
                    if ai.analysis_result.get("relevant_exclusions"):
                        relevant_exclusions = ai.analysis_result.get("relevant_exclusions")
            elif "validation" in atype and not validation_readiness:
                validation_readiness = score
            elif "readiness" in atype and not validation_readiness:
                validation_readiness = score
            elif "confidence" in atype:
                overall_confidence = score
                confidence_calculated = True

        # 4. Document Extractions
        if documents:
            doc_ids = [d.id for d in documents]
            extractions = (
                db.query(DocumentExtraction)
                .filter(DocumentExtraction.document_id.in_(doc_ids))
                .all()
            )
            for ext in extractions:
                doc_extractions_map[str(ext.document_id)] = ext
                data = ext.extracted_data or {}
                if not hospital and data.get("hospital_name"):
                    hospital = data.get("hospital_name")
                if not patient_age and data.get("age"):
                    try:
                        patient_age = int(data.get("age"))
                    except (ValueError, TypeError):
                        pass
                if not diagnosis and data.get("diagnosis"):
                    diagnosis = data.get("diagnosis")

            conf_scores = [float(e.ocr_confidence) for e in extractions if e.ocr_confidence is not None]
            if conf_scores and not ocr_confidence:
                ocr_confidence = round(sum(conf_scores) / len(conf_scores), 2)

        # 5. Check Claim Creation history remarks for creation metadata
        creation_hist = (
            db.query(ClaimHistory)
            .filter(
                ClaimHistory.claim_id == claim.id,
                ClaimHistory.action == "Claim Created",
            )
            .first()
        )
        if creation_hist and creation_hist.remarks:
            try:
                meta = json.loads(creation_hist.remarks)
                if isinstance(meta, dict):
                    if not hospital:
                        hospital = meta.get("hospital", "")
                    if not diagnosis:
                        diagnosis = meta.get("diagnosis", "")
                    diagnosis_code = meta.get("diagnosis_code", "")
                    diagnosis_code_system = meta.get("diagnosis_code_system", "ICD-10")
                    clinical_notes = meta.get("clinical_notes", "")
            except Exception:
                pass

    # Normalize fractional confidence scores (0.0 < x <= 1.0) to percentages (0-100%)
    if 0.0 < ocr_confidence <= 1.0:
        ocr_confidence = round(ocr_confidence * 100.0, 2)
    if 0.0 < medical_confidence <= 1.0:
        medical_confidence = round(medical_confidence * 100.0, 2)
    if 0.0 < policy_confidence <= 1.0:
        policy_confidence = round(policy_confidence * 100.0, 2)

    claim_readiness_val = float(claim.readiness_score or 0)
    if claim_readiness_val > 0:
        readiness_calculated = True

    if not validation_readiness and claim_readiness_val:
        validation_readiness = claim_readiness_val
    if not overall_confidence and claim_readiness_val:
        overall_confidence = claim_readiness_val
        confidence_calculated = True

    # Routing determination
    route_reasons: List[str] = []
    if mismatches:
        route_decision = "Human Review Required"
        route_reasons.append(f"{len(mismatches)} document mismatch(es) detected across claim package")
    elif missing_docs:
        route_decision = "Human Review Required"
        route_reasons.append(f"Missing mandatory documents: {', '.join(missing_docs[:3])}")
    elif policy_status == "Relevant Exclusion Detected" or len(relevant_exclusions) > 0:
        route_decision = "Human Review Required"
        route_reasons.append(f"Potential policy exclusion flag: {', '.join(relevant_exclusions[:2]) if relevant_exclusions else policy_status}")
    elif overall_confidence < 85.0:
        route_decision = "Human Review Required"
        route_reasons.append(f"Confidence score ({overall_confidence:.1f}%) is below automated threshold (85.0%)")
    elif claim_readiness_val < 80.0:
        route_decision = "Human Review Required"
        route_reasons.append(f"Readiness score ({claim_readiness_val:.1f}%) requires manual adjudicator inspection")
    else:
        route_decision = "Auto Approval Eligible"
        route_reasons.append("All structural cross-validations, clinical terms, and policy criteria satisfied")

    # Build Document Inventory with rich metadata
    serialized_docs: List[Dict[str, Any]] = []
    field_validation_rows: List[Dict[str, Any]] = []

    for document in documents:
        ext = doc_extractions_map.get(str(document.id))
        doc_extracted_data = ext.extracted_data if ext else {}
        doc_extracted_text = ext.extracted_text if ext else ""
        doc_ocr_conf = float(ext.ocr_confidence) if (ext and ext.ocr_confidence is not None) else None
        if doc_ocr_conf and doc_ocr_conf <= 1.0:
            doc_ocr_conf = round(doc_ocr_conf * 100.0, 2)

        raw_cat = document.document_type or "unknown"
        display_cat = raw_cat.replace("_", " ").title() if raw_cat != "unknown" else "Document"

        is_failed = document.processing_status == "Failed"
        is_processing = document.processing_status in {"Pending", "Processing"}
        is_verified = document.processing_status == "Completed"

        doc_status = "Processing" if is_processing else ("Failed" if is_failed else "Verified")

        serialized_docs.append({
            "id": str(document.id),
            "fileName": document.file_name,
            "category": display_cat,
            "rawCategory": raw_cat,
            "uploadTimestamp": document.uploaded_at.isoformat() if document.uploaded_at else None,
            "pageCount": 1,
            "uploadStatus": "Uploaded",
            "ocrStatus": "Completed" if (ext and ext.extracted_text) else ("Failed" if is_failed else "Pending"),
            "extractionStatus": "Completed" if (ext and ext.extracted_data) else ("Failed" if is_failed else "Pending"),
            "ocrConfidence": doc_ocr_conf,
            "validationResult": "Accepted" if is_verified else ("Needs Correction" if is_failed else "Awaiting Review"),
            "missingFields": [],
            "extractedFields": doc_extracted_data,
            "extractedTextPreview": doc_extracted_text[:200] if doc_extracted_text else "",
            "status": doc_status,
        })

        # Generate field-level validation rows from extracted data
        if doc_extracted_data:
            if doc_extracted_data.get("patient_name"):
                name_match = doc_extracted_data.get("patient_name").strip().lower() == patient.full_name.strip().lower()
                field_validation_rows.append({
                    "field": "Patient Name",
                    "extractedValue": doc_extracted_data.get("patient_name"),
                    "sourceDocument": document.file_name,
                    "page": "1",
                    "confidence": doc_ocr_conf,
                    "validationRule": "Matches registered claim patient full name",
                    "result": "Accepted" if name_match else "Mismatch",
                    "explanation": (
                        "Name matches the claim registration field; identity is not independently verified."
                        if name_match
                        else "Document name conflicts with the claim registration field and requires human review."
                    ),
                    "conflictingValue": patient.full_name if not name_match else None,
                })

            if doc_extracted_data.get("total_amount") is not None or doc_extracted_data.get("total_charges") is not None:
                bill_amt = float(doc_extracted_data.get("total_amount") or doc_extracted_data.get("total_charges") or 0)
                diff = abs(bill_amt - float(claim.claimed_amount or 0))
                is_amt_match = diff <= 1.0
                field_validation_rows.append({
                    "field": "Total Hospital Charges",
                    "extractedValue": f"INR {bill_amt:,.2f}",
                    "sourceDocument": document.file_name,
                    "page": "1",
                    "confidence": doc_ocr_conf,
                    "validationRule": "Reconciles with claimed amount",
                    "result": "Accepted" if is_amt_match else "Mismatch",
                    "explanation": "Extracted invoice total matches entered claimed amount within rounding tolerance." if is_amt_match else f"Invoice total {bill_amt} diverges from claim claimed amount {claim.claimed_amount}",
                    "conflictingValue": f"INR {float(claim.claimed_amount):,.2f}" if not is_amt_match else None,
                })

            if doc_extracted_data.get("admission_date"):
                adm_ext = str(doc_extracted_data.get("admission_date"))
                admission_matches = adm_ext == (
                    claim.admission_date.isoformat() if claim.admission_date else ""
                )
                field_validation_rows.append({
                    "field": "Admission Date",
                    "extractedValue": adm_ext,
                    "sourceDocument": document.file_name,
                    "page": "1",
                    "confidence": doc_ocr_conf,
                    "validationRule": "Hospitalization timeline continuity",
                    "result": "Accepted" if admission_matches else "Mismatch",
                    "explanation": (
                        "Date matches the claim registration field."
                        if admission_matches
                        else "Date conflicts with the claim registration field and requires human review."
                    ),
                    "conflictingValue": None if admission_matches else claim.admission_date.isoformat(),
                })

    # Default field validation entries if no documents uploaded yet
    if not field_validation_rows:
        field_validation_rows.append({
            "field": "Patient Full Name",
            "extractedValue": patient.full_name,
            "sourceDocument": "Claim registration data",
            "page": "1",
            "confidence": None,
            "validationRule": "Required alphabetic string validation",
            "result": "Not Evaluated",
            "explanation": "No supporting identity document has been processed; identity is not independently verified.",
            "conflictingValue": None,
        })
        field_validation_rows.append({
            "field": "Insurance Policy Number",
            "extractedValue": policy.policy_number,
            "sourceDocument": "Claim registration data",
            "page": "1",
            "confidence": None,
            "validationRule": "8-13 digit strict policy identifier rule",
            "result": "Not Evaluated",
            "explanation": "Policy details are claimant-provided and have not been independently confirmed.",
            "conflictingValue": None,
        })

    # 13 Complete Pipeline Stages with status, outputs, timestamps
    stages_spec = [
        ("01 Secure Document Intake", "Intake of claim packet and cryptographic validation", "Completed" if documents else "Processing"),
        ("02 Image Preprocessing", "Noise reduction, binarization, DPI normalization & skew check", "Completed" if documents else "Pending"),
        ("03 OCR & Text Extraction", "Tesseract / PyMuPDF multi-page high accuracy text recognition", "Completed" if ocr_confidence > 0 else "Pending"),
        ("04 Document Classification", "Regex and token evidence category classification", "Completed" if documents else "Pending"),
        ("05 Information Extraction", "Entity mapping for bills, summaries, KYC, receipts", "Completed" if len(field_validation_rows) > 2 else "Pending"),
        ("06 Medical Intelligence", f"ICD-10 clinical mapping & risk scoring ({medical_risk:.0f}/100)", "Completed" if medical_confidence > 0 else "Pending"),
        ("07 Policy Intelligence (RAG)", f"Vector RAG clause verification: {policy_status}", "Completed" if policy_confidence > 0 else "Pending"),
        ("08 Validation Engine", "Structural checks, financial arithmetic & cross-doc reconciliation", "Completed" if validation_readiness > 0 else "Pending"),
        ("09 Claim Readiness Engine", f"Weighted composite score: {claim_readiness_val:.2f}%", "Completed" if readiness_calculated else "Pending"),
        ("10 Confidence Engine", f"Evidence confidence scoring ({overall_confidence:.2f}%)", "Completed" if confidence_calculated else "Pending"),
        ("11 Automated Processing / Human Review", f"Routing decision -> {route_decision}", "Completed" if claim.claim_status in {"Approved", "Rejected"} else "Processing"),
        ("12 Final Claim Decision", f"Outcome: {claim.claim_status}", "Completed" if claim.claim_status in {"Approved", "Rejected"} else "Pending"),
        ("13 Claim History", "Immutable audit trail persisted in Neon PostgreSQL", "Completed"),
    ]

    pipeline_stages = [
        {
            "stageIndex": idx + 1,
            "name": name,
            "description": desc,
            "status": st,
            "timestamp": claim.updated_at.isoformat() if (st == "Completed" and claim.updated_at) else None,
        }
        for idx, (name, desc, st) in enumerate(stages_spec)
    ]

    # Audit Trail History from Neon PostgreSQL
    claim_history_records: List[Dict[str, Any]] = []
    if db:
        hist_rows = (
            db.query(ClaimHistory)
            .filter(ClaimHistory.claim_id == claim.id)
            .order_by(ClaimHistory.created_at.desc())
            .all()
        )
        for h in hist_rows:
            actor_name = "System Automated Engine"
            if h.performed_by:
                perf_user = db.query(User).filter(User.id == h.performed_by).first()
                if perf_user:
                    actor_name = f"{perf_user.full_name} ({perf_user.role})"
            claim_history_records.append({
                "id": str(h.id),
                "action": h.action,
                "previousStatus": h.previous_status or "—",
                "newStatus": h.new_status,
                "previousStage": h.previous_stage or "—",
                "newStage": h.new_stage or "—",
                "remarks": h.remarks or "",
                "performedBy": actor_name,
                "timestamp": h.created_at.isoformat() if h.created_at else None,
            })

    audit_event_records: List[Dict[str, Any]] = []
    if db:
        audit_rows = (
            db.query(AuditEvent)
            .filter(AuditEvent.claim_id == claim.id)
            .order_by(AuditEvent.created_at.desc())
            .all()
        )
        for event in audit_rows:
            audit_event_records.append({
                "id": str(event.id),
                "eventType": event.event_type,
                "actorUserId": str(event.actor_user_id) if event.actor_user_id else None,
                "details": event.details or {},
                "timestamp": event.created_at.isoformat() if event.created_at else None,
            })

    # Claim Readiness Breakdown (Weights: Validation 35%, Medical 25%, Policy 25%, OCR 15%)
    val_contrib = round(validation_readiness * 0.35, 2)
    med_contrib = round(medical_confidence * 0.25, 2)
    pol_contrib = round(policy_confidence * 0.25, 2)
    ocr_contrib = round(ocr_confidence * 0.15, 2)

    readiness_breakdown = {
        "readinessScore": claim_readiness_val,
        "readinessStatus": (
            "Ready for Next Stage"
            if claim_readiness_val >= 80 and not mismatches
            else ("Needs Human Review" if (mismatches or claim_readiness_val > 0) else "Not Ready")
        ),
        "weights": {
            "validation": 0.35,
            "medical": 0.25,
            "policy": 0.25,
            "ocr": 0.15,
        },
        "components": {
            "validation": {"score": validation_readiness, "weight": 0.35, "contribution": val_contrib},
            "medical": {"score": medical_confidence, "weight": 0.25, "contribution": med_contrib},
            "policy": {"score": policy_confidence, "weight": 0.25, "contribution": pol_contrib},
            "ocr": {"score": ocr_confidence, "weight": 0.15, "contribution": ocr_contrib},
        },
        "warnings": mismatches + risk_indicators,
        "blockers": missing_docs,
        "explanation": (
            f"Readiness calculated at {claim_readiness_val:.2f}% using weighted aggregation. "
            f"Validation ({val_contrib}%), Medical ({med_contrib}%), Policy ({pol_contrib}%), OCR ({ocr_contrib}%)."
        ),
    }

    confidence_details = {
        "overallConfidence": overall_confidence if confidence_calculated else None,
        "confidenceLevel": "High" if overall_confidence >= 85 else ("Medium" if overall_confidence >= 70 else "Low"),
        "routeDecision": route_decision,
        "routeReasons": route_reasons,
        "componentScores": {
            "ocr": ocr_confidence,
            "medical": medical_confidence,
            "policy": policy_confidence,
            "validation": validation_readiness,
            "readiness": claim_readiness_val,
        },
        "thresholds": {"autoProcessing": 85.0, "readiness": 80.0},
    }

    return {
        "id": str(claim.id),
        "claimNumber": claim.claim_number,
        "patientName": patient.full_name,
        "patientAge": patient_age if patient_age > 0 else None,
        "hospital": hospital or "—",
        "policyNumber": policy.policy_number,
        "insuranceProvider": policy.insurance_provider,
        "diagnosis": diagnosis or "—",
        "diagnosisCode": diagnosis_code or "—",
        "diagnosisCodeSystem": diagnosis_code_system,
        "clinicalNotes": clinical_notes,
        "admissionDate": claim.admission_date.isoformat() if claim.admission_date else "—",
        "dischargeDate": claim.discharge_date.isoformat() if claim.discharge_date else "—",
        "claimedAmount": float(claim.claimed_amount or 0),
        "currency": "INR",
        "status": claim.claim_status,
        "stage": claim.current_stage,
        "readiness": claim_readiness_val if readiness_calculated else None,
        "ocrConfidence": ocr_confidence if ocr_confidence > 0 else None,
        "medicalRisk": medical_risk,
        "medicalConfidence": medical_confidence if medical_confidence > 0 else None,
        "policyConfidence": policy_confidence if policy_confidence > 0 else None,
        "validationReadiness": validation_readiness if validation_readiness > 0 else None,
        "overallConfidence": overall_confidence if confidence_calculated else None,
        "routeDecision": route_decision,
        "routeReasons": route_reasons,
        "createdAt": claim.created_at.isoformat() if claim.created_at else None,
        "updatedAt": claim.updated_at.isoformat() if claim.updated_at else None,

        # Detail sections for Claim Readiness Dashboard
        "documents": serialized_docs,
        "pipelineStages": pipeline_stages,
        "fieldValidationTable": field_validation_rows,
        "medicalEvidence": {
            "diagnosis": diagnosis,
            "diagnosisCode": diagnosis_code,
            "procedure": procedure,
            "medicalConfidence": medical_confidence,
            "medicalRiskScore": medical_risk,
            "riskIndicators": risk_indicators,
        },
        "policyEvidence": {
            "insuranceProvider": policy.insurance_provider,
            "policyNumber": policy.policy_number,
            "policyStatus": policy_status,
            "retrievalConfidence": policy_confidence,
            "retrievedClauses": retrieved_clauses,
            "relevantExclusions": relevant_exclusions,
        },
        "readinessBreakdown": readiness_breakdown,
        "confidenceDetails": confidence_details,
        "history": claim_history_records,
        "auditEvents": audit_event_records,
        "amendments": [
            {
                "id": str(amendment.id),
                "requestedChanges": amendment.requested_changes,
                "originalValues": amendment.original_values,
                "reason": amendment.reason,
                "status": amendment.status,
                "reviewNote": amendment.review_note,
                "createdAt": amendment.created_at.isoformat() if amendment.created_at else None,
                "reviewedAt": amendment.reviewed_at.isoformat() if amendment.reviewed_at else None,
            }
            for amendment in (
                db.query(ClaimAmendment)
                .filter(ClaimAmendment.claim_id == claim.id)
                .order_by(ClaimAmendment.created_at.desc())
                .all()
                if db
                else []
            )
        ],
        "findings": findings if findings else [
            {
                "label": "Pipeline Status",
                "detail": f"Claim stage: {claim.current_stage}. Status: {claim.claim_status}.",
                "severity": "ok" if claim.claim_status in {"Approved", "Ready for Submission"} else "warn",
            }
        ],
    }


# =========================================================
# CLAIMS OPERATIONAL ANALYTICS SUMMARY
# =========================================================

@router.get("/summary")
def get_claims_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_document_reader),
):
    """
    Return operational analytics summary cards directly derived from live database:
    - Total claims
    - Approved claims
    - Rejected claims
    - Pending / In Review / Under Analysis claims
    - Average readiness score
    Scoped to claimant ownership or the officer's exact TPA organization.
    """
    query = db.query(Claim)
    if user.role == "claims_officer":
        query = query.join(Policy, Claim.policy_id == Policy.id)
    query = apply_claim_scope(query, user)

    claims = query.all()
    total = len(claims)
    approved = sum(1 for c in claims if c.claim_status == "Approved")
    rejected = sum(1 for c in claims if c.claim_status == "Rejected")
    awaiting_information = sum(
        1 for c in claims if "Additional Info Requested" in (c.current_stage or "")
    )
    escalated = sum(1 for c in claims if "Escalated" in (c.current_stage or ""))
    pending_review = sum(
        1 for c in claims
        if c.claim_status in {"Needs Review", "Under Analysis"}
        and "Additional Info Requested" not in (c.current_stage or "")
        and "Escalated" not in (c.current_stage or "")
    )
    pending = total - approved - rejected
    avg_readiness = (
        round(float(sum((c.readiness_score or 0) for c in claims)) / total, 1)
        if total > 0
        else 0.0
    )

    return {
        "totalClaims": total,
        "approvedClaims": approved,
        "rejectedClaims": rejected,
        "pendingClaims": pending,
        "pendingReviewClaims": pending_review,
        "awaitingInformationClaims": awaiting_information,
        "escalatedClaims": escalated,
        "averageReadinessScore": avg_readiness,
    }


@router.get("/analytics")
def get_claims_analytics(
    db: Session = Depends(get_db),
    user: User = Depends(require_claims_officer),
):
    rows = (
        apply_claim_scope(
            db.query(Claim, Policy).join(Policy, Claim.policy_id == Policy.id),
            user,
        )
        .order_by(Claim.created_at.asc())
        .all()
    )
    claims = [claim for claim, _policy in rows]
    claim_ids = [claim.id for claim in claims]
    decisions = {
        "Approved": sum(1 for claim in claims if claim.claim_status == "Approved"),
        "Rejected": sum(1 for claim in claims if claim.claim_status == "Rejected"),
        "Awaiting Information": sum(
            1 for claim in claims
            if "Additional Info Requested" in (claim.current_stage or "")
        ),
        "Escalated": sum(
            1 for claim in claims if "Escalated" in (claim.current_stage or "")
        ),
        "Pending Review": sum(
            1 for claim in claims
            if claim.claim_status in {"Needs Review", "Under Analysis"}
            and "Additional Info Requested" not in (claim.current_stage or "")
            and "Escalated" not in (claim.current_stage or "")
        ),
    }

    history_rows = (
        db.query(ClaimHistory)
        .filter(ClaimHistory.claim_id.in_(claim_ids))
        .all()
        if claim_ids
        else []
    )
    completed_at = {}
    for event in history_rows:
        if event.new_status in {"Approved", "Rejected"} and event.created_at:
            completed_at.setdefault(event.claim_id, event.created_at)

    elapsed_days = [
        (completed_at[claim.id] - claim.created_at).total_seconds() / 86400
        for claim in claims
        if claim.id in completed_at and claim.created_at
    ]

    verification_rows = (
        db.query(VerificationResult)
        .filter(VerificationResult.claim_id.in_(claim_ids))
        .all()
        if claim_ids
        else []
    )
    discrepancy_counts: Dict[str, int] = {}
    for verification in verification_rows:
        for mismatch in verification.mismatches or []:
            if isinstance(mismatch, dict):
                label = str(
                    mismatch.get("field")
                    or mismatch.get("type")
                    or mismatch.get("label")
                    or "Uncategorized discrepancy"
                )
            else:
                label = str(mismatch).strip() or "Uncategorized discrepancy"
            discrepancy_counts[label] = discrepancy_counts.get(label, 0) + 1

    readiness_events = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.claim_id.in_(claim_ids),
            AuditEvent.event_type == "document_processing_completed",
        )
        .all()
        if claim_ids
        else []
    )
    trend_values: Dict[str, List[float]] = {}
    for event in readiness_events:
        score = (event.details or {}).get("readiness_score")
        if event.created_at and isinstance(score, (int, float)):
            month = event.created_at.strftime("%Y-%m")
            trend_values.setdefault(month, []).append(float(score))

    return {
        "totalClaims": len(claims),
        "pendingReview": decisions["Pending Review"],
        "approved": decisions["Approved"],
        "rejected": decisions["Rejected"],
        "awaitingInformation": decisions["Awaiting Information"],
        "escalated": decisions["Escalated"],
        "averageProcessingTimeDays": (
            round(sum(elapsed_days) / len(elapsed_days), 2)
            if elapsed_days
            else None
        ),
        "decisionDistribution": decisions,
        "commonDiscrepancies": [
            {"category": category, "count": count}
            for category, count in sorted(
                discrepancy_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        "readinessTrends": [
            {
                "month": month,
                "averageReadiness": round(sum(scores) / len(scores), 2),
                "processedClaims": len(scores),
            }
            for month, scores in sorted(trend_values.items())
        ],
    }


# =========================================================
# GET ALL CLAIMS (SCOPED BY ORGANIZATION)
# =========================================================

@router.get("")
def get_claims(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(require_document_reader),
):
    """
    Return claims scoped to claimant ownership or exact TPA organization.
    """
    query = (
        db.query(Claim, Patient, Policy)
        .join(Patient, Claim.patient_id == Patient.id)
        .join(Policy, Claim.policy_id == Policy.id)
    )

    query = apply_claim_scope(query, user)

    # 2. Status filter
    if status_filter and status_filter.lower() != "all":
        query = query.filter(Claim.claim_status == status_filter)

    # 3. Search filter
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Claim.claim_number.ilike(search_pattern),
                Patient.full_name.ilike(search_pattern),
                Policy.policy_number.ilike(search_pattern),
                Claim.hospital_name.ilike(search_pattern),
            )
        )

    rows = query.order_by(Claim.created_at.desc()).all()

    result = []
    for claim, patient, policy in rows:
        result.append(
            serialize_claim(
                claim=claim,
                patient=patient,
                policy=policy,
                documents=[],
                db=db,
                detailed=False,
            )
        )

    return result


# =========================================================
# GET SINGLE CLAIM (UUID OR CLAIM NUMBER)
# =========================================================

@router.get("/{claim_id}")
def get_claim(
    claim_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_document_reader),
):
    """
    Return one comprehensive claim using its UUID OR human-readable claim_number.
    Enforces hospital/TPA organization access boundaries.
    """
    claim = None

    # 1. Try UUID lookup first
    try:
        claim_uuid = uuid.UUID(claim_id)
        claim = db.query(Claim).filter(Claim.id == claim_uuid).first()
    except ValueError:
        pass

    # 2. Fall back to claim_number lookup (case-insensitive)
    if not claim:
        claim = db.query(Claim).filter(Claim.claim_number.ilike(claim_id.strip())).first()

    if not claim:
        raise HTTPException(
            status_code=404,
            detail=f"Claim '{claim_id}' was not found in active workspace.",
        )

    patient = db.query(Patient).filter(Patient.id == claim.patient_id).first()
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()

    if not patient or not policy:
        raise HTTPException(
            status_code=500,
            detail="Claim relationships are incomplete in database.",
        )

    # 3. Enforce Server-Side Authorization Boundary
    if not check_claim_access(claim, policy, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This claim is outside your authorized organization.",
        )

    documents = db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim.id).all()

    return serialize_claim(
        claim=claim,
        patient=patient,
        policy=policy,
        documents=documents,
        db=db,
        detailed=True,
    )


# =========================================================
# CREATE CLAIM
# =========================================================

@router.post("")
def create_claim(
    claim_data: CreateClaimRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_claimant),
):
    """
    Create a new Claim, Patient, Policy, and initial ClaimHistory record.
    Associates the claim only with the authenticated claimant.
    """
    try:
        # 1. Patient full name
        patient_name = (claim_data.patientName or "").strip()
        if not patient_name:
            raise HTTPException(status_code=422, detail="Patient full name is required.")
        if any(ch.isdigit() for ch in patient_name):
            raise HTTPException(status_code=422, detail="Patient full name must not contain numbers.")
        if not re.match(r"^[\w\s'\-.]+$", patient_name, re.UNICODE) or re.search(r"[_]", patient_name):
            raise HTTPException(status_code=422, detail="Patient full name contains invalid characters.")
        if len(patient_name) < 2:
            raise HTTPException(status_code=422, detail="Patient full name must be at least 2 characters.")
        if len(patient_name) > 100:
            raise HTTPException(status_code=422, detail="Patient full name cannot exceed 100 characters.")

        # 2. Patient age
        if claim_data.patientAge is None or claim_data.patientAge < 0 or claim_data.patientAge > 120:
            raise HTTPException(status_code=422, detail="Patient age must be between 0 and 120 years.")

        # 3. Hospital name
        hospital_name = (claim_data.hospital or "").strip()
        if not hospital_name:
            raise HTTPException(status_code=422, detail="Hospital / provider name is required.")
        if len(hospital_name) < 2 or len(hospital_name) > 150:
            raise HTTPException(status_code=422, detail="Hospital / provider name must be between 2 and 150 characters.")

        # 4. Policy number (strictly 8-13 digits)
        policy_num = str(claim_data.policyNumber or "").strip()
        if not policy_num:
            raise HTTPException(status_code=422, detail="Policy number is required.")
        if not re.match(r"^\d{8,13}$", policy_num):
            raise HTTPException(status_code=422, detail="Policy number must be between 8 and 13 digits containing only numbers.")

        # 5. Insurance provider
        provider_name = (claim_data.insuranceProvider or "").strip()
        if not provider_name:
            raise HTTPException(status_code=422, detail="Insurance provider / TPA is required.")

        # 6. Claimed amount
        try:
            claimed_val = float(claim_data.claimedAmount)
        except (ValueError, TypeError):
            raise HTTPException(status_code=422, detail="Claimed amount must be a valid positive number.")
        if not (math.isfinite(claimed_val) and claimed_val > 0):
            raise HTTPException(status_code=422, detail="Claimed amount must be greater than 0.")
        if claimed_val > 100_000_000:
            raise HTTPException(status_code=422, detail="Claimed amount exceeds the permissible limit.")

        # 7. Dates
        if not claim_data.admissionDate or not claim_data.dischargeDate:
            raise HTTPException(status_code=422, detail="Both admission date and discharge date are required.")
        adm_date = parse_date(claim_data.admissionDate)
        dis_date = parse_date(claim_data.dischargeDate)
        if adm_date > dis_date:
            raise HTTPException(status_code=422, detail="Admission date cannot be after discharge date.")

        # 8. Diagnosis
        diag_text = (claim_data.diagnosis or "").strip()
        if not diag_text:
            raise HTTPException(status_code=422, detail="Clinical diagnosis selection or description is required.")

        # Find or create Patient
        dob = date(date.today().year - claim_data.patientAge, 1, 1) if claim_data.patientAge > 0 else None
        patient = db.query(Patient).filter(Patient.full_name == patient_name).first()
        if not patient:
            patient = Patient(full_name=patient_name, date_of_birth=dob)
            db.add(patient)
            db.flush()
        elif dob and not patient.date_of_birth:
            patient.date_of_birth = dob
            db.flush()

        # Find or create Policy
        policy = db.query(Policy).filter(Policy.policy_number == policy_num).first()
        if not policy:
            policy = Policy(policy_number=policy_num, insurance_provider=provider_name)
            db.add(policy)
            db.flush()
        claim_num = generate_claim_number()

        # Create Claim with hospital_name
        claim_kwargs = {
            "claim_number": claim_num,
            "patient_id": patient.id,
            "policy_id": policy.id,
            "hospital_name": hospital_name,
            "admission_date": adm_date,
            "discharge_date": dis_date,
            "claimed_amount": Decimal(str(claimed_val)),
            "claim_status": "Under Analysis",
            "current_stage": "01 Secure Document Intake",
            "readiness_score": Decimal("0"),
            "created_by": user.id,
        }
        claim = Claim(**claim_kwargs)
        db.add(claim)
        db.flush()

        # Record initial claim history entry in Neon PostgreSQL
        creation_remarks = {
            "hospital": hospital_name,
            "diagnosis": diag_text,
            "diagnosis_code": (claim_data.diagnosisCode or "").strip(),
            "diagnosis_code_system": (claim_data.diagnosisCodeSystem or "ICD-10").strip(),
            "clinical_notes": (claim_data.clinicalNotes or "").strip(),
            "stage": "01 Secure Document Intake",
        }
        history_entry = ClaimHistory(
            claim_id=claim.id,
            previous_status=None,
            new_status=claim.claim_status,
            previous_stage=None,
            new_stage=claim.current_stage,
            action="Claim Created",
            remarks=json.dumps(creation_remarks),
            performed_by=user.id,
        )
        db.add(history_entry)
        db.add(
            AuditEvent(
                event_type="claim_created",
                actor_user_id=user.id,
                claim_id=claim.id,
                details={"claim_number": claim.claim_number},
            )
        )

        db.commit()

        return {
            "id": str(claim.id),
            "claimNumber": claim.claim_number,
            "patientName": patient.full_name,
            "hospital": claim.hospital_name,
            "policyNumber": policy.policy_number,
            "insuranceProvider": policy.insurance_provider,
            "status": claim.claim_status,
            "stage": claim.current_stage,
            "readiness": float(claim.readiness_score or 0),
            "message": "Claim created successfully.",
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Claim creation failed.")


# =========================================================
# TPA REVIEW QUEUE (RESTRICTED TO TPA REVIEWERS)
# =========================================================

@router.get("/tpa/review-queue")
def get_tpa_review_queue(
    queue_filter: str = Query("pending_review"),  # pending_review, low_confidence, validation_mismatch, missing_documents, policy_review_required, info_requested, escalated, all
    hospital_filter: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None, max_length=150),
    db: Session = Depends(get_db),
    user: User = Depends(require_claims_officer),
):
    """
    TPA Review Queue for authorized reviewers.
    Scoped strictly to the reviewer's assigned TPA / Insurance Provider.
    Distinguishes 0% confidence from uncalculated confidence.
    """
    query = (
        db.query(Claim, Patient, Policy)
        .join(Patient, Claim.patient_id == Patient.id)
        .join(Policy, Claim.policy_id == Policy.id)
    )

    # Organization scoping
    query = apply_claim_scope(query, user)

    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Claim.claim_number.ilike(search_pattern),
                Patient.full_name.ilike(search_pattern),
                Claim.hospital_name.ilike(search_pattern),
                Policy.policy_number.ilike(search_pattern),
            )
        )

    if hospital_filter:
        query = query.filter(Claim.hospital_name.ilike(f"%{hospital_filter}%"))

    if status_filter:
        query = query.filter(Claim.claim_status == status_filter)

    rows = query.order_by(Claim.created_at.desc()).all()
    if not rows:
        return []

    claim_ids = [c.id for c, _, _ in rows]

    # Batch pre-fetch VerificationResult and AIAnalysis in 2 queries instead of 200
    verifications = {
        v.claim_id: v
        for v in db.query(VerificationResult)
        .filter(VerificationResult.claim_id.in_(claim_ids))
        .all()
    }
    ai_confidences = {
        ai.claim_id: ai
        for ai in db.query(AIAnalysis)
        .filter(
            AIAnalysis.claim_id.in_(claim_ids),
            AIAnalysis.analysis_type == "Confidence",
        )
        .all()
    }
    pending_amendments = {
        amendment.claim_id
        for amendment in db.query(ClaimAmendment)
        .filter(
            ClaimAmendment.claim_id.in_(claim_ids),
            ClaimAmendment.status == "Pending",
        )
        .all()
    }

    queue_items = []
    for claim, patient, policy in rows:
        # Check VerificationResult and AI analysis for queue routing flags
        verification = verifications.get(claim.id)
        mismatches = verification.mismatches if (verification and verification.mismatches) else []
        missing_docs = verification.missing_documents if (verification and verification.missing_documents) else []

        ai_confidence = ai_confidences.get(claim.id)
        conf_score = (
            float(ai_confidence.confidence_score)
            if (ai_confidence and ai_confidence.confidence_score is not None)
            else None
        )
        readiness_score = float(claim.readiness_score or 0)

        # Determine why it entered review
        reasons = []
        if claim.id in pending_amendments:
            reasons.append("Pending claimant amendment requires review")
        if claim.claim_status == "Needs Review":
            reasons.append("Claim flagged for adjudicator review")
        if mismatches:
            reasons.append(f"{len(mismatches)} document cross-validation mismatch(es)")
        if missing_docs:
            reasons.append(f"Missing mandatory documents: {', '.join(missing_docs[:2])}")
        if conf_score is not None and conf_score < 85.0:
            reasons.append(f"Evidence confidence ({conf_score:.1f}%) below 85% threshold")
        elif conf_score is None and readiness_score > 0 and readiness_score < 80.0:
            reasons.append(f"Readiness score ({readiness_score:.1f}%) requires manual check")

        # Apply queue filter
        include = True
        if queue_filter == "pending_review":
            include = (
                claim.claim_status in {"Needs Review", "Under Analysis"}
                and len(reasons) > 0
            )
        elif queue_filter == "low_confidence":
            include = conf_score is not None and conf_score < 85.0
        elif queue_filter == "validation_mismatch":
            include = len(mismatches) > 0
        elif queue_filter == "missing_documents":
            include = len(missing_docs) > 0
        elif queue_filter == "info_requested":
            include = "Additional Information Requested" in (claim.current_stage or "") or claim.claim_status == "Needs Review"
        elif queue_filter == "escalated":
            include = "Escalated" in (claim.current_stage or "") or "Escalate" in (claim.claim_status or "")
        elif queue_filter == "approved":
            include = claim.claim_status == "Approved"
        elif queue_filter == "rejected":
            include = claim.claim_status == "Rejected"

        if include:
            queue_items.append({
                "id": str(claim.id),
                "claimNumber": claim.claim_number,
                "patientName": patient.full_name,
                "hospital": claim.hospital_name or "—",
                "policyNumber": policy.policy_number,
                "insuranceProvider": policy.insurance_provider,
                "claimedAmount": float(claim.claimed_amount or 0),
                "status": claim.claim_status,
                "stage": claim.current_stage,
                "readiness": readiness_score,
                "confidenceScore": conf_score,
                "confidenceCalculated": conf_score is not None,
                "reasons": reasons if reasons else ["Awaiting manual adjudicator review"],
                "createdAt": claim.created_at.isoformat() if claim.created_at else None,
            })

    return queue_items


# =========================================================
# TPA DECISION: APPROVE / REJECT / ESCALATE / REQUEST INFO
# (RESTRICTED TO AUTHORIZED TPA REVIEWERS)
# =========================================================

@router.patch("/{claim_id}/status")
def update_claim_status(
    claim_id: str,
    status_data: UpdateClaimStatusRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_claims_officer),
):
    """
    Execute an official TPA adjudicator decision.
    Strictly restricted to organization-authorized claims officers.
    Persists status change and auditable ClaimHistory entry to Neon PostgreSQL.
    """
    claim = None
    try:
        claim_uuid = uuid.UUID(claim_id)
        claim = db.query(Claim).filter(Claim.id == claim_uuid).first()
    except ValueError:
        pass

    if not claim:
        claim = db.query(Claim).filter(Claim.claim_number.ilike(claim_id.strip())).first()

    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")

    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    if not policy:
        raise HTTPException(status_code=500, detail="Claim policy relationship missing.")

    if not check_claim_access(claim, policy, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This claim is outside your authorized TPA scope.",
        )

    action = status_data.action

    if not status_data.note or not status_data.note.strip():
        raise HTTPException(
            status_code=400,
            detail="A decision reason is required for every review action.",
        )
    if claim.claim_status in {"Approved", "Rejected"}:
        raise HTTPException(
            status_code=409,
            detail="A final decision has already been recorded for this claim.",
        )
    pending_amendment = (
        db.query(ClaimAmendment)
        .filter(
            ClaimAmendment.claim_id == claim.id,
            ClaimAmendment.status == "Pending",
        )
        .first()
    )
    if pending_amendment and status_data.action in {"Approve", "Reject"}:
        raise HTTPException(
            status_code=409,
            detail="Review the pending claimant amendment before recording a final decision.",
        )
    if action == "RequestInfo" and not status_data.requestedDocuments:
        raise HTTPException(
            status_code=422,
            detail="Specify the additional evidence or information required.",
        )
    if action == "Escalate" and not (status_data.destination or "").strip():
        raise HTTPException(
            status_code=422,
            detail="Specify the escalation destination.",
        )

    if action == "Approve":
        if claim.claim_status == "Approved":
            raise HTTPException(status_code=400, detail="Claim is already in Approved status.")

    action_map = {
        "Approve": "Approved",
        "Reject": "Rejected",
        "RequestInfo": "Needs Review",
        "Escalate": "Needs Review",
    }

    new_status = action_map.get(action)
    if not new_status:
        raise HTTPException(
            status_code=400,
            detail="Unsupported action. Must be Approve, Reject, RequestInfo, or Escalate.",
        )

    previous_status = claim.claim_status
    previous_stage = claim.current_stage

    # Apply status and stage updates
    claim.claim_status = new_status
    if action in {"Approve", "Reject"}:
        claim.current_stage = "11 Final Decision"
    elif action == "RequestInfo":
        claim.current_stage = "10 Needs Review — Additional Info Requested"
    elif action == "Escalate":
        claim.current_stage = "10 Needs Review — Escalated to Senior Adjudicator"

    # Persist ClaimHistory audit record in Neon PostgreSQL
    remarks_text = status_data.note.strip()
    if status_data.policyReference:
        remarks_text += f" | Policy Ref: {status_data.policyReference}"
    if status_data.destination:
        remarks_text += f" | Escalation Destination: {status_data.destination}"
    if status_data.requestedDocuments:
        remarks_text += " | Requested: " + ", ".join(status_data.requestedDocuments)

    history_entry = ClaimHistory(
        claim_id=claim.id,
        previous_status=previous_status,
        new_status=claim.claim_status,
        previous_stage=previous_stage,
        new_stage=claim.current_stage,
        action=action,
        remarks=remarks_text,
        performed_by=user.id,
    )
    db.add(history_entry)
    db.add(
        AuditEvent(
            event_type=f"claim_{action.lower()}",
            actor_user_id=user.id,
            claim_id=claim.id,
            details={
                "action": action,
                "previous_status": previous_status,
                "new_status": claim.claim_status,
                "requested_documents": status_data.requestedDocuments or [],
            },
        )
    )

    db.commit()
    db.refresh(claim)

    return {
        "success": True,
        "claimId": str(claim.id),
        "claimNumber": claim.claim_number,
        "previousStatus": previous_status,
        "newStatus": claim.claim_status,
        "newStage": claim.current_stage,
        "action": action,
        "adjudicator": user.full_name,
        "note": status_data.note,
    }


@router.get("/{claim_id}/amendments")
def get_claim_amendments(
    claim_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_document_reader),
):
    claim = _get_claim_by_identifier(db, claim_id)
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    if not policy or not check_claim_access(claim, policy, user):
        raise HTTPException(status_code=403, detail="This claim is outside your authorized scope.")

    amendments = (
        db.query(ClaimAmendment)
        .filter(ClaimAmendment.claim_id == claim.id)
        .order_by(ClaimAmendment.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(amendment.id),
            "requestedChanges": amendment.requested_changes,
            "originalValues": amendment.original_values,
            "reason": amendment.reason,
            "status": amendment.status,
            "reviewNote": amendment.review_note,
            "createdAt": amendment.created_at.isoformat() if amendment.created_at else None,
            "reviewedAt": amendment.reviewed_at.isoformat() if amendment.reviewed_at else None,
        }
        for amendment in amendments
    ]


@router.post("/{claim_id}/amendments", status_code=status.HTTP_201_CREATED)
def request_claim_amendment(
    claim_id: str,
    amendment_data: ClaimAmendmentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_claimant),
):
    claim = _get_claim_by_identifier(db, claim_id)
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    if not policy or not check_claim_access(claim, policy, user):
        raise HTTPException(status_code=403, detail="This claim is outside your authorized scope.")
    if claim.claim_status in {"Approved", "Rejected"}:
        raise HTTPException(status_code=409, detail="Finalized claims cannot be amended.")
    if not amendment_data.reason.strip():
        raise HTTPException(status_code=422, detail="An amendment reason is required.")

    allowed_fields = {
        "patientName",
        "hospital",
        "admissionDate",
        "dischargeDate",
        "claimedAmount",
    }
    changes = amendment_data.changes
    if not changes or not set(changes).issubset(allowed_fields):
        raise HTTPException(
            status_code=422,
            detail="Amendments may change only patientName, hospital, admissionDate, dischargeDate, or claimedAmount.",
        )

    patient = db.query(Patient).filter(Patient.id == claim.patient_id).first()
    if not patient:
        raise HTTPException(status_code=500, detail="Claim patient relationship is incomplete.")
    original_values: Dict[str, Any] = {
        "patientName": patient.full_name,
        "hospital": claim.hospital_name,
        "admissionDate": claim.admission_date.isoformat() if claim.admission_date else None,
        "dischargeDate": claim.discharge_date.isoformat() if claim.discharge_date else None,
        "claimedAmount": float(claim.claimed_amount),
    }

    normalized_changes: Dict[str, Any] = {}
    for key, value in changes.items():
        if key in {"patientName", "hospital"}:
            text_value = str(value).strip()
            if not text_value or len(text_value) > 150:
                raise HTTPException(status_code=422, detail=f"{key} must contain 1 to 150 characters.")
            normalized_changes[key] = text_value
        elif key in {"admissionDate", "dischargeDate"}:
            parsed_date = parse_date(str(value))
            normalized_changes[key] = parsed_date.isoformat() if parsed_date else None
        else:
            try:
                amount = float(value)
            except (TypeError, ValueError):
                raise HTTPException(status_code=422, detail="claimedAmount must be a positive number.")
            if not math.isfinite(amount) or amount <= 0 or amount > 100_000_000:
                raise HTTPException(status_code=422, detail="claimedAmount must be a positive valid amount.")
            normalized_changes[key] = amount

    admission_value = normalized_changes.get("admissionDate", original_values["admissionDate"])
    discharge_value = normalized_changes.get("dischargeDate", original_values["dischargeDate"])
    if (
        admission_value
        and discharge_value
        and date.fromisoformat(admission_value) > date.fromisoformat(discharge_value)
    ):
        raise HTTPException(status_code=422, detail="Admission date cannot be after discharge date.")

    pending = (
        db.query(ClaimAmendment)
        .filter(
            ClaimAmendment.claim_id == claim.id,
            ClaimAmendment.status == "Pending",
        )
        .first()
    )
    if pending:
        raise HTTPException(status_code=409, detail="A claim amendment is already awaiting review.")

    amendment = ClaimAmendment(
        claim_id=claim.id,
        requested_by=user.id,
        requested_changes=normalized_changes,
        original_values=original_values,
        reason=amendment_data.reason.strip(),
        status="Pending",
    )
    db.add(amendment)
    db.flush()
    db.add(
        AuditEvent(
            event_type="claim_amendment_requested",
            actor_user_id=user.id,
            claim_id=claim.id,
            details={"amendment_id": str(amendment.id), "fields": sorted(normalized_changes)},
        )
    )
    db.commit()
    return {
        "id": str(amendment.id),
        "status": amendment.status,
        "requestedChanges": amendment.requested_changes,
        "originalValues": amendment.original_values,
    }


@router.patch("/amendments/{amendment_id}")
def review_claim_amendment(
    amendment_id: str,
    decision_data: ClaimAmendmentDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_claims_officer),
):
    try:
        amendment_uuid = uuid.UUID(amendment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid amendment ID.")
    amendment = (
        db.query(ClaimAmendment)
        .filter(ClaimAmendment.id == amendment_uuid)
        .with_for_update()
        .first()
    )
    if not amendment:
        raise HTTPException(status_code=404, detail="Claim amendment not found.")
    claim = db.query(Claim).filter(Claim.id == amendment.claim_id).first()
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first() if claim else None
    if not claim or not policy or not check_claim_access(claim, policy, user):
        raise HTTPException(status_code=403, detail="This amendment is outside your authorized TPA scope.")
    if amendment.status != "Pending":
        raise HTTPException(status_code=409, detail="This amendment has already been reviewed.")
    if not decision_data.note.strip():
        raise HTTPException(status_code=422, detail="A review reason is required.")

    if decision_data.decision == "Approve":
        patient = db.query(Patient).filter(Patient.id == claim.patient_id).first()
        if not patient:
            raise HTTPException(status_code=500, detail="Claim patient relationship is incomplete.")
        changes = amendment.requested_changes
        if "patientName" in changes:
            patient.full_name = changes["patientName"]
        if "hospital" in changes:
            claim.hospital_name = changes["hospital"]
        if "admissionDate" in changes:
            claim.admission_date = date.fromisoformat(changes["admissionDate"])
        if "dischargeDate" in changes:
            claim.discharge_date = date.fromisoformat(changes["dischargeDate"])
        if "claimedAmount" in changes:
            claim.claimed_amount = Decimal(str(changes["claimedAmount"]))
        amendment.status = "Approved"
    else:
        amendment.status = "Rejected"

    now = datetime.utcnow()
    amendment.reviewed_by = user.id
    amendment.review_note = decision_data.note.strip()
    amendment.reviewed_at = now
    db.add(
        ClaimHistory(
            claim_id=claim.id,
            previous_status=claim.claim_status,
            new_status=claim.claim_status,
            previous_stage=claim.current_stage,
            new_stage=claim.current_stage,
            action=f"Claim Amendment {amendment.status}",
            remarks=amendment.review_note,
            performed_by=user.id,
        )
    )
    db.add(
        AuditEvent(
            event_type=f"claim_amendment_{amendment.status.lower()}",
            actor_user_id=user.id,
            claim_id=claim.id,
            details={"amendment_id": str(amendment.id), "fields": sorted(amendment.requested_changes)},
        )
    )
    db.commit()
    return {
        "id": str(amendment.id),
        "status": amendment.status,
        "reviewNote": amendment.review_note,
    }


# =========================================================
# HOSPITAL ACTION: RESPOND TO TPA INFORMATION REQUEST
# (ALLOWED FOR HOSPITAL COORDINATORS)
# =========================================================

@router.post("/{claim_id}/respond-info")
def hospital_respond_info(
    claim_id: str,
    response_data: HospitalResponseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_claimant),
):
    """
    Claimant submits a response to a TPA information request.
    Updates claim status back to Under Analysis / Hospital Response Submitted.
    """
    claim = None
    try:
        claim_uuid = uuid.UUID(claim_id)
        claim = db.query(Claim).filter(Claim.id == claim_uuid).first()
    except ValueError:
        pass

    if not claim:
        claim = db.query(Claim).filter(Claim.claim_number.ilike(claim_id.strip())).first()

    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")

    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    if not policy or not check_claim_access(claim, policy, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This claim is outside your authorized hospital scope.",
        )

    previous_status = claim.claim_status
    previous_stage = claim.current_stage

    claim.claim_status = "Under Analysis"
    claim.current_stage = "08 Cross-Validation Engine — Hospital Response Received"

    remarks = f"Hospital Coordinator Response: {response_data.notes}"
    if response_data.submittedDocuments:
        remarks += f" | Attached Documents: {', '.join(response_data.submittedDocuments)}"

    history_entry = ClaimHistory(
        claim_id=claim.id,
        previous_status=previous_status,
        new_status=claim.claim_status,
        previous_stage=previous_stage,
        new_stage=claim.current_stage,
        action="Hospital Response Submitted",
        remarks=remarks,
        performed_by=user.id,
    )
    db.add(history_entry)
    db.add(
        AuditEvent(
            event_type="claim_information_submitted",
            actor_user_id=user.id,
            claim_id=claim.id,
            details={"submitted_document_count": len(response_data.submittedDocuments or [])},
        )
    )

    db.commit()
    db.refresh(claim)

    return {
        "success": True,
        "claimId": str(claim.id),
        "newStatus": claim.claim_status,
        "newStage": claim.current_stage,
        "message": "Response submitted to TPA review queue successfully.",
    }