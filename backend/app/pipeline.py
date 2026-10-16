from pathlib import Path

from .validation_engine import validate_extracted_information
from .ocr import run_ocr
from .document_classifier import classify_document
from .information_extractor import extract_information
from .biomedical_nlp import get_biomedical_nlp_service
from .medical_intelligence import analyze_medical_information
from .policy_rag import get_policy_rag_engine
from .policy_intelligence import analyze_policy_information
from .llm_adapter import get_llm_client, ClaimContextForLLM
from .claim_readiness_engine import evaluate_claim_readiness
from .confidence_engine import evaluate_claim_confidence
from .final_claim_decision import evaluate_final_claim_decision
from .claim_history import record_claim_history


def load_policy_document(policy_path: str) -> str:
    """
    Load policy document text for Policy Intelligence.
    """

    with open(
        policy_path,
        "r",
        encoding="utf-8",
    ) as file:
        return file.read()


def process_document(
    image_path: str,
    policy_path: str,
    claim_id: str = "CLM-TEST-001",
):
    """
    Complete ClaimBridge document processing pipeline.

    Secure Document Intake
        ↓
    Image Preprocessing / OCR
        ↓
    Document Classification
        ↓
    Information Extraction
        ↓
    Structured Data + OCR Text
        ↓
    Medical Intelligence
        ↓
    Policy Intelligence
        ↓
    Validation Engine
        ↓
    Claim Readiness Engine
        ↓
    Confidence Engine
        ↓
    Auto Processing / Human Review
        ↓
    Final Claim Decision
        ↓
    Claim History
    """

    print("\n" + "=" * 60)
    print("CLAIMBRIDGE COMPLETE PROCESSING PIPELINE")
    print("=" * 60)

    # =====================================================
    # STEP 1: OCR
    # =====================================================

    print("\n[1/9] Running OCR...")

    ocr_result = run_ocr(
        image_path
    )

    extracted_text = ocr_result.get(
        "text",
        "",
    )

    ocr_confidence = ocr_result.get(
        "confidence",
        0.0,
    )

    print(
        f"OCR Confidence: "
        f"{ocr_confidence * 100:.2f}%"
    )

    print(
        f"Detected Lines: "
        f"{ocr_result.get('line_count', 0)}"
    )

    # =====================================================
    # STEP 2: DOCUMENT CLASSIFICATION
    # =====================================================

    print("\n[2/9] Classifying document...")

    classification_result = classify_document(
        extracted_text
    )

    print(
        f"Document Type: "
        f"{classification_result['document_type']}"
    )

    print(
        f"Classification Confidence: "
        f"{classification_result['confidence'] * 100:.2f}%"
    )

    # =====================================================
    # STEP 3: INFORMATION EXTRACTION
    # =====================================================

    print("\n[3/9] Extracting information...")

    extraction_result = extract_information(
        extracted_text,
        document_type=classification_result.get("document_type"),
    )

    # =====================================================
    # STEP 4: BIOMEDICAL NLP
    # =====================================================

    print("\n[4/11] Running Biomedical NLP...")

    biomedical_service = get_biomedical_nlp_service()
    biomedical_result = biomedical_service.process_clinical_text(
        extracted_text
    )

    print(
        f"Detected Diseases: {biomedical_result.diseases}"
    )
    print(
        f"Detected Procedures: {biomedical_result.procedures}"
    )
    print(
        f"Detected Medications: {biomedical_result.medications}"
    )

    # =====================================================
    # STEP 5: MEDICAL INTELLIGENCE
    # =====================================================

    print("\n[5/11] Running Medical Intelligence...")

    medical_result = analyze_medical_information(
        extracted_text,
        extraction_result,
    )

    # Enrich medical diagnosis/procedure if absent from regex
    if not medical_result.get("diagnosis") and biomedical_result.diseases:
        medical_result["diagnosis"] = biomedical_result.diseases[0]
    if not medical_result.get("procedure") and biomedical_result.procedures:
        medical_result["procedure"] = biomedical_result.procedures[0]
    medical_result["biomedical_nlp"] = biomedical_result.to_dict()

    print(
        f"Medical Diagnosis: "
        f"{medical_result['diagnosis']}"
    )

    print(
        f"Medical Procedure: "
        f"{medical_result['procedure']}"
    )

    print(
        f"Medical Risk Score: "
        f"{medical_result['risk_score']}"
    )

    print(
        f"Medical Confidence: "
        f"{medical_result['confidence_score'] * 100:.2f}%"
    )

    print(
        f"Medical Status: "
        f"{medical_result['processing_status']}"
    )

    # =====================================================
    # STEP 6: POLICY RAG & POLICY INTELLIGENCE
    # =====================================================

    print("\n[6/11] Running Policy RAG Retrieval & Intelligence...")

    policy_text = load_policy_document(
        policy_path
    )

    rag_engine = get_policy_rag_engine()
    policy_id = Path(policy_path).stem if policy_path else "sample_policy"
    policy_rag_citations = rag_engine.retrieve(
        query=extracted_text,
        policy_id=policy_id,
        top_k=3,
    )

    policy_result = analyze_policy_information(
        policy_text=policy_text,
        ocr_text=extracted_text,
        extracted_information=extraction_result,
        medical_information=medical_result,
    )

    policy_result["rag_citations"] = [c.to_dict() for c in policy_rag_citations]

    print(
        f"Policy Status: "
        f"{policy_result['policy_status']}"
    )

    print(
        f"Policy Retrieval Confidence: "
        f"{policy_result['retrieval_confidence'] * 100:.2f}%"
    )

    print(
        f"Retrieved Policy Citations: "
        f"{len(policy_rag_citations)}"
    )

    print(
        f"Relevant Exclusions: "
        f"{policy_result['relevant_exclusions']}"
    )

    # =====================================================
    # STEP 7: DETERMINISTIC VALIDATION
    # =====================================================

    print("\n[7/11] Running Validation Engine...")

    validation_result = validate_extracted_information(
        extraction_result
    )

    print(
        f"Verification Status: "
        f"{validation_result['verification_status']}"
    )

    print(
        f"Validation Readiness Score: "
        f"{validation_result['readiness_score']:.2f}%"
    )

    print(
        f"Missing Fields: "
        f"{validation_result['missing_fields']}"
    )

    print(
        f"Mismatches: "
        f"{validation_result['mismatches']}"
    )

    # =====================================================
    # STEP 8: LLM REVIEWER EXPLANATION & ADVISORY SYNTHESIS
    # =====================================================

    print("\n[8/11] Generating LLM Reviewer Advisory Note...")

    llm_client = get_llm_client()
    llm_context = ClaimContextForLLM(
        claim_id=claim_id,
        patient_name=extraction_result.get("patient_name"),
        patient_age=extraction_result.get("age"),
        hospital=extraction_result.get("hospital_name"),
        policy_number=extraction_result.get("policy_number"),
        claimed_amount=float(extraction_result.get("total_charges") or 0.0),
        diagnosis=medical_result.get("diagnosis"),
        procedure=medical_result.get("procedure"),
        medical_indicators=medical_result.get("medical_indicators", []),
        medical_services=medical_result.get("medical_services", []),
        policy_citations=[c.to_dict() for c in policy_rag_citations],
        missing_documents=validation_result.get("missing_fields", []),
        mismatches=validation_result.get("mismatches", []),
        readiness_score=validation_result.get("readiness_score"),
    )

    llm_explanation_result = llm_client.generate_explanation(llm_context)

    print(
        f"LLM Synthesis Status: {llm_explanation_result.provider_status}"
    )

    # =====================================================
    # STEP 7: CLAIM READINESS ENGINE
    # =====================================================

    print("\n[7/9] Evaluating Claim Readiness...")

    readiness_result = evaluate_claim_readiness(
        ocr_result=ocr_result,
        validation_result=validation_result,
        medical_result=medical_result,
        policy_result=policy_result,
    )

    print(
        f"Claim Readiness Score: "
        f"{readiness_result['readiness_score']:.2f}%"
    )

    print(
        f"Readiness Status: "
        f"{readiness_result['readiness_status']}"
    )

    # =====================================================
    # STEP 8: CONFIDENCE ENGINE
    # =====================================================

    print("\n[8/9] Evaluating Confidence...")

    confidence_result = evaluate_claim_confidence(
        ocr_result=ocr_result,
        medical_result=medical_result,
        policy_result=policy_result,
        validation_result=validation_result,
        readiness_result=readiness_result,
    )

    print(
        f"Confidence Score: "
        f"{confidence_result['confidence_score']:.2f}%"
    )

    print(
        f"Confidence Level: "
        f"{confidence_result['confidence_level']}"
    )

    print(
        f"Processing Route: "
        f"{confidence_result['processing_route']}"
    )

    # =====================================================
    # STEP 9: FINAL DECISION + CLAIM HISTORY
    # =====================================================

    print("\n[9/9] Generating Final Claim Decision...")

    decision_result = evaluate_final_claim_decision(
        readiness_result=readiness_result,
        confidence_result=confidence_result,
        policy_result=policy_result,
        validation_result=validation_result,
    )

    print(
        f"Final Processing Decision: "
        f"{decision_result['decision']}"
    )

    # -----------------------------------------------------
    # Claim History
    # -----------------------------------------------------

    print("\nRecording Claim History...")

    history_result = record_claim_history(
        claim_id=claim_id,
        decision_result=decision_result,
        readiness_result=readiness_result,
        confidence_result=confidence_result,
        policy_result=policy_result,
        validation_result=validation_result,
    )

    print(
        f"Claim History Status: "
        f"{history_result['processing_status']}"
    )

    # =====================================================
    # COMPLETE RESULT
    # =====================================================

    result = {
        "claim_id": claim_id,

        "file": image_path,

        "ocr": ocr_result,

        "classification": classification_result,

        "extracted_information": extraction_result,

        "biomedical_nlp": biomedical_result.to_dict(),

        "medical_intelligence": medical_result,

        "policy_rag": [c.to_dict() for c in policy_rag_citations],

        "policy_intelligence": policy_result,

        "validation": validation_result,

        "llm_explanation": llm_explanation_result.to_dict(),

        "claim_readiness": readiness_result,

        "confidence": confidence_result,

        "final_claim_decision": decision_result,

        "claim_history": history_result,
    }

    print("\n" + "=" * 60)
    print("CLAIMBRIDGE PROCESSING COMPLETED")
    print("=" * 60)

    return result


if __name__ == "__main__":

    import os

    backend_dir = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )

    input_path = os.path.join(
        backend_dir,
        "test_images",
        "sample_bill.png",
    )

    policy_path = os.path.join(
        backend_dir,
        "policies",
        "sample_policy.txt",
    )

    process_document(
        image_path=input_path,
        policy_path=policy_path,
        claim_id="CLM-TEST-001",
    )
