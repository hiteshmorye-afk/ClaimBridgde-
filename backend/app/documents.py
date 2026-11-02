from datetime import date, datetime
import json
import logging
import shutil
import concurrent.futures
import uuid
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from pydantic import BaseModel

from .auth import (
    require_document_reader,
    require_claimant,
    canonical_role_name,
)
from .claims import apply_claim_scope, check_claim_access
from .database import get_db, SessionLocal
from .models import (
    AIAnalysis,
    AuditEvent,
    Claim,
    ClaimDocument,
    DocumentExtraction,
    InsuranceProvider,
    MedicalAnalysis,
    Patient,
    PatientConsent,
    Policy,
    User,
    VerificationResult,
)
from .pipeline import process_document
from .validation_engine import validate_cross_document_consistency
from .document_reliability import calculate_document_reliability
from .document_classifier import normalize_category_name
from .claim_readiness_engine import calculate_explainable_claim_readiness

logger = logging.getLogger(__name__)

pipeline_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=3,
    thread_name_prefix="claimbridge_pipeline_worker",
)


def safe_decimal(val, default=0.0) -> Decimal:
    if val is None:
        return Decimal(str(default))
    if isinstance(val, (int, float, Decimal)):
        return Decimal(str(val))
    if isinstance(val, str):
        cleaned = val.replace("%", "").strip()
        try:
            return Decimal(cleaned)
        except Exception:
            return Decimal(str(default))
    return Decimal(str(default))


COMPATIBLE_CATEGORIES = {
    "identity_proof": {"identity_proof", "aadhaar", "pan", "passport", "voter_id", "kyc"},
    "insurance_card": {"insurance_card", "insurance_policy", "policy_schedule", "health_card"},
    "claim_form": {"claim_form", "part_a", "part_b", "duly_filled_claim_form"},
    "consultation_letter": {"consultation_letter", "prescription", "opd_slip", "referral_letter"},
    "diagnostic_report": {"diagnostic_report", "lab_report", "investigation_report", "pathology_report", "radiology_report"},
    "hospital_bill": {"hospital_bill", "final_hospital_bill", "bill", "invoice"},
    "discharge_summary": {"discharge_summary", "discharge_card"},
    "payment_receipt": {"payment_receipt", "receipt", "advance_receipt"},
    "pharmacy_bill": {"pharmacy_bill", "medical_store_bill"},
    "fir_mlc": {"fir_mlc", "fir", "mlc"},
    "implant_invoice": {"implant_invoice", "implant_sticker"},
    "ambulance_receipt": {"ambulance_receipt", "ambulance_certificate"},
    "pre_authorization": {"pre_authorization", "pre_auth_form", "pre_auth_approval"},
    "other_medical_doc": {"other_medical_doc", "medical_report", "consent_form"},
}

CATEGORY_DISPLAY_NAMES = {
    "identity_proof": "Aadhaar / Identity Proof",
    "insurance_card": "Health Insurance Card / Policy",
    "claim_form": "Duly Filled Claim Form",
    "consultation_letter": "Doctor's Prescription & Consultation",
    "diagnostic_report": "Diagnostic & Investigation Reports",
    "hospital_bill": "Final Hospital Bill",
    "discharge_summary": "Discharge Summary",
    "payment_receipt": "Payment Receipt",
    "pharmacy_bill": "Pharmacy Bill",
    "fir_mlc": "Medico-Legal Certificate / FIR",
    "implant_invoice": "Implant Invoice & Sticker",
    "ambulance_receipt": "Ambulance Receipt",
    "pre_authorization": "Pre-Authorization Form / Admission Notes",
    "other_medical_doc": "Patient Consent Form / Supporting Medical Document",
}

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


# =========================================================
# PATHS
# =========================================================

BACKEND_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BACKEND_DIR / "uploads"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

POLICY_PATH = (
    BACKEND_DIR
    / "policies"
    / "sample_policy.txt"
)


# =========================================================
# ALLOWED FILE TYPES
# =========================================================

ALLOWED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
}


# =========================================================
# LIST DOCUMENTS (SCOPED BY ORGANIZATION)
# =========================================================

def check_document_access(document: ClaimDocument, claim: Optional[Claim], policy: Optional[Policy], user: User) -> bool:
    """Verify authorized document access respecting admin, claimant owner, hospital, and TPA scope."""
    if not user:
        return False
    role = canonical_role_name(user.role)
    if role == "admin":
        return True

    if not claim:
        return True

    if role == "claimant":
        if claim.created_by == user.id:
            return True
        raw_role = (user.role or "").strip().lower()
        if raw_role in {"hospital_coordinator", "coordinator", "hospital coordinator"}:
            if (user.organization or "").strip() and (claim.hospital_name or "").strip():
                return user.organization.strip().casefold() in claim.hospital_name.strip().casefold()
        return False

    if role in ("claim_officer", "claims_officer", "tpa_reviewer"):
        user_org = (user.organization or "").strip().casefold()
        insurer = ((policy.insurance_provider if policy else getattr(claim, "insurance_provider", None)) or "").strip().casefold()
        return bool(user_org and insurer and user_org == insurer)

    return False

