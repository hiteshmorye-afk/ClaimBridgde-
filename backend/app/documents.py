import json
import uuid
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
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

from .auth import (
    require_document_reader,
    require_claimant,
)
from .claims import apply_claim_scope, check_claim_access
from .database import get_db
from .models import (
    AIAnalysis,
    AuditEvent,
    Claim,
    ClaimDocument,
    DocumentExtraction,
    MedicalAnalysis,
    Policy,
    User,
    VerificationResult,
)
from .pipeline import process_document
from .validation_engine import validate_cross_document_consistency


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
        .join(Claim, ClaimDocument.claim_id == Claim.id)
        .join(Policy, Claim.policy_id == Policy.id)
    )
    query = apply_claim_scope(query, user)

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


# =========================================================
# UPLOAD DOCUMENT
# =========================================================

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("Auto-Detect"),
    claim_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_claimant),
):
    """
    Upload a document and associate it with
    an existing ClaimBridge claim.

    Processing is intentionally kept separate
    from upload so that document intake and AI
    processing remain separate pipeline stages.
    """

    # -----------------------------------------------------
    # STEP 1 — VALIDATE FILE
    # -----------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file was provided.",
        )

    # Sanitize original filename to prevent path traversal
    original_filename = Path(file.filename).name

    extension = Path(
        original_filename
    ).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                "Allowed types: PNG, JPG, JPEG, PDF."
            ),
        )

    # -----------------------------------------------------
    # STEP 2 & 3 — RESOLVE CLAIM
    # -----------------------------------------------------

    claim = None
    if claim_id:
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
                detail=(
                    "Claim not found. "
                    "Create the claim before uploading documents."
                ),
            )
    else:
        claims_query = (
            db.query(Claim, Policy)
            .join(Policy, Claim.policy_id == Policy.id)
            .order_by(Claim.created_at.desc())
        )
        claims_query = apply_claim_scope(claims_query, user)
        scoped_claim = claims_query.first()
        claim = scoped_claim[0] if scoped_claim else None
        if not claim:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No claim in your authorized organization was found to associate the document with. "
                    "Please specify claim_id or create a claim first."
                ),
            )

    claim_policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    if not claim_policy or not check_claim_access(claim, claim_policy, user):
        raise HTTPException(
            status_code=403,
            detail="This claim is outside your authorized organization.",
        )

    # -----------------------------------------------------
    # STEP 4 — CREATE DOCUMENT UUID
    # -----------------------------------------------------

    document_id = uuid.uuid4()

    safe_filename = (
        f"{document_id}{extension}"
    )

    file_path = (
        UPLOAD_DIR / safe_filename
    )

    # -----------------------------------------------------
    # STEP 5 — SAVE FILE & VALIDATE CONTENT
    # -----------------------------------------------------

    try:

        file_content = await file.read()

        if not file_content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty (0 bytes).",
            )

        # Enforce 50 MB limit
        if len(file_content) > 50 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File size exceeds maximum allowed limit (50 MB).",
            )

        # Enforce valid PDF header
        if extension == ".pdf":
            if len(file_content) < 5 or not file_content.startswith(b"%PDF-"):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid PDF file: Missing or invalid PDF signature (%PDF-).",
                )

        with open(
            file_path,
            "wb",
        ) as output_file:

            output_file.write(
                file_content
            )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to save uploaded file: {str(exc)}"
            ),
        )

    # -----------------------------------------------------
    # STEP 6 — CREATE CLAIM DOCUMENT RECORD
    # -----------------------------------------------------

    document = ClaimDocument(
        id=document_id,

        claim_id=claim.id,

        document_type=category,

        file_name=original_filename,

        file_path=str(file_path),

        processing_status="Pending",
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

        db.refresh(document)

    except Exception as exc:

        db.rollback()

        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail=(
                f"Document database creation failed: {str(exc)}"
            ),
        )

    # -----------------------------------------------------
    # STEP 7 — RETURN DOCUMENT INFORMATION
    # -----------------------------------------------------

    return {
        "documentId": str(
            document.id
        ),

        "claimId": str(
            document.claim_id
        ),

        "fileName": document.file_name,

        "category": document.document_type,

        "processingStatus": (
            document.processing_status
        ),

        "message": (
            "Document uploaded successfully."
        ),
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
    Run the existing ClaimBridge AI pipeline
    against an uploaded document.

    Pipeline:

        OCR
        ↓
        Document Classification
        ↓
        Information Extraction
        ↓
        Medical Intelligence
        ↓
        Policy Intelligence
        ↓
        Validation
        ↓
        Claim Readiness
        ↓
        Confidence
        ↓
        Final Claim Decision
    """

    # -----------------------------------------------------
    # STEP 1 — VALIDATE DOCUMENT UUID
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
    # STEP 2 — FIND DOCUMENT
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

    claim = db.query(Claim).filter(Claim.id == document.claim_id).first()
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first() if claim else None
    if not claim or not policy or not check_claim_access(claim, policy, user):
        raise HTTPException(
            status_code=403,
            detail="This document is outside your authorized organization.",
        )

    # -----------------------------------------------------
    # STEP 3 — VERIFY FILE EXISTS
    # -----------------------------------------------------

    if not document.file_path:

        raise HTTPException(
            status_code=400,
            detail=(
                "Document does not have a stored file path."
            ),
        )

    image_path = Path(
        document.file_path
    )

    if not image_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Uploaded document file "
                "could not be found on the server."
            ),
        )

    # -----------------------------------------------------
    # STEP 4 — VERIFY POLICY FILE
    # -----------------------------------------------------

    if not POLICY_PATH.exists():

        raise HTTPException(
            status_code=500,
            detail=(
                "ClaimBridge sample policy file "
                "could not be found."
            ),
        )

    # -----------------------------------------------------
    # STEP 5 — UPDATE PROCESSING STATUS
    # -----------------------------------------------------

    document.processing_status = "Processing"
    db.add(
        AuditEvent(
            event_type="document_processing_started",
            actor_user_id=user.id,
            claim_id=claim.id,
            details={"document_id": str(document.id)},
        )
    )

    db.commit()

    # -----------------------------------------------------
    # STEP 6 — RUN EXISTING CLAIMBRIDGE PIPELINE
    # -----------------------------------------------------

    try:

        pipeline_result = process_document(
            image_path=str(image_path),

            policy_path=str(
                POLICY_PATH
            ),

            claim_id=str(
                document.claim_id
            ),
        )

    except Exception:

        document.processing_status = "Failed"
        db.add(
            AuditEvent(
                event_type="document_processing_failed",
                actor_user_id=user.id,
                claim_id=claim.id,
                details={"document_id": str(document.id)},
            )
        )

        db.commit()

        raise HTTPException(
            status_code=500,
            detail=(
                "ClaimBridge document processing failed. Review the server logs."
            ),
        )

    # -----------------------------------------------------
    # STEP 7 — EXTRACT PIPELINE RESULTS
    # -----------------------------------------------------

    ocr_result = (
        pipeline_result.get(
            "ocr",
            {},
        )
    )

    classification_result = (
        pipeline_result.get(
            "classification",
            {},
        )
    )

    detected_category = classification_result.get("document_type")
    if detected_category and detected_category != "unknown":
        document.document_type = detected_category

    extraction_result = (
        pipeline_result.get(
            "extracted_information",
            {},
        )
    )

    medical_result = (
        pipeline_result.get(
            "medical_intelligence",
            {},
        )
    )

    policy_result = (
        pipeline_result.get(
            "policy_intelligence",
            {},
        )
    )

    validation_result = (
        pipeline_result.get(
            "validation",
            {},
        )
    )

    readiness_result = (
        pipeline_result.get(
            "claim_readiness",
            {},
        )
    )

    confidence_result = (
        pipeline_result.get(
            "confidence",
            {},
        )
    )

    final_decision_result = (
        pipeline_result.get(
            "final_claim_decision",
            {},
        )
    )

    # -----------------------------------------------------
    # STEP 8 — PERSIST OCR + EXTRACTION
    # -----------------------------------------------------

    try:

        existing_extraction = (
            db.query(DocumentExtraction)
            .filter(
                DocumentExtraction.document_id
                == document.id
            )
            .first()
        )

        if existing_extraction:

            extraction_record = (
                existing_extraction
            )

        else:

            extraction_record = (
                DocumentExtraction(
                    document_id=document.id
                )
            )

            db.add(
                extraction_record
            )

        extraction_record.extracted_text = (
            ocr_result.get(
                "text",
                "",
            )
        )

        extraction_record.extracted_data = (
            extraction_result
        )

        extraction_record.ocr_confidence = safe_decimal(
            ocr_result.get("confidence", 0)
        )

        extraction_record.extraction_status = "Completed"

        # -------------------------------------------------
        # STEP 9 — PERSIST MEDICAL ANALYSIS
        # -------------------------------------------------

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
            medical_result.get(
                "confidence_score",
                medical_result.get(
                    "medical_confidence",
                    medical_result.get("confidence", 0),
                ),
            )
        )
        medical_record.risk_score = safe_decimal(
            medical_result.get(
                "risk_score",
                medical_result.get("medical_risk_score", 0),
            )
        )
        medical_record.processing_status = "Completed"

        # -------------------------------------------------
        # STEP 10 — PERSIST AI ANALYSIS RECORDS (UPSERT)
        # -------------------------------------------------

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

            risk_value = result.get(
                "risk_score",
                result.get("medical_risk_score", 0),
            )

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

        # -------------------------------------------------
        # STEP 11 — PERSIST VERIFICATION RESULT & CROSS RECONCILIATION
        # -------------------------------------------------

        readiness_score = readiness_result.get("readiness_score", 0)
        verification_status = validation_result.get("status", "Completed")

        missing_documents = validation_result.get(
            "missing",
            validation_result.get("missing_documents", []),
        )

        mismatches = validation_result.get("mismatches", [])
        risk_indicators = validation_result.get("risk_indicators", [])

        # Cross-document reconciliation across all documents for this claim
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

        # Merge single-doc and cross-document mismatches & risks
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
            verification_record = VerificationResult(
                claim_id=document.claim_id
            )
            db.add(verification_record)

        verification_record.readiness_score = safe_decimal(readiness_score)
        verification_record.verification_status = verification_status
        verification_record.missing_documents = combined_missing_docs
        verification_record.mismatches = combined_mismatches
        verification_record.risk_indicators = combined_risk_indicators
        verification_record.verification_summary = json.dumps(verification_summary_data)

        # -------------------------------------------------
        # STEP 12 — UPDATE CLAIM READINESS
        # -------------------------------------------------

        claim = (
            db.query(Claim)
            .filter(Claim.id == document.claim_id)
            .first()
        )

        if claim:
            claim.readiness_score = safe_decimal(readiness_score)

        # -------------------------------------------------
        # STEP 13 — MARK DOCUMENT COMPLETE
        # -------------------------------------------------

        document.processing_status = (
            "Completed"
        )
        db.add(
            AuditEvent(
                event_type="document_processing_completed",
                actor_user_id=user.id,
                claim_id=claim.id if claim else None,
                details={
                    "document_id": str(document.id),
                    "readiness_score": float(readiness_score),
                },
            )
        )

        # -------------------------------------------------
        # STEP 14 — COMMIT EVERYTHING
        # -------------------------------------------------

        db.commit()

    except Exception as exc:

        db.rollback()

        document = (
            db.query(ClaimDocument)
            .filter(
                ClaimDocument.id
                == document_uuid
            )
            .first()
        )

        if document:

            document.processing_status = (
                "Failed"
            )

            db.commit()

        raise HTTPException(
            status_code=500,
            detail=(
                "Pipeline result persistence failed: "
                f"{str(exc)}"
            ),
        )

    # -----------------------------------------------------
    # STEP 15 — RETURN COMPLETE PIPELINE RESULT
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

        "processingStatus": (
            document.processing_status
        ),

        "pipeline": pipeline_result,

        "message": (
            "Document processed successfully "
            "through the ClaimBridge pipeline."
        ),
    }


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

    claim = db.query(Claim).filter(Claim.id == document.claim_id).first()
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first() if claim else None
    if not claim or not policy or not check_claim_access(claim, policy, user):
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

    claim = db.query(Claim).filter(Claim.id == document.claim_id).first()
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first() if claim else None
    if not claim or not policy or not check_claim_access(claim, policy, user):
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