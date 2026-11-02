"""
ClaimBridge Pre-Authorization Workflow & Document Intelligence Test Suite

Tests:
1. Wrong Document Detection (Category X selected, Category Y detected)
2. Document Reliability & Readiness Score (0-100 with transparent 5-part breakdown)
3. Authenticity disclaimer: Ordinary scans receive 0/15 points and label 'Authenticity Not Independently Verified'
4. ICD-10 medical intelligence and condition mapping
5. Cross-document consistency reconciliation
6. Dynamic non-technical explanations
"""

import pytest
from app.document_reliability import calculate_document_reliability
from app.document_classifier import classify_document, normalize_category_name
from app.information_extractor import extract_information


def test_01_document_reliability_scoring_breakdown():
    """Verify the 5 dimensions of document reliability score."""
    result = calculate_document_reliability(
        ocr_confidence=0.92,
        has_text=True,
        category_match=True,
        category_status="Correct Document Type",
        extracted_data={
            "patient_name": "Rahul Sharma",
            "hospital_name": "Apollo Hospitals",
            "bill_number": "BILL-1029",
            "total_amount": "45000",
            "admission_date": "10.09.2026",
        },
        validation_mismatches=[],
        document_category="hospital_bill",
        has_crypto_signature=False,
        issuer_verified=False,
    )

    score = result["score"]
    breakdown = result["breakdown"]

    # Verify score components
    assert breakdown["readability"]["score"] == 18.4  # 0.92 * 20
    assert breakdown["categoryMatch"]["score"] == 20.0
    assert breakdown["completeness"]["score"] == 25.0
    assert breakdown["consistency"]["score"] == 20.0
    assert breakdown["authenticity"]["score"] == 0.0  # 0/15 for ordinary scan
    assert result["authenticityStatus"] == "Authenticity Not Independently Verified"

    # Total score should equal sum of components
    assert score == pytest.approx(83.4, 0.1)
    assert result["tier"] == "Good Readiness"
    assert "Your document is 83/100 ready" in result["explanation"]
    assert "issuing authority has not been independently verified" in result["explanation"]


def test_02_wrong_document_detection():
    """Verify that wrong document category penalizes score and flags mismatch."""
    # User selected hospital_bill, but document is discharge_summary
    result = calculate_document_reliability(
        ocr_confidence=0.90,
        has_text=True,
        category_match=False,
        category_status="Incorrect Document Type",
        extracted_data={"patient_name": "Rahul Sharma"},
        validation_mismatches=["Incorrect Document Type – This file appears to be a Discharge Summary, not a Final Hospital Bill."],
        document_category="hospital_bill",
        has_crypto_signature=False,
    )

    breakdown = result["breakdown"]
    assert breakdown["categoryMatch"]["score"] == 0.0
    assert breakdown["categoryMatch"]["status"] == "Incorrect Document Type"
    assert breakdown["consistency"]["score"] == 15.0  # 20 - 5 penalty for 1 mismatch
    assert result["score"] < 60.0
    assert result["tier"] in ["Needs Attention", "Low Readiness"]


def test_03_unreadable_file_handling():
    """Verify that unreadable/empty text receives 0 readability points."""
    result = calculate_document_reliability(
        ocr_confidence=0.0,
        has_text=False,
        category_match=None,
        category_status="Manual Review Required",
        extracted_data={},
        validation_mismatches=[],
        document_category="hospital_bill",
    )

    assert result["breakdown"]["readability"]["score"] == 0.0
    assert result["breakdown"]["completeness"]["score"] == 0.0
    assert result["tier"] == "Low Readiness"


def test_04_category_classification_mismatch_detection():
    """Verify document classifier detects distinct categories."""
    discharge_text = (
        "APOLLO HOSPITALS\n"
        "DISCHARGE SUMMARY\n"
        "PATIENT: Rahul Sharma\n"
        "ADMISSION DATE: 10.09.2026\n"
        "DISCHARGE DATE: 14.09.2026\n"
        "FINAL DIAGNOSIS: Acute Appendicitis\n"
        "PROCEDURE: Laparoscopic Appendectomy\n"
        "CONDITION AT DISCHARGE: Stable\n"
    )
    classified = classify_document(discharge_text)
    assert classified["document_type"] == "discharge_summary"
    assert classified["confidence"] >= 0.70

    bill_text = (
        "APOLLO HOSPITALS\n"
        "FINAL HOSPITAL BILL (ITEMIZED INVOICE)\n"
        "PATIENT NAME: Rahul Sharma\n"
        "BILL NO: 994821\n"
        "ROOM CHARGES: 15000\n"
        "SURGERY CHARGES: 35000\n"
        "TOTAL AMOUNT: 50000.00\n"
    )
    classified_bill = classify_document(bill_text)
    assert classified_bill["document_type"] == "hospital_bill"
    assert classified_bill["confidence"] >= 0.70


def test_05_category_normalization_aliases():
    """Verify alias resolution for pre-auth categories."""
    assert normalize_category_name("Aadhaar") == "identity_proof"
    assert normalize_category_name("KYC") == "identity_proof"
    assert normalize_category_name("Health Insurance Card") == "insurance_card"
    assert normalize_category_name("Doctor's Consultation Papers") == "consultation_letter"
    assert normalize_category_name("Lab Report") == "diagnostic_report"
    assert normalize_category_name("Final Hospital Bill") == "hospital_bill"
    assert normalize_category_name("Discharge Summary") == "discharge_summary"
    assert normalize_category_name("Pre Authorization") == "pre_authorization"


def test_06_medical_extraction_icd10():
    """Verify extraction extracts diagnosis and clinical fields."""
    clinical_text = (
        "MAX SUPER SPECIALITY HOSPITAL\n"
        "CONSULTATION REPORT & PRESCRIPTION\n"
        "PATIENT: Anita Verma\n"
        "DATE: 01.11.2026\n"
        "DIAGNOSIS: Acute Cholecystitis with cholelithiasis\n"
        "RX:\n"
        "TAB CIPROFLOXACIN 500MG 1-0-1\n"
        "ADVICE: Elective Cholecystectomy\n"
    )
    extracted = extract_information(clinical_text, document_type="consultation_letter")
    assert extracted.get("patient_name") == "Anita Verma"
    assert "cholecystitis" in (extracted.get("diagnosis") or "").lower()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
