import re

new_section = '''# =========================================================
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
    if claim_id:
        try:
            claim_uuid = uuid.UUID(claim_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid claim ID.")

        claim = db.query(Claim).filter(Claim.id == claim_uuid).first()
        if not claim:
            raise HTTPException(
                status_code=404,
                detail="Claim not found. Create the claim before uploading documents.",
            )
    else:
        claims_query = (
            db.query(Claim, Policy)
            .outerjoin(Policy, Claim.policy_id == Policy.id)
            .order_by(Claim.created_at.desc())
        )
        claims_query = apply_claim_scope(claims_query, user)
        scoped_claim = claims_query.first()
        claim = scoped_claim[0] if scoped_claim else None
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

    claim_policy = db.query(Policy).filter(Policy.id == claim.policy_id).first() if (claim and claim.policy_id) else None
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
            background_tasks.add_task(
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
        db.refresh(document)
    except Exception as exc:
        db.rollback()
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Document database creation failed: {str(exc)}")

    # Queue background processing immediately
    background_tasks.add_task(
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
'''

with open('backend/app/documents.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Locate markers
upload_idx = content.find('# =========================================================\n# UPLOAD DOCUMENT\n# =========================================================')
if upload_idx == -1:
    upload_idx = content.find('# =========================================================\r\n# UPLOAD DOCUMENT\r\n# =========================================================')

next_idx = content.find('# =========================================================\n# GET DOCUMENT OCR / PROCESSING RESULT\n# =========================================================')
if next_idx == -1:
    next_idx = content.find('# =========================================================\r\n# GET DOCUMENT OCR / PROCESSING RESULT\r\n# =========================================================')

if upload_idx == -1 or next_idx == -1:
    raise ValueError(f"Could not locate markers: upload_idx={upload_idx}, next_idx={next_idx}")

updated_content = content[:upload_idx] + new_section + "\n\n" + content[next_idx:]

with open('backend/app/documents.py', 'w', encoding='utf-8') as f:
    f.write(updated_content)

print("Successfully updated backend/app/documents.py!")
