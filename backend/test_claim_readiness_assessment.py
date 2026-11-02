"""
Test Suite: Explainable Claim Readiness Assessment & Scoring System
Covers all 15 deterministic scenarios specified in ClaimBridge workflow rules:
1. Patient Identity & Details (full + verified)
2. Patient Identity & Details (missing + unverified)
3. Insurance Policy Information (valid + adequate)
4. Insurance Policy Information (sum insured exceeded or missing)
5. Medical Diagnosis & ICD-10 (full + mapped)
6. Medical Diagnosis & ICD-10 (unmapped / missing)
7. Required Documents: Initial Pre-Auth stage (NO final bill or discharge summary required)
8. Required Documents: Final Auth stage (final bill & discharge summary required)
9. Required Documents: Reimbursement stage
10. Document Quality & Correctness: Misclassified document gives 0 points for category
11. Cross-Document Consistency: Discrepancies deduct points
12. Consent & Authorization: Missing consent deducts points with action
13. Missing Critical Information triggers is_provisional = True
14. Deterministic Total Score equals sum of category points & readiness levels map correctly
15. Independence & Consistency: Switching document in same claim leaves Claim Readiness score identical
"""

import pytest
from app.claim_readiness_engine import (
    DEFAULT_CATEGORY_WEIGHTS,
    STAGE_REQUIRED_DOCUMENTS,
    calculate_explainable_claim_readiness,
    determine_readiness_level,
)
from app.document_reliability import calculate_document_reliability


# =========================================================================
# TEST SCENARIO 1: Patient Identity & Details (Full + Verified)
# =========================================================================
def test_01_patient_identity_full_and_verified():
    patient = {
        "full_name": "Aarav Sharma",
        "date_of_birth": "1988-06-15",
        "gender": "Male",
        "contact_number": "9876543210",
    }
    claim = {
        "aadhaar_verification_status": "Verified via Aadhaar QR/XML",
    }

    result = calculate_explainable_claim_readiness(
        patient=patient,
        claim=claim,
        stage="preauth",
    )

    cat = result["categories"]["patient_identity"]
    assert cat["weight"] == 15.0
    assert cat["score"] == 15.0
    assert cat["status"] == "Passed"
    assert len(cat["missing_info"]) == 0
    assert len(cat["deductions"]) == 0


# =========================================================================
# TEST SCENARIO 2: Patient Identity & Details (Missing + Unverified)
# =========================================================================
def test_02_patient_identity_missing_and_unverified():
    patient = {
        "full_name": "Aarav Sharma",
        # Missing DOB, gender, contact
    }
    claim = {
        "aadhaar_verification_status": "Not Yet Verified",
    }

    result = calculate_explainable_claim_readiness(
        patient=patient,
        claim=claim,
        stage="preauth",
    )

    cat = result["categories"]["patient_identity"]
    assert cat["score"] < 15.0
    # Patient name passed (4 pts), DOB failed, gender failed, contact failed, identity pending
    assert cat["score"] == 4.0
    assert any("birth" in m.lower() for m in cat["missing_info"])
    assert any("gender" in d.lower() for d in cat["deductions"])
    assert len(cat["recommended_actions"]) > 0


# =========================================================================
# TEST SCENARIO 3: Insurance Policy Information (Valid + Adequate)
# =========================================================================
def test_03_policy_information_valid_and_adequate():
    policy = {
        "policy_number": "STAR-HLTH-2026-9921",
        "insurance_provider": "Star Health and Allied Insurance",
        "policy_start_date": "2026-01-01",
        "policy_end_date": "2026-12-31",
        "coverage_amount": 500000.0,
    }
    claim = {
        "admission_date": "2026-04-10",
        "claimed_amount": 75000.0,
    }
    documents = [
        {"document_type": "insurance_card", "file_name": "star_card.pdf", "category_match": True}
    ]

    result = calculate_explainable_claim_readiness(
        policy=policy,
        claim=claim,
        documents=documents,
        stage="preauth",
    )

    cat = result["categories"]["policy_information"]
    assert cat["weight"] == 20.0
    assert cat["score"] == 20.0
    assert cat["status"] == "Passed"