@router.get("")
def list_documents(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    claim_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_document_reader),
):
    """
    List uploaded documents with organization-level scoping:
    - Hospital coordinators only see documents of their hospital.
    - TPA reviewers only see documents of their assigned insurance provider.
    - Admins see all documents.
    """
    query = (
        db.query(ClaimDocument, Claim, Policy)
        .outerjoin(Claim, ClaimDocument.claim_id == Claim.id)
        .outerjoin(Policy, Claim.policy_id == Policy.id)
    )
    normalized_role = canonical_role_name(user.role)
    raw_role = (user.role or "").strip().lower()
    is_hospital_coordinator = raw_role in {"hospital_coordinator", "coordinator", "hospital coordinator"}

    if normalized_role == "admin":
        pass
    elif normalized_role == "claimant":
        if is_hospital_coordinator and (user.organization or "").strip():
            query = query.filter(
                or_(
                    Claim.created_by == user.id,
                    Claim.hospital_name.ilike(f"%{user.organization.strip()}%"),
                )
            )
        else:
            query = query.filter(or_(Claim.created_by == user.id, ClaimDocument.claim_id.is_(None)))
    elif normalized_role in ("claim_officer", "claims_officer", "tpa_reviewer") and (user.organization or "").strip():
        user_org = user.organization.strip()
        query = query.filter(
            or_(
                Policy.insurance_provider.ilike(f"%{user_org}%"),
                Claim.hospital_name.ilike(f"%{user_org}%"),
            )
        )

    if claim_id:
        try:
            claim_uuid = uuid.UUID(claim_id)
            query = query.filter(ClaimDocument.claim_id == claim_uuid)
        except ValueError:
            query = query.filter(Claim.claim_number.ilike(claim_id.strip()))

    if category and category != "All":
        cat_clean = category.strip()
        query = query.filter(
            or_(
                ClaimDocument.document_type.ilike(f"%{cat_clean}%"),
                ClaimDocument.document_type.ilike(f"%{cat_clean.replace(' ', '_')}%"),
            )
        )

    docs = query.order_by(ClaimDocument.uploaded_at.desc()).all()

    results = []
    for doc, claim_obj, policy_obj in docs:
        if not check_claim_access(claim_obj, policy_obj, user):
            continue
        extraction = (
            db.query(DocumentExtraction)
            .filter(DocumentExtraction.document_id == doc.id)
            .first()
        )

        size_str = "—"
        if doc.file_path:
            p = Path(doc.file_path)
            if p.exists():
                try:
                    bytes_size = p.stat().st_size
                    if bytes_size >= 1024 * 1024:
                        size_str = f"{bytes_size / (1024 * 1024):.1f} MB"
                    else:
                        size_str = f"{max(1, bytes_size // 1024)} KB"
                except Exception:
                    pass

        raw_cat = doc.document_type or "Document"
        display_cat = raw_cat.replace("_", " ").title()

        conf = 0.0
        if extraction and extraction.ocr_confidence is not None:
            c = float(extraction.ocr_confidence)
            if 0 < c <= 1.0:
                conf = round(c * 100.0, 2)
            else:
                conf = round(c, 2)

        if search:
            q = search.lower().strip()
            claim_num = claim_obj.claim_number.lower() if claim_obj else ""
            if (
                q not in doc.file_name.lower()
                and q not in raw_cat.lower()
                and q not in display_cat.lower()
                and q not in claim_num
            ):
                continue

        results.append({
            "id": str(doc.id),
            "name": doc.file_name,
            "category": display_cat,
            "rawCategory": raw_cat,
            "claimId": claim_obj.claim_number if claim_obj else str(doc.claim_id),
            "claimUuid": str(doc.claim_id),
            "confidence": conf,
            "status": "Verified" if doc.processing_status == "Completed" else ("Failed" if doc.processing_status == "Failed" else "Processing"),
            "size": size_str,
            "date": doc.uploaded_at.strftime("%d.%m.%Y") if doc.uploaded_at else "",
        })

    return results


