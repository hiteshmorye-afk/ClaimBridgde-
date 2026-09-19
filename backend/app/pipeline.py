from .validation_engine import validate_extracted_information
from .ocr import run_ocr
from .document_classifier import classify_document
from .information_extractor import extract_information
from .medical_intelligence import analyze_medical_information
from .policy_intelligence import analyze_policy_information
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
        extracted_text
    )

    # =====================================================
    # STEP 4: MEDICAL INTELLIGENCE
    # =====================================================

    print("\n[4/9] Running Medical Intelligence...")

    medical_result = analyze_medical_information(
        extracted_text,
        extraction_result,
    )

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
    # STEP 5: POLICY INTELLIGENCE
    # =====================================================

    print("\n[5/9] Running Policy Intelligence...")

    policy_text = load_policy_document(
        policy_path
    )

    policy_result = analyze_policy_information(
        policy_text=policy_text,
        ocr_text=extracted_text,
        extracted_information=extraction_result,
        medical_information=medical_result,
    )

    print(
        f"Policy Status: "
        f"{policy_result['policy_status']}"
    )

    print(
        f"Policy Retrieval Confidence: "
        f"{policy_result['retrieval_confidence'] * 100:.2f}%"
    )

    print(
        f"Relevant Exclusions: "
        f"{policy_result['relevant_exclusions']}"
    )

    # =====================================================
    # STEP 6: VALIDATION
    # =====================================================

    print("\n[6/9] Running Validation Engine...")

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

        "medical_intelligence": medical_result,

        "policy_intelligence": policy_result,

        "validation": validation_result,

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