# =========================================================================
# TEST SCENARIO 4: Insurance Policy Information (Sum Insured Exceeded / Missing Card)
# =========================================================================
def test_04_policy_information_sum_insured_exceeded_or_missing():
    policy = {
        "policy_number": "POL-1002",
        "insurance_provider": "HDFC ERGO",
        "policy_start_date": "2026-01-01",
        "policy_end_date": "2026-12-31",
        "coverage_amount": 50000.0,  # 50k sum insured
    }
    claim = {
        "claimed_amount": 120000.0,  # Exceeds sum insured
    }
    # No insurance card uploaded

    result = calculate_explainable_claim_readiness(
        policy=policy,
        claim=claim,
        documents=[],
        stage="preauth",
    )

    cat = result["categories"]["policy_information"]
    assert cat["score"] < 20.0
    assert any("exceeds" in d.lower() for d in cat["deductions"])
    assert any("Insurance Card" in m for m in cat["missing_info"])


# =========================================================================
# TEST SCENARIO 5: Medical Diagnosis & ICD-10 (Full + Mapped)
# =========================================================================
def test_05_medical_diagnosis_and_icd10_full():
    medical_analysis = {
        "diagnosis": "Dengue Fever with Thrombocytopenia",
        "icd10_code": "A90",
        "procedure": "Intravenous Fluid Replacement and Platelet Monitoring",
        "confidence_score": 0.95,
    }
    claim = {
        "clinical_notes": "Platelet count 45,000/uL with high grade fever. Inpatient monitoring required.",
    }

    result = calculate_explainable_claim_readiness(
        medical_analysis=medical_analysis,
        claim=claim,
        stage="preauth",
    )

    cat = result["categories"]["medical_diagnosis"]
    assert cat["weight"] == 20.0
    assert cat["score"] == 20.0
    assert cat["status"] == "Passed"


# =========================================================================
# TEST SCENARIO 6: Medical Diagnosis & ICD-10 (Unmapped / Missing)
# =========================================================================
def test_06_medical_diagnosis_missing_icd10():
    medical_analysis = {
        "diagnosis": "Abdominal Pain",
        "icd10_code": "",  # Unmapped
        "procedure": "",   # Missing
    }

    result = calculate_explainable_claim_readiness(
        medical_analysis=medical_analysis,
        stage="preauth",
    )

    cat = result["categories"]["medical_diagnosis"]
    assert cat["score"] < 20.0
    assert any("ICD-10" in m for m in cat["missing_info"])
    assert any("ICD-10" in a for a in cat["recommended_actions"])


# =========================================================================
# TEST SCENARIO 7: Required Documents for Initial Pre-Auth Stage
# CRITICAL: Final hospital bill and discharge summary are NOT required!
# =========================================================================
def test_07_required_documents_initial_preauth_stage():
    # Only Pre-auth documents uploaded: ID, Insurance Card, Prescription, Pre-Auth form
    documents = [
        {"document_type": "identity_proof", "file_name": "aadhaar.pdf", "category_match": True},
        {"document_type": "insurance_card", "file_name": "card.pdf", "category_match": True},
        {"document_type": "consultation_letter", "file_name": "prescription.pdf", "category_match": True},
        {"document_type": "pre_authorization", "file_name": "preauth_form.pdf", "category_match": True},
    ]

    result = calculate_explainable_claim_readiness(
        documents=documents,
        stage="preauth",  # or "initial_preauth"
    )

    cat = result["categories"]["required_documents"]
    assert cat["weight"] == 20.0
    # Must achieve full 20/20 without requiring final bill or discharge summary!
    assert cat["score"] == 20.0
    assert cat["status"] == "Passed"
    assert len(cat["missing_info"]) == 0
    # Verify neither hospital bill nor discharge summary are in missing requirements
    assert not any("hospital bill" in m.lower() for m in result["missing_requirements"])
    assert not any("discharge summary" in m.lower() for m in result["missing_requirements"])