@router.get("/{document_id}")
def get_document_detail(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_document_reader),
):
    """Return a comprehensive structured verification payload for a single uploaded document."""
    try:
        document_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID.")

    document = db.query(ClaimDocument).filter(ClaimDocument.id == document_uuid).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    claim = db.query(Claim).filter(Claim.id == document.claim_id).first() if document.claim_id else None
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first() if (claim and claim.policy_id) else None

    if not check_document_access(document, claim, policy, user):
        raise HTTPException(status_code=403, detail="This document is outside your authorized organization.")

    extraction = (
        db.query(DocumentExtraction)
        .filter(DocumentExtraction.document_id == document.id)
        .first()
    )

    medical_analysis = (
        db.query(MedicalAnalysis)
        .filter(MedicalAnalysis.document_id == document.id)
        .order_by(MedicalAnalysis.created_at.desc())
        .first()
    )

    ai_rows = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.document_id == document.id)
        .all()
    )

    verification = (
        db.query(VerificationResult)
        .filter(VerificationResult.claim_id == claim.id)
        .first()
    ) if claim else None

    validation_result = {}
    for row in ai_rows:
        if row.analysis_type == "Validation":
            validation_result = row.analysis_result or {}
            break

    if not validation_result and verification and verification.verification_summary:
        try:
            validation_summary = json.loads(verification.verification_summary)
            validation_result = validation_summary.get("validation", validation_summary)
        except Exception:
            validation_result = {"verification_summary": verification.verification_summary}

    classification_result = {}
    policy_result = {}
    for row in ai_rows:
        if row.analysis_type == "Document Classification":
            classification_result = row.analysis_result or {}
        elif row.analysis_type == "Policy Intelligence":
            policy_result = row.analysis_result or {}

    pipeline_stages = [
        {
            "stage": "OCR & Extraction",
            "status": "Completed" if extraction and extraction.extracted_text else ("Failed" if document.processing_status == "Failed" else "Pending"),
            "timestamp": extraction.updated_at.isoformat() if extraction and extraction.updated_at else None,
            "result": str(extraction.extracted_data) if extraction and extraction.extracted_data else None,
            "warning": None if extraction and extraction.extracted_text else "No OCR text persisted yet.",
        },
        {
            "stage": "Classification",
            "status": "Completed" if classification_result else ("Failed" if document.processing_status == "Failed" else "Pending"),
            "timestamp": None,
            "result": json.dumps(classification_result) if classification_result else None,
            "warning": None if classification_result else "Document type not classified yet.",
        },
        {
            "stage": "Validation",
            "status": "Completed" if validation_result else ("Failed" if document.processing_status == "Failed" else "Pending"),
            "timestamp": None,
            "result": json.dumps(validation_result) if validation_result else None,
            "warning": None if validation_result else "Validation results not available yet.",
        },
        {
            "stage": "Medical Intelligence",
            "status": "Completed" if medical_analysis and medical_analysis.analysis_result else ("Failed" if document.processing_status == "Failed" else "Pending"),
            "timestamp": medical_analysis.updated_at.isoformat() if medical_analysis and medical_analysis.updated_at else None,
            "result": json.dumps(medical_analysis.analysis_result) if medical_analysis and medical_analysis.analysis_result else None,
            "warning": None if medical_analysis and medical_analysis.analysis_result else "No medical analysis available.",
        },
    ]

    overall_status = "Verified"
    if document.processing_status == "Failed":
        overall_status = "Failed"
    elif document.processing_status == "Processing":
        overall_status = "Processing"
    elif verification and verification.verification_status and verification.verification_status.lower() in {"needs review", "incomplete"}:
        overall_status = "Needs Review"
    elif not extraction or not extraction.extracted_text:
        overall_status = "Pending"

    match_summary = []
    if isinstance(validation_result.get("mismatches"), list):
        for item in validation_result["mismatches"]:
            if isinstance(item, dict):
                match_summary.append({
                    "field": item.get("field", "document"),
                    "expected": item.get("expected", "Expected value"),
                    "extracted": item.get("actual", item.get("extracted", "—")),
                    "status": "Mismatch",
                    "evidence": item.get("evidence") or item.get("message"),
                })
            else:
                match_summary.append({
                    "field": "document",
                    "expected": "Consistent claim data",
                    "extracted": str(item),
                    "status": "Mismatch",
                    "evidence": str(item),
                })

    cross_document_comparisons = []
    if verification and verification.verification_summary:
        try:
            cross_document_payload = json.loads(verification.verification_summary)
            validation_cross = cross_document_payload.get("cross_document_validation") or cross_document_payload.get("crossDocumentValidation") or {}
            comparisons = validation_cross.get("comparisons") or validation_cross.get("mismatches") or []
            if isinstance(comparisons, list):
                for item in comparisons:
                    if isinstance(item, dict):
                        cross_document_comparisons.append({
                            "documentA": item.get("documentA") or item.get("document_a") or "Document A",
                            "field": item.get("field") or item.get("attribute") or "Value",
                            "documentB": item.get("documentB") or item.get("document_b") or "Document B",
                            "comparisonResult": item.get("comparisonResult") or item.get("status") or "Needs review",
                            "explanation": item.get("explanation") or item.get("details") or "",
                        })
        except Exception:
            cross_document_comparisons = []

    # Calculate explainable Document Reliability & Readiness Score (0-100)
    has_text = bool(extraction and extraction.extracted_text and extraction.extracted_text.strip())
    ocr_conf = float(extraction.ocr_confidence or 0.0) if extraction else 0.0
    cat_match = classification_result.get("category_match")
    cat_status = classification_result.get("category_status", "Correct Document Type" if cat_match else "Needs Review")
    
    reliability = calculate_document_reliability(
        ocr_confidence=ocr_conf,
        has_text=has_text,
        category_match=cat_match,
        category_status=cat_status,
        extracted_data=extraction.extracted_data if extraction else {},
        validation_mismatches=validation_result.get("mismatches", []),
        document_category=document.document_type or "document",
        has_crypto_signature=False,
        issuer_verified=False,
    )

    # Build plain-English field checking table: Information | Found in PDF | Compared With | Result
    field_checks = []
    ext_data = (extraction.extracted_data or {}) if extraction else {}
    
    # 1. Patient Name Check
    patient = db.query(Patient).filter(Patient.id == claim.patient_id).first() if (claim and claim.patient_id) else None
    claim_pat_name = patient.full_name if patient else ""
    found_pat_name = ext_data.get("patient_name") or ext_data.get("insured_name")
    if found_pat_name:
        if claim_pat_name:
            if found_pat_name.strip().lower() == claim_pat_name.strip().lower():
                pat_res = "Match"
            elif any(part in claim_pat_name.lower() for part in found_pat_name.lower().split()):
                pat_res = "Partial Match"
            else:
                pat_res = "Difference Found"
        else:
            pat_res = "Not Compared"
    else:
        pat_res = "Missing Info"
    field_checks.append({
        "information": "Patient Name",
        "foundInPdf": str(found_pat_name) if found_pat_name else "Not Found in Document",
        "comparedWith": claim_pat_name if claim_pat_name else "Claim Patient Name",
        "result": pat_res,
        "explanation": f"Patient name '{found_pat_name}' matches claim details." if pat_res == "Match" else ("Name appears different from claim details." if pat_res == "Difference Found" else "Patient name could not be identified in this file.")
    })

    # 2. Policy Number Check
    claim_pol_no = policy.policy_number if policy else ""
    found_pol_no = ext_data.get("policy_number") or ext_data.get("member_id")
    if found_pol_no:
        if claim_pol_no:
            pat_no_res = "Match" if claim_pol_no.lower() in found_pol_no.lower() or found_pol_no.lower() in claim_pol_no.lower() else "Difference Found"
        else:
            pat_no_res = "Not Compared"
    else:
        pat_no_res = "Missing Info"
    field_checks.append({
        "information": "Policy Number",
        "foundInPdf": str(found_pol_no) if found_pol_no else "Not Found in Document",
        "comparedWith": claim_pol_no if claim_pol_no else "Insurance Policy Details",
        "result": pat_no_res,
        "explanation": "Policy number verified against insurance record." if pat_no_res == "Match" else "Policy number missing or different."
    })

    # 3. Hospital Name Check
    claim_hosp = (claim.hospital_name or "") if claim else ""
    found_hosp = ext_data.get("hospital_name") or ext_data.get("clinic_name")
    if found_hosp:
        if claim_hosp:
            hosp_res = "Match" if claim_hosp.lower() in found_hosp.lower() or found_hosp.lower() in claim_hosp.lower() else "Difference Found"
        else:
            hosp_res = "Not Compared"
    else:
        hosp_res = "Missing Info"
    field_checks.append({
        "information": "Hospital Name",
        "foundInPdf": str(found_hosp) if found_hosp else "Not Found in Document",
        "comparedWith": claim_hosp if claim_hosp else "Admitting Hospital",
        "result": hosp_res,
        "explanation": "Hospital name matches admitting provider." if hosp_res == "Match" else "Hospital name not found or differs from admission details."
    })

    # 4. Dates Check
    claim_adm = claim.admission_date.strftime("%d.%m.%Y") if (claim and claim.admission_date) else ""
    found_adm = ext_data.get("admission_date") or ext_data.get("bill_date") or ext_data.get("report_date")
    if found_adm:
        date_res = "Match" if claim_adm and (claim_adm in str(found_adm) or str(found_adm) in claim_adm) else "Difference Found"
    else:
        date_res = "Missing Info"
    field_checks.append({
        "information": "Treatment / Admission Date",
        "foundInPdf": str(found_adm) if found_adm else "Not Found in Document",
        "comparedWith": claim_adm if claim_adm else "Admission Record",
        "result": date_res,
        "explanation": "Date matches admission date." if date_res == "Match" else "Date not clearly identified or differs."
    })

    # 5. Financial / Bill Amount Check (if billing doc)
    if "bill" in (document.document_type or "").lower() or "receipt" in (document.document_type or "").lower():
        claim_amt = str(claim.claimed_amount) if (claim and claim.claimed_amount) else ""
        found_amt = ext_data.get("total_amount") or ext_data.get("claimed_amount") or ext_data.get("net_payable")
        amt_res = "Match" if found_amt and claim_amt and (str(int(float(found_amt))) == str(int(float(claim_amt)))) else ("Difference Found" if found_amt else "Missing Info")
        field_checks.append({
            "information": "Total Bill Amount",
            "foundInPdf": f"₹{found_amt}" if found_amt else "Not Found in Document",
            "comparedWith": f"₹{claim_amt}" if claim_amt else "Claimed Amount",
            "result": amt_res,
            "explanation": "Billed sum matches claimed figure." if amt_res == "Match" else "Billed sum differs from pre-auth estimate or claim total."
        })

    # Build medical diagnosis intelligence table for medical documents
    medical_diagnoses = []
    med_res = (medical_analysis.analysis_result or {}) if medical_analysis else {}
    if med_res:
        diags = med_res.get("diagnoses") or med_res.get("icd10_mappings") or []
        if isinstance(diags, list):
            for d in diags:
                if isinstance(d, dict):
                    medical_diagnoses.append({
                        "originalDiagnosis": d.get("original") or d.get("diagnosis") or d.get("text") or "Clinical Diagnosis",
                        "normalizedDiagnosis": d.get("normalized") or d.get("name") or "Normalized Condition",
                        "icd10Code": d.get("code") or d.get("icd10_code") or "R69",
                        "description": d.get("description") or "Illness, unspecified",
                        "confidence": int(float(d.get("confidence") or 0.85) * 100) if float(d.get("confidence") or 0.85) <= 1.0 else int(d.get("confidence") or 85),
                        "status": d.get("status") or "AI Suggested",
                        "evidence": d.get("evidence") or "Extracted from medical document findings",
                    })
        if not medical_diagnoses and (med_res.get("diagnosis") or (medical_analysis and medical_analysis.diagnosis)):
            d_name = med_res.get("diagnosis") or (medical_analysis.diagnosis if medical_analysis else "")
            medical_diagnoses.append({
                "originalDiagnosis": d_name,
                "normalizedDiagnosis": d_name,
                "icd10Code": med_res.get("icd10_code") or ("A90" if "dengue" in d_name.lower() else "K35.80" if "appendic" in d_name.lower() else "R69"),
                "description": med_res.get("icd10_description") or "Documented primary diagnosis",
                "confidence": 92,
                "status": "AI Suggested",
                "evidence": f"Identified in {document.document_type} clinical narrative",
            })

    # Calculate explainable Claim Readiness Assessment for the claim
    claim_readiness = None
    if claim:
        claim_docs = db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim.id).all()
        doc_ids = [d.id for d in claim_docs]
        claim_exts = {
            str(ext.document_id): ext
            for ext in db.query(DocumentExtraction).filter(DocumentExtraction.document_id.in_(doc_ids)).all()
        } if doc_ids else {}
        claim_consents = db.query(PatientConsent).filter(PatientConsent.claim_id == claim.id).all()
        
        claim_stage = getattr(claim, "claim_type", "preauth") or "preauth"
        curr_stg = str(getattr(claim, "current_stage", "")).lower()
        if "final" in curr_stg or "discharge" in curr_stg:
            claim_stage = "final_auth"

        claim_readiness = calculate_explainable_claim_readiness(
            claim=claim,
            patient=patient,
            policy=policy,
            documents=claim_docs,
            extractions=claim_exts,
            medical_analysis=medical_analysis,
            verification_result=verification,
            consents=claim_consents,
            stage=claim_stage,
        )

    return {
        "documentId": str(document.id),
        "fileName": document.file_name,
        "category": document.document_type,
        "claimId": str(document.claim_id) if document.claim_id else "Unassigned",
        "claimNumber": claim.claim_number if claim else "Standalone / Pre-Auth Draft",
        "uploadDate": document.uploaded_at.isoformat() if document.uploaded_at else None,
        "processingStatus": document.processing_status,
        "ocrStatus": "Completed" if extraction and extraction.extracted_text else ("Failed" if document.processing_status == "Failed" else "Pending"),
        "extractionStatus": extraction.extraction_status if extraction else "Pending",
        "validationStatus": verification.verification_status if verification else "Pending",
        "matchingStatus": validation_result.get("verification_status") or ("Needs Review" if match_summary else "Validated"),
        "overallStatus": overall_status,
        "ocrConfidence": float(extraction.ocr_confidence) if extraction and extraction.ocr_confidence is not None else 0.0,
        "extractedText": extraction.extracted_text if extraction else None,
        "extractedFields": extraction.extracted_data if extraction else {},
        "classification": classification_result,
        "validation": validation_result,
        "medicalAnalysis": medical_analysis.analysis_result if medical_analysis else {},
        "policyIntelligence": policy_result,
        "matchSummary": match_summary,
        "crossDocumentComparisons": cross_document_comparisons,
        "reliabilityScore": reliability["score"],
        "reliabilityBreakdown": reliability["breakdown"],
        "reliabilityTier": reliability["tier"],
        "reliabilityTierSummary": reliability["tierSummary"],
        "authenticityStatus": reliability["authenticityStatus"],
        "plainEnglishExplanation": reliability["explanation"],
        "missingFields": reliability.get("missingFields", []),
        "foundFields": reliability.get("foundFields", []),
        "extractionConfidence": reliability.get("extractionConfidence", 0.0),
        "recommendedCorrections": reliability.get("recommendedCorrections", []),
        "claimReadiness": claim_readiness,
        "fieldChecks": field_checks,
        "medicalDiagnoses": medical_diagnoses,
        "fileUrl": f"/documents/{document.id}/file",
        "pipeline": {
            "stages": pipeline_stages,
        },
    }


