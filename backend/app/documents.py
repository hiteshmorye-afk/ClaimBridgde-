import uuid
from decimal import Decimal
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from .database import get_db
from .models import (
    AIAnalysis,
    Claim,
    ClaimDocument,
    DocumentExtraction,
    MedicalAnalysis,
    VerificationResult,
)
from .pipeline import process_document


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
# UPLOAD DOCUMENT
# =========================================================

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(...),
    claim_id: str = Form(...),
    db: Session = Depends(get_db),
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

    original_filename = file.filename

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
    # STEP 2 — VALIDATE CLAIM UUID
    # -----------------------------------------------------

    try:
        claim_uuid = uuid.UUID(claim_id)

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid claim ID.",
        )

    # -----------------------------------------------------
    # STEP 3 — VERIFY CLAIM EXISTS
    # -----------------------------------------------------

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
    # STEP 5 — SAVE FILE
    # -----------------------------------------------------

    try:

        file_content = await file.read()

        if not file_content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
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

    except Exception as exc:

        document.processing_status = "Failed"

        db.commit()

        raise HTTPException(
            status_code=500,
            detail=(
                "ClaimBridge document processing failed: "
                f"{str(exc)}"
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

        extraction_record.ocr_confidence = (
            Decimal(
                str(
                    ocr_result.get(
                        "confidence",
                        0,
                    )
                )
            )
        )

        extraction_record.extraction_status = (
            "Completed"
        )

        # -------------------------------------------------
        # STEP 9 — PERSIST MEDICAL ANALYSIS
        # -------------------------------------------------

        existing_medical = (
            db.query(MedicalAnalysis)
            .filter(
                MedicalAnalysis.claim_id
                == document.claim_id,

                MedicalAnalysis.document_id
                == document.id,
            )
            .first()
        )

        if existing_medical:

            medical_record = (
                existing_medical
            )

        else:

            medical_record = (
                MedicalAnalysis(
                    claim_id=document.claim_id,
                    document_id=document.id,
                )
            )

            db.add(
                medical_record
            )

        medical_record.diagnosis = (
            medical_result.get(
                "diagnosis"
            )
        )

        medical_record.procedure = (
            medical_result.get(
                "procedure"
            )
        )

        medical_record.analysis_result = (
            medical_result
        )

        medical_record.confidence_score = (
            Decimal(
                str(
                    medical_result.get(
                        "medical_confidence",
                        medical_result.get(
                            "confidence",
                            0,
                        ),
                    )
                )
            )
        )

        medical_record.risk_score = (
            Decimal(
                str(
                    medical_result.get(
                        "medical_risk_score",
                        medical_result.get(
                            "risk_score",
                            0,
                        ),
                    )
                )
            )
        )

        medical_record.processing_status = (
            "Completed"
        )

        # -------------------------------------------------
        # STEP 10 — PERSIST AI ANALYSIS RECORDS
        # -------------------------------------------------

        ai_records = [
            (
                "Document Classification",
                classification_result,
            ),
            (
                "Policy Intelligence",
                policy_result,
            ),
            (
                "Validation",
                validation_result,
            ),
            (
                "Claim Readiness",
                readiness_result,
            ),
            (
                "Confidence",
                confidence_result,
            ),
            (
                "Final Claim Decision",
                final_decision_result,
            ),
        ]

        for analysis_type, result in ai_records:

            confidence_value = (
                result.get(
                    "confidence",
                    result.get(
                        "confidence_score",
                        result.get(
                            "retrieval_confidence",
                            result.get(
                                "overall_confidence",
                                result.get(
                                    "readiness_score",
                                    0,
                                ),
                            ),
                        ),
                    ),
                )
            )

            risk_value = (
                result.get(
                    "risk_score",
                    result.get(
                        "medical_risk_score",
                        0,
                    ),
                )
            )

            ai_record = AIAnalysis(
                claim_id=document.claim_id,

                document_id=document.id,

                analysis_type=analysis_type,

                model_name=(
                    "ClaimBridge Pipeline"
                ),

                input_data={
                    "document_id": str(
                        document.id
                    ),
                    "file_name": (
                        document.file_name
                    ),
                },

                analysis_result=result,

                confidence_score=Decimal(
                    str(
                        confidence_value
                        or 0
                    )
                ),

                risk_score=Decimal(
                    str(
                        risk_value
                        or 0
                    )
                ),

                processing_status="Completed",
            )

            db.add(
                ai_record
            )

        # -------------------------------------------------
        # STEP 11 — PERSIST VERIFICATION RESULT
        # -------------------------------------------------

        readiness_score = (
            readiness_result.get(
                "readiness_score",
                0,
            )
        )

        verification_status = (
            validation_result.get(
                "status",
                "Completed",
            )
        )

        missing_documents = (
            validation_result.get(
                "missing",
                validation_result.get(
                    "missing_documents",
                    [],
                ),
            )
        )

        mismatches = (
            validation_result.get(
                "mismatches",
                [],
            )
        )

        risk_indicators = (
            validation_result.get(
                "risk_indicators",
                [],
            )
        )

        verification_summary = {
            "validation": validation_result,
            "claim_readiness": readiness_result,
            "confidence": confidence_result,
            "final_claim_decision": (
                final_decision_result
            ),
        }

        verification_record = (
            db.query(VerificationResult)
            .filter(
                VerificationResult.claim_id
                == document.claim_id
            )
            .first()
        )

        if not verification_record:

            verification_record = (
                VerificationResult(
                    claim_id=document.claim_id
                )
            )

            db.add(
                verification_record
            )

        verification_record.readiness_score = (
            Decimal(
                str(
                    readiness_score
                    or 0
                )
            )
        )

        verification_record.verification_status = (
            verification_status
        )

        verification_record.missing_documents = (
            missing_documents
        )

        verification_record.mismatches = (
            mismatches
        )

        verification_record.risk_indicators = (
            risk_indicators
        )

        verification_record.verification_summary = (
            verification_summary
        )

        # -------------------------------------------------
        # STEP 12 — UPDATE CLAIM READINESS
        # -------------------------------------------------

        claim = (
            db.query(Claim)
            .filter(
                Claim.id
                == document.claim_id
            )
            .first()
        )

        if claim:

            claim.readiness_score = (
                Decimal(
                    str(
                        readiness_score
                        or 0
                    )
                )
            )

        # -------------------------------------------------
        # STEP 13 — MARK DOCUMENT COMPLETE
        # -------------------------------------------------

        document.processing_status = (
            "Completed"
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

@router.get("/{document_id}/ocr")
def get_document_ocr(
    document_id: str,
    db: Session = Depends(get_db),
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