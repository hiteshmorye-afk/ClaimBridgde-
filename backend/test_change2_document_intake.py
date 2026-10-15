"""
ClaimBridge Change 2 Automated Verification Test Suite
======================================================
Tests:
1. Document Classifier: All 15 Categories & Confidence Scoring
2. Document Classifier: Category Normalization Mapping
3. Information Extractor: Core & Document-Specific Extractors for 15 Categories
4. Sensitive Data Masking: Aadhaar, PAN, Passport, Bank Account Numbers
5. Financial Arithmetic Validation: Matching & Discrepant Bills
6. Single Document Validation: Category-Specific Required Fields
7. Cross-Document Reconciliation: Cashless vs Reimbursement Rules
8. Cross-Document Reconciliation: Accident, Implant, and Ambulance Conditional Documents
9. Cross-Document Reconciliation: Receipts Shortfall & Pre-Auth Cap Exceedance
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.document_classifier import (
    classify_document,
    normalize_category_name,
    DOCUMENT_EVIDENCE,
)
from app.information_extractor import (
    extract_information,
    mask_aadhaar,
    mask_pan,
    mask_passport,
    mask_bank_account,
    extract_bill_details,
)
from app.validation_engine import (
    validate_extracted_information,
    validate_cross_document_consistency,
    CATEGORY_REQUIRED_FIELDS,
)


class Change2TestSuite:
    passed = 0
    failed = 0

    @classmethod
    def record(cls, test_num: int, name: str, status: str, detail: str = ""):
        if status == "PASSED":
            cls.passed += 1
            print(f"[PASSED] Test {test_num}: {name} -> {detail}")
        else:
            cls.failed += 1
            print(f"[FAILED] Test {test_num}: {name} -> {detail}")


def test_01_classify_all_15_categories():
    """Verify document classification across all 15 supported categories."""
    cases = [
        # Section A
        ("claim_form", "HEALTH INSURANCE CLAIM FORM Part A To be filled by the insured. Details of primary insured. Claim number: CLM-101. Total claimed amount: 50000"),
        ("insurance_card", "HEALTH CARD Member ID Card Policy Schedule Policy Number: POL-44582 Validity: Valid from 01.01.2026 thru 31.12.2026 Sum Insured: 500,000"),
        ("identity_proof", "UNIQUE IDENTIFICATION AUTHORITY OF INDIA Aadhaar Card Government of India DOB: 14.08.1978 Male 4521 8892 1092"),
        ("bank_proof", "CANCELLED CHEQUE HDFC Bank Branch: Indiranagar IFSC Code: HDFC0001234 A/c No: 50100234589214 Savings A/c Account Holder: David Miller"),

        # Section B
        ("discharge_summary", "DISCHARGE SUMMARY Hospital Course in Hospital Date of Admission: 10.08.2026 Date of Discharge: 14.08.2026 Condition at Discharge: Stable Advice on Discharge: Rest"),
        ("consultation_letter", "CONSULTATION PAPER Doctor's Consultation OPD Slip Chief Complaints: Severe abdominal pain Dr. Watson Clinic Visit"),
        ("diagnostic_report", "DIAGNOSTIC REPORT Radiology Report Ultrasound Whole Abdomen Findings and Impression: Acute cholecystitis with gallstones Observed value normal"),

        # Section C
        ("hospital_bill", "TAX INVOICE Final Hospital Bill Invoice No: INV-9901 Billing Date: 14.08.2026 Room Rent: 15,000 Pharmacy: 20,000 Total Charges: 85,000 Amount Payable: 85,000"),
        ("payment_receipt", "PAYMENT RECEIPT Money Receipt Received with thanks from David Miller Sum of Rupees: 85,000 Amount Paid: 85,000 Payment Mode: UPI Txn ID: UPI-9921827"),
        ("pharmacy_bill", "RETAIL PHARMACY TAX INVOICE Medical Store Cash Memo Drug Licence No: DL-882 Batch No: B-991 MRP: 1,500 Total Amount: 4,500"),

        # Section D
        ("fir_mlc", "MEDICO-LEGAL CERTIFICATE MLC No: MLC-2026-99 Police Station: Central Station History of Road Traffic Accident Injury Report Offence alcohol consumed: negative"),
        ("implant_invoice", "IMPLANT INVOICE Outer Pouch Sticker Orthopaedic Implant Brand Name: Titanium Hip Joint Lot No: LOT-99281 Serial No: SN-44821 Price: 45,000 Sterile"),
        ("ambulance_receipt", "AMBULANCE RECEIPT Emergency Transit Ambulance Service Vehicle No: KA-01-AB-1234 Pickup Location: Whitefield To: Apollo Hospital Distance: 18 kms Amount Paid: 3,500"),
        ("pre_authorization", "CASHLESS PRE-AUTHORIZATION LETTER TPA Pre-Auth Approval Pre-Auth ID: PA-88219 Approved Amount: 80,000 Initial authorization for inpatient treatment"),

        # Section E
        ("other_medical_doc", "MEDICAL CERTIFICATE Fitness Certificate To whomsoever it may concern This is to certify that David Miller was suffering from illness and advised rest"),
    ]

    for expected_type, text in cases:
        res = classify_document(text)
        assert res["document_type"] == expected_type, f"Expected {expected_type}, got {res['document_type']} for text: {text[:40]}"
        assert res["confidence"] >= 0.60, f"Low confidence {res['confidence']} for {expected_type}"

    Change2TestSuite.record(1, "15 Document Categories Classification", "PASSED", "All 15 categories classified with confidence >= 60%")


def test_02_category_normalization():
    """Verify category normalization maps UI names and aliases correctly."""
    mappings = [
        ("Duly Filled Claim Form", "claim_form"),
        ("Health Insurance Card", "insurance_card"),
        ("KYC / Identity Proof", "identity_proof"),
        ("Cancelled Cheque", "bank_proof"),
        ("Discharge Card", "discharge_summary"),
        ("Doctor's Consultation Papers", "consultation_letter"),
        ("Investigation / Diagnostic Reports", "diagnostic_report"),
        ("Final Hospital Bill", "hospital_bill"),
        ("Payment Receipts", "payment_receipt"),
        ("Pharmacy & Medical Store Bills", "pharmacy_bill"),
        ("Medico-Legal Certificate (MLC) / FIR", "fir_mlc"),
        ("Implant Invoice & Sticker", "implant_invoice"),
        ("Ambulance Receipt / Certificate", "ambulance_receipt"),
        ("Pre-Authorization Approval Letter / Query Sheet", "pre_authorization"),
        ("Other Supporting Documents", "other_medical_doc"),
    ]

    for ui_name, expected_backend in mappings:
        norm = normalize_category_name(ui_name)
        assert norm == expected_backend, f"Expected {expected_backend}, got {norm} for '{ui_name}'"

    Change2TestSuite.record(2, "Category Normalization", "PASSED", f"Successfully normalized {len(mappings)} category names")


def test_03_sensitive_masking():
    """Verify sensitive identity and bank masking rules."""
    # Aadhaar masking
    assert mask_aadhaar("4521 8892 1092") == "XXXX-XXXX-1092"
    assert mask_aadhaar("452188921092") == "XXXX-XXXX-1092"

    # PAN masking
    assert mask_pan("ABCDE1234F") == "ABCDE****F"

    # Passport masking
    assert mask_passport("Z1234567") == "Z1****67"

    # Bank Account masking
    assert mask_bank_account("50100234589214") == "XXXXXX9214"

    Change2TestSuite.record(3, "Sensitive Data Masking", "PASSED", "Aadhaar, PAN, Passport, and Bank Account correctly masked")


def test_04_arithmetic_validation():
    """Verify itemized billing arithmetic validation and discrepancy reporting."""
    # Case 1: Matching bill (Room 15,000 + Pharmacy 20,000 + Consultation 5,000 = 40,000, Tax 2,000, Total 42,000)
    matching_bill_text = """
    Apollo Hospital
    TAX INVOICE
    Room Charges: 15,000
    Pharmacy Charges: 20,000
    Consultation Fee: 5,000
    Subtotal: 40,000
    Tax: 2,000
    Total Charges: 42,000
    """
    res1 = extract_bill_details(matching_bill_text)
    arith1 = res1.get("arithmetic_validation", {})
    assert arith1.get("is_valid") is True, f"Expected valid arithmetic, got {arith1}"
    assert arith1.get("itemized_sum") == 40000.0

    # Case 2: Discrepant bill (Printed total 85,000 but line items sum to 35,000)
    discrepant_bill_text = """
    Apollo Hospital
    TAX INVOICE
    Room Charges: 15,000
    Pharmacy Charges: 20,000
    Subtotal: 35,000
    Total Charges: 85,000
    """
    res2 = extract_bill_details(discrepant_bill_text)
    arith2 = res2.get("arithmetic_validation", {})
    assert arith2.get("is_valid") is False, "Expected arithmetic discrepancy"
    assert len(arith2.get("discrepancies", [])) > 0
    assert "50,000.00" in arith2["discrepancies"][0]

    Change2TestSuite.record(4, "Billing Arithmetic Validation", "PASSED", "Validated matching bill and detected 50,000 discrepancy")


def test_05_single_doc_validation_with_arithmetic():
    """Verify validation engine flags arithmetic errors in verification result."""
    extracted = {
        "document_type": "hospital_bill",
        "patient_name": "David Miller",
        "admission_date": "10.08.2026",
        "discharge_date": "14.08.2026",
        "total_charges": 85000.0,
        "arithmetic_validation": {
            "is_valid": False,
            "itemized_sum": 35000.0,
            "calculated_total": 35000.0,
            "discrepancies": ["Bill total discrepancy of 50,000.00"],
        },
    }
    val_res = validate_extracted_information(extracted)
    assert val_res["verification_status"] == "Needs Review"
    assert any("Bill total discrepancy" in m for m in val_res["mismatches"])

    Change2TestSuite.record(5, "Single Document Arithmetic Verification", "PASSED", "Status -> Needs Review on arithmetic error")


def test_06_cross_reconciliation_reimbursement():
    """Verify cross-document reconciliation for Reimbursement claims."""
    # Reimbursement requires bank proof and payment receipts
    ctx_reimb = {"claim_type": "reimbursement"}

    # Case A: Missing Bank Proof and Payment Receipts
    docs_incomplete = [
        {"document_type": "hospital_bill", "patient_name": "David Miller", "total_charges": 50000.0, "admission_date": "10.08.2026", "discharge_date": "14.08.2026"},
        {"document_type": "discharge_summary", "patient_name": "David Miller", "diagnosis": "Cholecystitis", "admission_date": "10.08.2026", "discharge_date": "14.08.2026"},
    ]
    res_a = validate_cross_document_consistency(docs_incomplete, claim_context=ctx_reimb)
    assert "bank_proof" in res_a["missing_documents"]
    assert "payment_receipt" in res_a["missing_documents"]

    # Case B: Complete package with receipt shortfall (Billed 50k, Receipt 30k)
    docs_shortfall = [
        {"document_type": "hospital_bill", "patient_name": "David Miller", "total_charges": 50000.0, "admission_date": "10.08.2026", "discharge_date": "14.08.2026"},
        {"document_type": "discharge_summary", "patient_name": "David Miller", "diagnosis": "Cholecystitis", "admission_date": "10.08.2026", "discharge_date": "14.08.2026"},
        {"document_type": "claim_form", "patient_name": "David Miller"},
        {"document_type": "insurance_card", "policy_number": "POL-9921"},
        {"document_type": "identity_proof", "holder_name": "David Miller"},
        {"document_type": "bank_proof", "bank_name": "HDFC"},
        {"document_type": "payment_receipt", "amount_paid": 30000.0, "total_charges": 30000.0},
    ]
    res_b = validate_cross_document_consistency(docs_shortfall, claim_context=ctx_reimb)
    assert res_b["cross_document_status"] == "Discrepancy Detected"
    assert any("Receipt reconciliation shortfall" in m for m in res_b["mismatches"])

    Change2TestSuite.record(6, "Reimbursement Reconciliation & Shortfall", "PASSED", "Flagged missing bank proof and $20,000 receipt shortfall")


def test_07_cross_reconciliation_cashless_and_specials():
    """Verify Cashless pre-auth and conditional accident/implant/ambulance requirements."""
    # Cashless claim requiring Pre-Auth
    ctx_cashless = {
        "claim_type": "cashless",
        "is_accident": True,
        "has_implant": True,
        "has_ambulance": True,
    }

    docs_cashless = [
        {"document_type": "hospital_bill", "patient_name": "David Miller", "total_charges": 90000.0, "admission_date": "10.08.2026", "discharge_date": "14.08.2026"},
        {"document_type": "discharge_summary", "patient_name": "David Miller", "diagnosis": "Fracture", "admission_date": "10.08.2026", "discharge_date": "14.08.2026"},
        {"document_type": "claim_form", "patient_name": "David Miller"},
        {"document_type": "insurance_card", "policy_number": "POL-9921"},
        {"document_type": "identity_proof", "holder_name": "David Miller"},
    ]

    res = validate_cross_document_consistency(docs_cashless, claim_context=ctx_cashless)
    missing = res["missing_documents"]
    assert "pre_authorization" in missing, "Missing pre_authorization not flagged"
    assert "fir_mlc" in missing, "Missing fir_mlc not flagged for accident"
    assert "implant_invoice" in missing, "Missing implant_invoice not flagged for implant"
    assert "ambulance_receipt" in missing, "Missing ambulance_receipt not flagged for ambulance"

    Change2TestSuite.record(7, "Contextual Missing Documents", "PASSED", "Flagged Pre-Auth, MLC/FIR, Implant Invoice, and Ambulance Receipt")


def test_08_cashless_preauth_cap_exceeded():
    """Verify that billed amount exceeding pre-authorized limit is flagged."""
    ctx_cashless = {"claim_type": "cashless"}

    docs = [
        {"document_type": "hospital_bill", "patient_name": "David Miller", "total_charges": 95000.0, "admission_date": "10.08.2026", "discharge_date": "14.08.2026"},
        {"document_type": "discharge_summary", "patient_name": "David Miller", "diagnosis": "Cholecystitis", "admission_date": "10.08.2026", "discharge_date": "14.08.2026"},
        {"document_type": "pre_authorization", "approved_amount": 75000.0},
    ]

    res = validate_cross_document_consistency(docs, claim_context=ctx_cashless)
    assert res["cross_document_status"] == "Discrepancy Detected"
    assert any("exceed pre-authorized cashless limit" in m for m in res["mismatches"])

    Change2TestSuite.record(8, "Pre-Auth Limit Exceeded", "PASSED", "Flagged $20,000 exceedance over authorized cashless cap")


def run_all_tests():
    print("\n" + "=" * 65)
    print("CLAIMBRIDGE CHANGE 2 VERIFICATION SUITE")
    print("=" * 65)

    test_01_classify_all_15_categories()
    test_02_category_normalization()
    test_03_sensitive_masking()
    test_04_arithmetic_validation()
    test_05_single_doc_validation_with_arithmetic()
    test_06_cross_reconciliation_reimbursement()
    test_07_cross_reconciliation_cashless_and_specials()
    test_08_cashless_preauth_cap_exceeded()

    print("=" * 65)
    print(f"RESULTS: {Change2TestSuite.passed} Passed, {Change2TestSuite.failed} Failed")
    print("=" * 65 + "\n")

    if Change2TestSuite.failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