# =========================================================
# PIPELINE EXECUTION & BACKGROUND TASKS
# =========================================================

def execute_pipeline_sync(
    document_uuid: uuid.UUID,
    user_id: Optional[uuid.UUID],
    db: Session,
) -> dict:
    """
    Synchronous execution of the ClaimBridge pipeline for a document.
    Updates progress stages (OCR Processing -> Validation -> Completed / Failed)
    and persists all extraction, AI analysis, and verification records.
    """
    document = (
        db.query(ClaimDocument)
        .filter(ClaimDocument.id == document_uuid)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    claim = db.query(Claim).filter(Claim.id == document.claim_id).first() if document.claim_id else None

    if not document.file_path:
        raise HTTPException(status_code=400, detail="Document does not have a stored file path.")

    image_path = Path(document.file_path)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded document file could not be found on the server.")

    if not POLICY_PATH.exists():
        raise HTTPException(status_code=500, detail="ClaimBridge sample policy file could not be found.")

    # 1. Update status to OCR Processing
    document.processing_status = "OCR Processing"
    if user_id:
        db.add(
            AuditEvent(
                event_type="document_processing_started",
                actor_user_id=user_id,
                claim_id=claim.id if claim else None,
                details={"document_id": str(document.id)},
            )
        )
    db.commit()

    # 2. Run ClaimBridge pipeline
    try:
        pipeline_result = process_document(
            image_path=str(image_path),
            policy_path=str(POLICY_PATH),
            claim_id=str(document.claim_id or "DRAFT-INTAKE"),
        )
    except Exception as pipe_err:
        logger.error(f"Pipeline error for document {document.id}: {pipe_err}", exc_info=True)
        document.processing_status = "Failed"
        if user_id:
            db.add(
                AuditEvent(
                    event_type="document_processing_failed",
                    actor_user_id=user_id,
                    claim_id=claim.id if claim else None,
                    details={"document_id": str(document.id), "error": str(pipe_err)},
                )
            )
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"ClaimBridge document processing failed: {str(pipe_err)}",
        )

    # 3. Update status to Validation
    document.processing_status = "Validation"
    db.commit()

    # 4. Extract results & document classification checks
    ocr_result = pipeline_result.get("ocr", {})
    classification_result = pipeline_result.get("classification", {})
    detected_category = classification_result.get("document_type")
    classification_conf = float(classification_result.get("confidence", 0.0) or 0.0)
    user_category = document.document_type or "Auto-Detect"
    has_extracted_text = bool(ocr_result.get("text") and str(ocr_result.get("text")).strip())

    category_match = True
    category_status = "Correct Document Type"
    category_mismatch_warning = None

    if not has_extracted_text:
        category_match = False
        category_status = "Unreadable File"
        category_mismatch_warning = f"Unreadable File: No extractable text found in {document.file_name}. Please upload a clear scan."
        document.processing_status = "Failed"
        document.validation_status = "Unreadable File"
    elif user_category and user_category.lower() not in {"auto-detect", "unknown", "other_medical_doc", "document"}:
        norm_selected = normalize_category_name(user_category)
        norm_detected = normalize_category_name(detected_category)

        if norm_detected and norm_detected != "unknown" and classification_conf >= 0.50:
            is_compat = False
            for cat_key, cat_group in COMPATIBLE_CATEGORIES.items():
                if norm_selected == cat_key or norm_selected in cat_group:
                    if norm_detected == cat_key or norm_detected in cat_group:
                        is_compat = True
                        break
            if not is_compat:
                category_match = False
                category_status = "Incorrect Document Type"
                sel_display = CATEGORY_DISPLAY_NAMES.get(norm_selected, user_category)
                det_display = CATEGORY_DISPLAY_NAMES.get(norm_detected, detected_category)
                category_mismatch_warning = f"Incorrect Document Type. This PDF appears to be a {det_display}, not {sel_display}. Please upload the correct document."
                document.validation_status = "Incorrect Document Type"
            else:
                category_match = True
                category_status = "Correct Document Type"
                document.validation_status = "Verified"
        elif classification_conf < 0.45:
            category_match = None
            category_status = "Document Type Uncertain"
            category_mismatch_warning = "Document Type Uncertain: Please review to ensure the uploaded file matches selected category."
            document.validation_status = "Needs Review"
        else:
            category_match = True
            category_status = "Correct Document Type"
            document.validation_status = "Verified"
    else:
        if detected_category and detected_category != "unknown":
            document.document_type = detected_category

    classification_result["category_match"] = category_match
    classification_result["category_status"] = category_status
    if category_mismatch_warning:
        classification_result["mismatch_warning"] = category_mismatch_warning

    extraction_result = pipeline_result.get("extracted_information", {})
    medical_result = pipeline_result.get("medical_intelligence", {})
    policy_result = pipeline_result.get("policy_intelligence", {})
    validation_result = pipeline_result.get("validation", {})
    readiness_result = pipeline_result.get("claim_readiness", {})
    confidence_result = pipeline_result.get("confidence", {})
    final_decision_result = pipeline_result.get("final_claim_decision", {})

    # 5. Persist records
    try:
        existing_extraction = (
            db.query(DocumentExtraction)
            .filter(DocumentExtraction.document_id == document.id)
            .first()
        )
        if existing_extraction:
            extraction_record = existing_extraction
        else:
            extraction_record = DocumentExtraction(document_id=document.id)
            db.add(extraction_record)

        extraction_record.extracted_text = str(ocr_result.get("text", ""))
        extraction_record.extracted_data = extraction_result
        extraction_record.ocr_confidence = safe_decimal(ocr_result.get("confidence", 0))
        extraction_record.extraction_status = "Completed"

        existing_medical = (
            db.query(MedicalAnalysis)
            .filter(
                MedicalAnalysis.claim_id == document.claim_id,
                MedicalAnalysis.document_id == document.id,
            )
            .first()
        )
        if existing_medical:
            medical_record = existing_medical
        else:
            medical_record = MedicalAnalysis(
                claim_id=document.claim_id,
                document_id=document.id,
            )
            db.add(medical_record)

        medical_record.diagnosis = medical_result.get("diagnosis")
        medical_record.procedure = medical_result.get("procedure")
        medical_record.analysis_result = medical_result
        medical_record.confidence_score = safe_decimal(
            medical_result.get("confidence_score", medical_result.get("medical_confidence", medical_result.get("confidence", 0)))
        )
        medical_record.risk_score = safe_decimal(
            medical_result.get("risk_score", medical_result.get("medical_risk_score", 0))
        )
        medical_record.processing_status = "Completed"

        ai_records = [
            ("Document Classification", classification_result),
            ("Policy Intelligence", policy_result),
            ("Validation", validation_result),
            ("Claim Readiness", readiness_result),
            ("Confidence", confidence_result),
            ("Final Claim Decision", final_decision_result),
        ]

        for analysis_type, result in ai_records:
            confidence_value = result.get(
                "confidence",
                result.get(
                    "confidence_score",
                    result.get(
                        "retrieval_confidence",
                        result.get(
                            "overall_confidence",
                            result.get("readiness_score", 0),
                        ),
                    ),
                ),
            )
            risk_value = result.get("risk_score", result.get("medical_risk_score", 0))

            existing_ai = (
                db.query(AIAnalysis)
                .filter(
                    AIAnalysis.claim_id == document.claim_id,
                    AIAnalysis.document_id == document.id,
                    AIAnalysis.analysis_type == analysis_type,
                )
                .first()
            )
            if existing_ai:
                ai_record = existing_ai
            else:
                ai_record = AIAnalysis(
                    claim_id=document.claim_id,
                    document_id=document.id,
                    analysis_type=analysis_type,
                )
                db.add(ai_record)

            ai_record.model_name = "ClaimBridge Pipeline"
            ai_record.input_data = {
                "document_id": str(document.id),
                "file_name": document.file_name,
            }
            ai_record.analysis_result = result
            ai_record.confidence_score = safe_decimal(confidence_value)
            ai_record.risk_score = safe_decimal(risk_value)
            ai_record.processing_status = "Completed"

        readiness_score = readiness_result.get("readiness_score", 0)
        verification_status = validation_result.get("status", "Completed")
        missing_documents = validation_result.get("missing", validation_result.get("missing_documents", []))
        mismatches = validation_result.get("mismatches", [])
        risk_indicators = validation_result.get("risk_indicators", [])

        other_extractions = (
            db.query(DocumentExtraction)
            .join(ClaimDocument, DocumentExtraction.document_id == ClaimDocument.id)
            .filter(
                ClaimDocument.claim_id == document.claim_id,
                ClaimDocument.id != document.id,
                DocumentExtraction.extraction_status == "Completed",
            )
            .all()
        )
        all_doc_extractions = [
            e.extracted_data for e in other_extractions if e.extracted_data
        ] + [extraction_result]

        cross_reconciliation = validate_cross_document_consistency(all_doc_extractions)
        combined_mismatches = list(dict.fromkeys(mismatches + cross_reconciliation.get("mismatches", [])))
        combined_risk_indicators = list(dict.fromkeys(risk_indicators + cross_reconciliation.get("risk_indicators", [])))
        combined_missing_docs = list(dict.fromkeys(missing_documents + cross_reconciliation.get("missing_documents", [])))

        if combined_mismatches:
            verification_status = "Needs Review"
            mismatch_penalty = min(len(combined_mismatches) * 10, 40)
            readiness_score = max(0.0, float(readiness_score) - mismatch_penalty)

        verification_summary_data = {
            "validation": validation_result,
            "claim_readiness": readiness_result,
            "confidence": confidence_result,
            "final_claim_decision": final_decision_result,
            "cross_document_validation": cross_reconciliation,
        }

        verification_record = (
            db.query(VerificationResult)
            .filter(VerificationResult.claim_id == document.claim_id)
            .first()
        )
        if not verification_record:
            verification_record = VerificationResult(claim_id=document.claim_id)
            db.add(verification_record)

        verification_record.readiness_score = safe_decimal(readiness_score)
        verification_record.verification_status = verification_status
        verification_record.missing_documents = combined_missing_docs
        verification_record.mismatches = combined_mismatches
        verification_record.risk_indicators = combined_risk_indicators
        verification_record.verification_summary = json.dumps(verification_summary_data)

        if claim:
            claim.readiness_score = safe_decimal(readiness_score)

        if document.processing_status != "Failed":
            document.processing_status = "Completed"

        if user_id:
            db.add(
                AuditEvent(
                    event_type="document_processing_completed",
                    actor_user_id=user_id,
                    claim_id=claim.id if claim else None,
                    details={
                        "document_id": str(document.id),
                        "readiness_score": float(readiness_score),
                    },
                )
            )

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(f"Persistence error for document {document_uuid}: {exc}", exc_info=True)
        doc = db.query(ClaimDocument).filter(ClaimDocument.id == document_uuid).first()
        if doc:
            doc.processing_status = "Failed"
            db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline result persistence failed: {str(exc)}",
        )

    return {
        "documentId": str(document.id),
        "claimId": str(document.claim_id),
        "fileName": document.file_name,
        "processingStatus": document.processing_status,
        "pipeline": pipeline_result,
        "message": "Document processed successfully through the ClaimBridge pipeline.",
    }