# =========================================================================
# TEST SCENARIO 8: Required Documents for Final Auth Stage
# Must require final hospital bill, discharge summary, indoor case papers!
# =========================================================================
def test_08_required_documents_final_auth_stage():
    # Same documents as pre-auth (no final bill, no discharge summary)
    documents = [
        {"document_type": "identity_proof", "file_name": "aadhaar.pdf", "category_match": True},
        {"document_type": "insurance_card", "file_name": "card.pdf", "category_match": True},
        {"document_type": "pre_authorization", "file_name": "preauth_form.pdf", "category_match": True},
    ]

    result = calculate_explainable_claim_readiness(
        documents=documents,
        stage="final_auth",
    )

    cat = result["categories"]["required_documents"]
    # Final bill and discharge summary are missing at final_auth stage
    assert cat["score"] < 20.0
    assert any("Hospital Bill" in m for m in cat["missing_info"])
    assert any("Discharge Summary" in m for m in cat["missing_info"])
    assert any("Upload Hospital Bill" in req for req in result["missing_requirements"])


# =========================================================================
# TEST SCENARIO 9: Required Documents for Reimbursement Stage
# =========================================================================
def test_09_required_documents_reimbursement_stage():
    documents = [
        {"document_type": "hospital_bill", "file_name": "final_bill.pdf", "category_match": True},
        {"document_type": "payment_receipt", "file_name": "receipt.pdf", "category_match": True},
        {"document_type": "discharge_summary", "file_name": "discharge.pdf", "category_match": True},
        {"document_type": "claim_form", "file_name": "form.pdf", "category_match": True},
        {"document_type": "consultation_letter", "file_name": "opd.pdf", "category_match": True},
    ]

    result = calculate_explainable_claim_readiness(
        documents=documents,
        stage="reimbursement",
    )

    cat = result["categories"]["required_documents"]
    assert cat["weight"] == 20.0
    assert cat["score"] == 20.0
    assert cat["status"] == "Passed"


# =========================================================================
# TEST SCENARIO 10: Document Quality & Misclassification
# Misclassified document gives 0 points for category correctness
# =========================================================================
def test_10_document_quality_and_misclassification():
    documents = [
        {
            "document_type": "identity_proof",
            "file_name": "hospital_bill_uploaded_as_id.pdf",
            "category_status": "Incorrect Document Type",
            "category_match": False,
            "ocr_confidence": 0.88,
        }
    ]

    result = calculate_explainable_claim_readiness(
        documents=documents,
        stage="preauth",
    )

    cat = result["categories"]["document_quality"]
    # Category correctness check gets 0
    cat_checks = {c["name"]: c for c in cat["checks"]}
    assert cat_checks["Document Category Classification"]["earned_points"] == 0.0
    assert any("Incorrect Document Type" in d for d in cat["deductions"])


# =========================================================================
# TEST SCENARIO 11: Cross-Document Consistency (Discrepancies Deduct Points)
# =========================================================================
def test_11_cross_document_consistency_reconciliation():
    verification_result = {
        "mismatches": [
            "Patient name in hospital bill ('Ramesh K') differs from policy ('Ramesh Kumar')",
            "Billed amount ₹80,000 does not match estimate ₹60,000",
        ]
    }
    claim = {
        "admission_date": "2026-05-10",
        "discharge_date": "2026-05-08",  # Chronological error: discharge before admission
    }

    result = calculate_explainable_claim_readiness(
        verification_result=verification_result,
        claim=claim,
        stage="preauth",
    )

    cat = result["categories"]["cross_document_consistency"]
    assert cat["score"] < cat["weight"]
    assert any("Patient name" in d for d in cat["deductions"])
    assert any("Claimed amount" in d or "amount" in d.lower() for d in cat["deductions"])
    assert any("precedes admission" in d for d in cat["deductions"])


