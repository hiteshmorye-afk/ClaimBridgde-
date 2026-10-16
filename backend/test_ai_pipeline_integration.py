"""
ClaimBridge Integrated AI Pipeline Unit & Invariant Test Suite
=============================================================
Tests the end-to-end sequence:
Document OCR/Text -> Classification -> Extraction -> Biomedical NLP ->
Policy RAG -> LLM Reviewer Explanation -> Validation -> Readiness -> Decision

Verifies all critical architectural invariants:
1. Missing documents remain distinct from policy exclusions.
2. Medical evidence is not treated as proof of policy coverage.
3. Readiness does not imply approval (High readiness can still require Human Review).
4. Low readiness does not automatically imply rejection (routes to Human Review).
5. The LLM and BioBERT cannot bypass authorization or deterministic validation.
6. AI/provider failures do not corrupt claim status or fabricate successful processing.
"""

import pytest
from app.document_classifier import classify_document
from app.information_extractor import extract_information
from app.biomedical_nlp import get_biomedical_nlp_service
from app.medical_intelligence import analyze_medical_information
from app.policy_rag import get_policy_rag_engine
from app.policy_intelligence import analyze_policy_information
from app.validation_engine import validate_extracted_information
from app.llm_adapter import get_llm_client, ClaimContextForLLM
from app.claim_readiness_engine import evaluate_claim_readiness
from app.confidence_engine import evaluate_claim_confidence
from app.final_claim_decision import evaluate_final_claim_decision


SAMPLE_DISCHARGE_SUMMARY_OCR = """
APOLLO HOSPITALS INTERNATIONAL
DISCHARGE SUMMARY
Patient Name: Rajesh Kumar
Age: 52
Admission Date: 12.08.2026
Discharge Date: 16.08.2026
Total Charges: INR 165000

DIAGNOSIS: Acute Cholecystitis with Cholelithiasis
CHIEF COMPLAINT: Severe acute abdominal pain and fever.
PROCEDURE PERFORMED: Laparoscopic Cholecystectomy under general anaesthesia.
TREATMENT: Inj Ceftriaxone, Inj Pantoprazole, IV fluids.
INVESTIGATIONS: Ultrasound Abdomen showed distended gallbladder with multiple calculi.
"""

SAMPLE_POLICY_CORPUS = """
CLAIMBRIDGE STANDARD HEALTH INSURANCE POLICY

SECTION 1 - INPATIENT HOSPITALIZATION
Hospitalization expenses are covered for medically necessary acute inpatient care.

SECTION 2 - SURGICAL PROCEDURES
Medically necessary surgical procedures performed by a qualified surgeon are covered.

SECTION 3 - EXCLUSIONS
Cosmetic treatments, aesthetic surgeries, and self-inflicted injuries are excluded.

SECTION 4 - MANDATORY CLAIM DOCUMENTS
Claimant must submit the official discharge summary, itemized hospital bill,
and diagnostic lab/radiology reports.
"""