def run_pipeline_background_task(document_id: str, user_id: str, user_role: str):
    """Background task runner executing the OCR & processing pipeline."""
    logger.info(f"Background task starting for document {document_id}")
    db = SessionLocal()
    try:
        user_uuid = uuid.UUID(user_id) if user_id else None
        execute_pipeline_sync(uuid.UUID(document_id), user_uuid, db)
        logger.info(f"Background task finished successfully for document {document_id}")
    except Exception as exc:
        logger.error(f"Background task failed for document {document_id}: {exc}", exc_info=True)
    finally:
        db.close()


# =========================================================
# UPLOAD DOCUMENT
# =========================================================

@router.post("/upload")
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = Form("Auto-Detect"),
    claim_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_claimant),
):
    """
    Upload a document and associate it with an existing ClaimBridge claim.
    The file is saved, validated, persisted in DB, and returned immediately (< 200ms).
    Heavy OCR, classification, and validation are started as an asynchronous background task.
    """
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file was provided.",
        )

    original_filename = Path(file.filename).name
    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed types: PNG, JPG, JPEG, PDF.",
        )

    claim = None
    claim_policy = None
    if claim_id:
        try:
            claim_uuid = uuid.UUID(claim_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid claim ID.")

        row = (
            db.query(Claim, Policy)
            .outerjoin(Policy, Claim.policy_id == Policy.id)
            .filter(Claim.id == claim_uuid)
            .first()
        )
        if not row or not row[0]:
            raise HTTPException(
                status_code=404,
                detail="Claim not found. Create the claim before uploading documents.",
            )
        claim, claim_policy = row[0], row[1]
    else:
        claims_query = (
            db.query(Claim, Policy)
            .outerjoin(Policy, Claim.policy_id == Policy.id)
            .order_by(Claim.created_at.desc())
        )
        claims_query = apply_claim_scope(claims_query, user)
        scoped_claim = claims_query.first()
        if scoped_claim:
            claim, claim_policy = scoped_claim[0], scoped_claim[1]
        if not claim:
            draft_num = f"CLM-DRAFT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            u_name = getattr(user, "full_name", None) or getattr(user, "email", "New Patient")
            patient = db.query(Patient).filter(Patient.full_name == u_name).first()
            if not patient:
                patient = Patient(full_name=u_name)
                db.add(patient)
                db.flush()
            default_prov = db.query(InsuranceProvider).first()
            prov_name = default_prov.name if default_prov else "HDFC ERGO General Insurance"
            policy = db.query(Policy).first()
            if not policy:
                policy = Policy(
                    policy_number=f"POL-DRAFT-{datetime.utcnow().strftime('%Y%m%d')}",
                    insurance_provider=prov_name,
                    policy_start_date=date.today(),
                    policy_end_date=date(date.today().year + 1, 12, 31),
                    coverage_amount=Decimal("500000"),
                )
                db.add(policy)
                db.flush()
            claim = Claim(
                claim_number=draft_num,
                patient_id=patient.id,
                policy_id=policy.id,
                hospital_name=user.organization or "Hospital Intake",
                admission_date=date.today(),
                claimed_amount=Decimal("0"),
                claim_status="Draft",
                current_stage="01 Secure Document Intake",
                readiness_score=Decimal("0"),
                created_by=user.id,
                claim_type="cashless",
                discharge_readiness_status="Pending Pre-Auth",
            )
            db.add(claim)
            db.flush()

    if not claim_policy and claim and claim.policy_id:
        claim_policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    if not check_claim_access(claim, claim_policy, user):
        raise HTTPException(
            status_code=403,
            detail="This claim is outside your authorized organization.",
        )

    # Check for duplicate document for this claim
    existing_doc = (
        db.query(ClaimDocument)
        .filter(
            ClaimDocument.claim_id == claim.id,
            ClaimDocument.file_name == original_filename,
        )
        .first()
    )
    if existing_doc and existing_doc.file_path and Path(existing_doc.file_path).exists():
        if category and category != "Auto-Detect":
            existing_doc.document_type = category
            db.commit()
        if existing_doc.processing_status not in ["Completed", "OCR Processing", "Validation"]:
            pipeline_executor.submit(
                run_pipeline_background_task,
                str(existing_doc.id),
                str(user.id),
                user.role,
            )
        return {
            "documentId": str(existing_doc.id),
            "claimId": str(existing_doc.claim_id),
            "fileName": existing_doc.file_name,
            "category": existing_doc.document_type,
            "processingStatus": existing_doc.processing_status or "Uploaded",
            "message": "Document already uploaded and queued for processing.",
        }

    document_id = uuid.uuid4()
    safe_filename = f"{document_id}{extension}"
    file_path = UPLOAD_DIR / safe_filename

    try:
        # Stream file to disk in chunks to avoid buffering entire file in memory
        with open(file_path, "wb") as output_file:
            shutil.copyfileobj(file.file, output_file)

        file_size = file_path.stat().st_size
        if file_size == 0:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

        if file_size > 50 * 1024 * 1024:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="File size exceeds maximum allowed limit (50 MB).")

        if extension == ".pdf":
            with open(file_path, "rb") as check_f:
                header = check_f.read(5)
            if header != b"%PDF-":
                file_path.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="Invalid PDF file: Missing or invalid PDF signature (%PDF-).")

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(exc)}")

    document = ClaimDocument(
        id=document_id,
        claim_id=claim.id,
        document_type=category,
        file_name=original_filename,
        file_path=str(file_path),
        processing_status="Uploaded",
    )

    try:
        db.add(document)
        db.add(
            AuditEvent(
                event_type="document_uploaded",
                actor_user_id=user.id,
                claim_id=claim.id,
                details={"document_id": str(document.id), "category": category},
            )
        )
        db.commit()

    except Exception as exc:
        db.rollback()
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Document database creation failed: {str(exc)}")

    # Queue background processing immediately
    pipeline_executor.submit(
        run_pipeline_background_task,
        str(document.id),
        str(user.id),
        user.role,
    )

    return {
        "documentId": str(document.id),
        "claimId": str(document.claim_id),
        "fileName": document.file_name,
        "category": document.document_type,
        "processingStatus": document.processing_status,
        "message": "Document uploaded successfully and queued for processing.",
    }