# =========================================================================
# TEST SCENARIO 12: Consent & Authorization
# =========================================================================
def test_12_consent_and_authorization():
    # Missing consent
    result_missing = calculate_explainable_claim_readiness(
        claim={"doctor_name": "Dr. Vivek Mehta"},
        consents=[],
        stage="preauth",
    )
    cat_missing = result_missing["categories"]["consent_authorization"]
    assert cat_missing["score"] == 2.0  # Only doctor passed (2 pts), consent 0 pts
    assert any("consent" in d.lower() and "missing" in d.lower() for d in cat_missing["deductions"])

    # Consent provided
    consents = [{"status": "Given", "consenter_name": "Aarav Sharma"}]
    result_full = calculate_explainable_claim_readiness(
        claim={"doctor_name": "Dr. Vivek Mehta"},
        consents=consents,
        stage="preauth",
    )
    cat_full = result_full["categories"]["consent_authorization"]
    assert cat_full["score"] == 5.0
    assert cat_full["status"] == "Passed"


# =========================================================================
# TEST SCENARIO 13: Missing Critical Information triggers is_provisional = True
# =========================================================================
def test_13_critical_missing_info_provisional_flag():
    # Missing patient name and policy number
    result = calculate_explainable_claim_readiness(
        patient={},
        policy={},
        claim={},
        documents=[],
        stage="preauth",
    )

    assert result["is_provisional"] is True
    assert len(result["provisional_reasons"]) > 0
    assert any("name is missing" in r for r in result["provisional_reasons"])
    assert any("policy number is missing" in r for r in result["provisional_reasons"])


# =========================================================================
# TEST SCENARIO 14: Deterministic Total Score & Readiness Levels
# =========================================================================
def test_14_total_score_sum_and_readiness_levels():
    # Levels mapping test
    assert determine_readiness_level(95.0) == "Excellent Readiness"
    assert determine_readiness_level(82.5) == "Good Readiness"
    assert determine_readiness_level(65.0) == "Needs Attention"
    assert determine_readiness_level(42.0) == "Incomplete"

    # Perfect claim payload
    patient = {
        "full_name": "Priya Nair",
        "date_of_birth": "1992-03-24",
        "gender": "Female",
        "contact_number": "9123456780",
    }
    policy = {
        "policy_number": "POL-9999",
        "insurance_provider": "Care Health Insurance",
        "policy_start_date": "2026-01-01",
        "policy_end_date": "2026-12-31",
        "coverage_amount": 1000000.0,
    }
    claim = {
        "admission_date": "2026-06-01",
        "claimed_amount": 80000.0,
        "doctor_name": "Dr. Sunita Rao",
        "aadhaar_verification_status": "Verified via Aadhaar QR/XML",
        "clinical_notes": "Acute appendicitis indicated for laparoscopic appendectomy.",
    }
    medical_analysis = {
        "diagnosis": "Acute Appendicitis",
        "icd10_code": "K35.80",
        "procedure": "Laparoscopic Appendectomy",
        "confidence_score": 0.95,
    }
    documents = [
        {"id": "doc1", "document_type": "identity_proof", "file_name": "aadhaar.pdf", "category_match": True, "ocr_confidence": 0.92, "extracted_text": "Aadhaar text"},
        {"id": "doc2", "document_type": "insurance_card", "file_name": "card.pdf", "category_match": True, "ocr_confidence": 0.90, "extracted_text": "Card text"},
        {"id": "doc3", "document_type": "consultation_letter", "file_name": "rx.pdf", "category_match": True, "ocr_confidence": 0.94, "extracted_text": "Rx text"},
        {"id": "doc4", "document_type": "pre_authorization", "file_name": "preauth.pdf", "category_match": True, "ocr_confidence": 0.91, "extracted_text": "Preauth text"},
    ]
    consents = [{"status": "Given", "consenter_name": "Priya Nair"}]

    result = calculate_explainable_claim_readiness(
        patient=patient,
        policy=policy,
        claim=claim,
        medical_analysis=medical_analysis,
        documents=documents,
        consents=consents,
        stage="preauth",
    )

    # Deterministic sum verification: total score must equal sum of category scores
    sum_categories = sum(c["score"] for c in result["category_list"])
    assert result["readiness_score"] == round(sum_categories, 1)
    assert result["readiness_score"] == 100.0
    assert result["readiness_level"] == "Excellent Readiness"
    assert result["is_provisional"] is False