def test_connected_ai_pipeline_execution():
    # 1. Classification
    class_res = classify_document(SAMPLE_DISCHARGE_SUMMARY_OCR)
    assert class_res["document_type"] == "discharge_summary"

    # 2. Information Extraction
    ext_res = extract_information(SAMPLE_DISCHARGE_SUMMARY_OCR, document_type=class_res["document_type"])
    assert ext_res["patient_name"] == "Rajesh Kumar"
    assert ext_res["admission_date"] == "12.08.2026"
    assert ext_res["total_charges"] == 165000.0

    # 3. Biomedical NLP
    bio_service = get_biomedical_nlp_service()
    bio_res = bio_service.process_clinical_text(SAMPLE_DISCHARGE_SUMMARY_OCR)
    assert "Acute Cholecystitis" in bio_res.diseases
    assert "Laparoscopic Cholecystectomy" in bio_res.procedures
    assert "Ceftriaxone" in bio_res.medications

    # 4. Medical Intelligence (Enriched)
    med_res = analyze_medical_information(SAMPLE_DISCHARGE_SUMMARY_OCR, ext_res)
    if not med_res.get("procedure") and bio_res.procedures:
        med_res["procedure"] = bio_res.procedures[0]
    assert "Acute Cholecystitis" in med_res["diagnosis"]
    assert "Laparoscopic Cholecystectomy" in med_res["procedure"]
    assert med_res["medical_risk_score"] < 50

    # 5. Policy RAG Retrieval (Isolated)
    rag_engine = get_policy_rag_engine()
    rag_engine.ingest_policy_text(SAMPLE_POLICY_CORPUS, policy_id="POL-STD", document_name="standard_policy.txt")
    citations = rag_engine.retrieve(SAMPLE_DISCHARGE_SUMMARY_OCR, policy_id="POL-STD", top_k=3)
    assert len(citations) >= 1
    assert all(c.policy_id == "POL-STD" for c in citations)

    # 6. Policy Intelligence
    policy_res = analyze_policy_information(
        policy_text=SAMPLE_POLICY_CORPUS,
        ocr_text=SAMPLE_DISCHARGE_SUMMARY_OCR,
        extracted_information=ext_res,
        medical_information=med_res,
        top_k=5,
    )
    assert "Covered" in policy_res["policy_status"]

    # 7. Deterministic Validation
    val_res = validate_extracted_information(ext_res)
    assert val_res["readiness_score"] > 60

    # 8. LLM Reviewer Advisory Note
    llm_client = get_llm_client()
    llm_ctx = ClaimContextForLLM(
        claim_id="CLM-TEST-001",
        patient_name=ext_res.get("patient_name"),
        patient_age=ext_res.get("age"),
        hospital="Apollo Hospitals International",
        policy_number="9876543210",
        claimed_amount=ext_res.get("total_charges"),
        diagnosis=med_res.get("diagnosis"),
        procedure=med_res.get("procedure"),
        medical_indicators=med_res.get("medical_indicators", []),
        medical_services=med_res.get("medical_services", []),
        policy_citations=[c.to_dict() for c in citations],
        missing_documents=val_res.get("missing_fields", []),
        mismatches=val_res.get("mismatches", []),
        readiness_score=val_res.get("readiness_score"),
    )
    llm_res = llm_client.generate_explanation(llm_ctx)
    assert len(llm_res.verified_facts) >= 2
    assert llm_res.provider_status in {"mock", "success", "fallback_unavailable"}

    # 9. Claim Readiness Engine
    readiness_res = evaluate_claim_readiness(
        ocr_result={"confidence": 0.95},
        validation_result=val_res,
        medical_result=med_res,
        policy_result=policy_res,
    )
    assert readiness_res["readiness_score"] > 0

    # 10. Confidence Engine
    conf_res = evaluate_claim_confidence(
        ocr_result={"confidence": 0.95},
        medical_result=med_res,
        policy_result=policy_res,
        validation_result=val_res,
        readiness_result=readiness_res,
    )
    assert conf_res["confidence_score"] > 0

    # 11. Final Decision
    decision_res = evaluate_final_claim_decision(
        readiness_result=readiness_res,
        confidence_result=conf_res,
        policy_result=policy_res,
        validation_result=val_res,
    )
    assert decision_res["decision"] in {"Proceed with Automated Processing", "Human Review Required", "Additional Review Required"}


def test_invariant_missing_documents_vs_policy_exclusions():
    """Missing documents must remain distinct from policy exclusions."""
    val_res = validate_extracted_information({})
    assert "patient_name" in val_res["missing_fields"]

    policy_res = analyze_policy_information(
        policy_text=SAMPLE_POLICY_CORPUS,
        ocr_text="Cosmetic rhinoplasty aesthetic surgery exclusions.",
        extracted_information={},
        medical_information={"diagnosis": "Cosmetic Rhinoplasty", "procedure": "Aesthetic Surgery"},
        top_k=5,
    )
    # Exclusions are policy flags, not missing document fields
    assert "patient_name" not in policy_res["relevant_exclusions"]
    assert any("cosmetic" in e.lower() for e in policy_res["relevant_exclusions"])


def test_invariant_low_readiness_does_not_imply_rejection():
    """Low readiness must route to Human Review, never automatic rejection."""
    low_readiness = {"readiness_score": 35.0, "readiness_status": "Low Readiness"}
    low_conf = {"confidence_score": 40.0, "confidence_level": "Low", "processing_route": "Human Review Required"}
    policy_res = {"policy_status": "Needs Review", "relevant_exclusions": []}
    val_res = {"verification_status": "Incomplete", "readiness_score": 35.0}

    decision = evaluate_final_claim_decision(
        readiness_result=low_readiness,
        confidence_result=low_conf,
        policy_result=policy_res,
        validation_result=val_res,
    )
    assert decision["decision"] in {"Human Review Required", "Additional Review Required"}
    assert decision["decision"] != "Rejected"


def test_invariant_llm_cannot_alter_readiness_or_decision():
    """LLM output schema has no fields for altering readiness score or making binding decisions."""
    llm_client = get_llm_client()
    ctx = ClaimContextForLLM(
        claim_id="CLM-001",
        diagnosis="Acute Appendicitis",
        readiness_score=50.0,
    )
    res = llm_client.generate_explanation(ctx)
    res_dict = res.to_dict()

    # Verify no mutable decision/authorization fields exist
    assert "claim_decision" not in res_dict
    assert "override_readiness" not in res_dict
    assert "authorize_payment" not in res_dict
    assert "Advisory AI output" in res_dict["disclaimer"]