# =========================================================
# PROCESS DOCUMENT
# =========================================================

@router.post("/{document_id}/process")
def process_uploaded_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_claimant),
):
    """
    Run or fetch results of the ClaimBridge AI pipeline for an uploaded document.
    If already completed by background task, returns cached results immediately.
    """
    try:
        document_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID.")

    document = (
        db.query(ClaimDocument)
        .filter(ClaimDocument.id == document_uuid)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    claim = db.query(Claim).filter(Claim.id == document.claim_id).first() if document.claim_id else None
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first() if (claim and claim.policy_id) else None
    if not check_document_access(document, claim, policy, user):
        raise HTTPException(
            status_code=403,
            detail="This document is outside your authorized organization.",
        )

    # If already completed in background, return persisted results
    if document.processing_status == "Completed":
        extraction = db.query(DocumentExtraction).filter(DocumentExtraction.document_id == document.id).first()
        ai_rows = db.query(AIAnalysis).filter(AIAnalysis.document_id == document.id).all()
        med_row = db.query(MedicalAnalysis).filter(MedicalAnalysis.document_id == document.id).first()
        classification = {}
        validation = {}
        readiness = {}
        for r in ai_rows:
            if r.analysis_type == "Document Classification":
                classification = r.analysis_result or {}
            elif r.analysis_type == "Validation":
                validation = r.analysis_result or {}
            elif r.analysis_type == "Claim Readiness":
                readiness = r.analysis_result or {}

        return {
            "documentId": str(document.id),
            "claimId": str(document.claim_id),
            "fileName": document.file_name,
            "processingStatus": document.processing_status,
            "pipeline": {
                "ocr": {"text": extraction.extracted_text if extraction else "", "confidence": float(extraction.ocr_confidence or 0.0) if extraction else 0.0},
                "classification": classification,
                "extracted_information": extraction.extracted_data if extraction else {},
                "medical_intelligence": med_row.analysis_result if med_row else {},
                "validation": validation,
                "claim_readiness": readiness,
            },
            "message": "Document processed successfully through the ClaimBridge pipeline.",
        }

    return execute_pipeline_sync(document_uuid, user.id, db)


# =========================================================
# GET DOCUMENT OCR / PROCESSING RESULT
# =========================================================

@router.get("/{document_id}/file")
def download_document_file(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_document_reader),
):
    try:
        document_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID.")

    document = (
        db.query(ClaimDocument)
        .filter(ClaimDocument.id == document_uuid)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    claim = db.query(Claim).filter(Claim.id == document.claim_id).first() if document.claim_id else None
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first() if (claim and claim.policy_id) else None
    if not check_document_access(document, claim, policy, user):
        raise HTTPException(status_code=403, detail="This document is outside your authorized scope.")

    file_path = Path(document.file_path or "").resolve()
    upload_root = UPLOAD_DIR.resolve()
    if file_path.parent != upload_root or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Document file is unavailable.")

    db.add(
        AuditEvent(
            event_type="document_downloaded",
            actor_user_id=user.id,
            claim_id=claim.id,
            details={"document_id": str(document.id)},
        )
    )
    db.commit()
    return FileResponse(
        path=file_path,
        filename=document.file_name,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{document_id}/ocr")
def get_document_ocr(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_document_reader),
):
    """
    Return the persisted OCR/extraction result
    for a processed document.
    """

    # -----------------------------------------------------
    # VALIDATE UUID
    # -----------------------------------------------------

    try:

        document_uuid = uuid.UUID(
            document_id
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid document ID.",
        )

    # -----------------------------------------------------
    # FIND DOCUMENT
    # -----------------------------------------------------

    document = (
        db.query(ClaimDocument)
        .filter(
            ClaimDocument.id
            == document_uuid
        )
        .first()
    )

    if not document:

        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    claim = db.query(Claim).filter(Claim.id == document.claim_id).first() if document.claim_id else None
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first() if (claim and claim.policy_id) else None
    if not check_document_access(document, claim, policy, user):
        raise HTTPException(
            status_code=403,
            detail="This document is outside your authorized organization.",
        )

    # -----------------------------------------------------
    # FIND EXTRACTION
    # -----------------------------------------------------

    extraction = (
        db.query(DocumentExtraction)
        .filter(
            DocumentExtraction.document_id
            == document.id
        )
        .first()
    )

    # -----------------------------------------------------
    # NO OCR RESULT YET
    # -----------------------------------------------------

    if not extraction:

        return {
            "documentId": str(
                document.id
            ),

            "claimId": str(
                document.claim_id
            ),

            "fileName": (
                document.file_name
            ),

            "confidence": 0,

            "extractedFields": {},

            "boundingBoxes": [],

            "status": (
                document.processing_status
            ),

            "message": (
                "Document has not been processed yet."
            ),
        }

    # -----------------------------------------------------
    # RETURN PERSISTED OCR RESULT
    # -----------------------------------------------------

    return {
        "documentId": str(
            document.id
        ),

        "claimId": str(
            document.claim_id
        ),

        "fileName": (
            document.file_name
        ),

        "confidence": float(
            extraction.ocr_confidence
            or 0
        ),

        "extractedFields": (
            extraction.extracted_data
            or {}
        ),

        "boundingBoxes": [],

        "status": (
            document.processing_status
        ),

        "message": (
            "OCR and extraction results "
            "retrieved successfully."
        ),
    }

# =========================================================
# ASSOCIATE DOCUMENTS TO CLAIM
# =========================================================

class AssociateDocumentsRequest(BaseModel):
    documentIds: List[str]
    claimId: str

@router.post("/associate-claim")
def associate_documents_to_claim(
    payload: AssociateDocumentsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_claimant),
):
    """Associate documents uploaded during draft wizard with the created claim."""
    try:
        claim_uuid = uuid.UUID(payload.claimId)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim UUID.")
    claim = db.query(Claim).filter(Claim.id == claim_uuid).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")
    
    updated_count = 0
    for doc_id_str in payload.documentIds:
        try:
            doc_uuid = uuid.UUID(doc_id_str)
            doc = db.query(ClaimDocument).filter(ClaimDocument.id == doc_uuid).first()
            if doc:
                doc.claim_id = claim.id
                updated_count += 1
        except Exception:
            continue
    db.commit()
    return {"message": f"Successfully associated {updated_count} documents with claim {claim.claim_number}.", "updatedCount": updated_count}