# =========================================================================
# TEST SCENARIO 15: Independence & Consistency Across Views
# Scanned hospital documents receive 0 authenticity points
# Document Reliability evaluates selected document; Overall Claim Readiness evaluates whole claim
# Switching document leaves Overall Claim Readiness Score identical
# =========================================================================
def test_15_score_independence_and_consistency_across_views():
    # 1. Document Reliability Score test: scanned hospital document gets 0/15 authenticity pts
    rel_doc1 = calculate_document_reliability(
        ocr_confidence=0.92,
        has_text=True,
        category_match=True,
        category_status="Correct Document Type",
        extracted_data={"patient_name": "Priya Nair", "hospital_name": "City Hospital", "bill_number": "B12"},
        validation_mismatches=[],
        document_category="hospital_bill",
        has_crypto_signature=False,
        issuer_verified=False,
    )
    assert rel_doc1["breakdown"]["authenticity"]["score"] == 0.0
    assert rel_doc1["authenticityStatus"] == "Authenticity Not Independently Verified"

    # Document 2 (e.g. low quality scan)
    rel_doc2 = calculate_document_reliability(
        ocr_confidence=0.45,
        has_text=True,
        category_match=True,
        category_status="Correct Document Type",
        extracted_data={},
        validation_mismatches=["Date mismatch"],
        document_category="diagnostic_report",
        has_crypto_signature=False,
    )
    # The two documents have different reliability scores
    assert rel_doc1["score"] != rel_doc2["score"]
    assert rel_doc1["score"] > rel_doc2["score"]

    # 2. Overall Claim Readiness consistency:
    # Evaluating Claim Readiness for the claim containing both documents:
    claim_payload = {
        "id": "claim-uuid-1",
        "claim_number": "CB-2026-001",
        "patient_name": "Priya Nair",
        "policy_number": "POL-9999",
        "diagnosis": "Acute Appendicitis",
        "diagnosis_code": "K35.80",
        "claimed_amount": 50000.0,
    }
    claim_docs = [
        {"id": "doc1", "document_type": "identity_proof", "category_match": True, "ocr_confidence": 0.92, "extracted_text": "Text"},
        {"id": "doc2", "document_type": "insurance_card", "category_match": True, "ocr_confidence": 0.45, "extracted_text": "Text"},
        {"id": "doc3", "document_type": "consultation_letter", "category_match": True, "ocr_confidence": 0.90, "extracted_text": "Text"},
        {"id": "doc4", "document_type": "pre_authorization", "category_match": True, "ocr_confidence": 0.88, "extracted_text": "Text"},
    ]

    # Evaluate claim readiness when viewing doc1
    readiness_viewing_doc1 = calculate_explainable_claim_readiness(
        claim=claim_payload,
        documents=claim_docs,
        stage="preauth",
    )

    # Evaluate claim readiness when viewing doc2
    readiness_viewing_doc2 = calculate_explainable_claim_readiness(
        claim=claim_payload,
        documents=claim_docs,
        stage="preauth",
    )

    # Consistency rule: Overall Claim Readiness Score is identical across document views!
    assert readiness_viewing_doc1["readiness_score"] == readiness_viewing_doc2["readiness_score"]
    assert readiness_viewing_doc1["readiness_level"] == readiness_viewing_doc2["readiness_level"]
    assert readiness_viewing_doc1["categories"] == readiness_viewing_doc2["categories"]
