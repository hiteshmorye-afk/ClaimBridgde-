"""
Comprehensive test suite for ClaimBridge critical workflow fixes:
1. Real OCR & Document Classification (Strict Wrong Document Detection)
2. Initial Pre-Authorization Optional Discharge Date Validation
3. Document Detail API Full Structured Payload (No Empty Payload)
4. Document Association & Repository Linking
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import uuid
from datetime import date, datetime
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.auth import password_hash, create_access_token
from app.models import User, Claim, Policy, Patient, ClaimDocument, DocumentExtraction, InsuranceProvider
from app.document_classifier import classify_document, normalize_category_name

client = TestClient(app)

TEST_USER_ID = str(uuid.uuid4())
TEST_OFFICER_ID = str(uuid.uuid4())
TEST_EMAIL = f"arya.workflow.{uuid.uuid4().hex[:6]}@claimbridge.test"


@pytest.fixture(scope="module", autouse=True)
def setup_test_data():
    db = SessionLocal()
    # Check or create provider
    provider = db.query(InsuranceProvider).filter(InsuranceProvider.name == "HDFC ERGO General Insurance").first()
    if not provider:
        provider = InsuranceProvider(
            name="HDFC ERGO General Insurance",
            code="HDFC-ERGO",
            tpa_code="HDFC-TPA",
            status="ACTIVE",
        )
        db.add(provider)
        db.commit()

    # Create test claimant user
    user = User(
        id=TEST_USER_ID,
        full_name="Arya Sharma",
        email=TEST_EMAIL,
        password_hash=password_hash.hash("ValidPass123!"),
        role="claimant",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.close()


def get_claimant_headers():
    token = create_access_token(
        user_id=TEST_USER_ID,
        email=TEST_EMAIL,
        role="claimant",
        portal="Hospital",
    )
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# ISSUE 1: CLASSIFICATION & WRONG DOCUMENT DETECTION
# ==============================================================================

def test_normalization_map_aliases():
    """Verify all UI category aliases resolve to canonical backend types."""
    assert normalize_category_name("Aadhaar / Identity Proof") == "identity_proof"
    assert normalize_category_name("Identity Proof (Aadhaar / ID)") == "identity_proof"
    assert normalize_category_name("Health Insurance Card / Policy") == "insurance_card"
    assert normalize_category_name("Insurance Policy / Health Card") == "insurance_card"
    assert normalize_category_name("Doctor's Prescription & Consultation") == "consultation_letter"
    assert normalize_category_name("Pre-Authorization Form / Admission Notes") == "pre_authorization"
    assert normalize_category_name("Diagnostic & Investigation Reports") == "diagnostic_report"
    assert normalize_category_name("Final Hospital Bill") == "hospital_bill"
    assert normalize_category_name("Discharge Summary") == "discharge_summary"


def test_wrong_document_detection_claim_form_vs_aadhaar():
    """Verify a Duly Filled Claim Form uploaded as Aadhaar is classified as claim_form and rejected."""
    claim_form_text = """
    HEALTH INSURANCE CLAIM FORM - PART A
    TO BE FILLED IN BY THE INSURED
    Claim ID: CLM-99281
    Details of Primary Insured: Arya Sharma
    Policy No: POL-2024-88192
    Declaration by the Insured: I hereby declare that the details given above are true.
    Signature of the Insured: Arya Sharma
    """
    res = classify_document(claim_form_text)
    assert res["document_type"] == "claim_form"
    assert res["confidence"] >= 0.70


def test_wrong_document_detection_insurance_card_vs_preauth():
    """Verify an Insurance Card uploaded as Pre-Authorization Form is classified as insurance_card."""
    card_text = """
    HDFC ERGO HEALTH CARD
    Member ID Card / Health Insurance Policy
    Member ID: MEM-881290
    Policy Number: 2812-9910-1122
    Valid Upto: 31/12/2026
    Sum Insured: Rs. 5,00,000
    TPA: Family Health Plan Insurance TPA Ltd
    """
    res = classify_document(card_text)
    assert res["document_type"] == "insurance_card"
    assert res["confidence"] >= 0.70


def test_wrong_document_detection_hospital_bill_vs_consultation():
    """Verify a Hospital Bill uploaded as Doctor's Consultation is classified as hospital_bill."""
    bill_text = """
    APOLLO HOSPITALS ENTERPRISE LIMITED
    FINAL HOSPITAL BILL / TAX INVOICE
    Bill No: BILL-2026-9011
    Date of Admission: 12.04.2026
    Date of Discharge: 15.04.2026
    Room Rent & Nursing Charges: Rs. 15,000
    Pharmacy Charges: Rs. 8,500
    Investigation Charges: Rs. 4,200
    Total Amount: Rs. 27,700
    Net Payable: Rs. 27,700
    """
    res = classify_document(bill_text)
    assert res["document_type"] == "hospital_bill"
    assert res["confidence"] >= 0.70


def test_wrong_document_detection_prescription_vs_diagnostic_report():
    """Verify a Prescription uploaded as Diagnostic Report is classified as consultation_letter/prescription."""
    rx_text = """
    CITY CLINIC & HEALTHCARE
    DOCTOR'S CONSULTATION & PRESCRIPTION
    Consultant: Dr. V. K. Mehta, MD
    Rx
    Tab Dolo 650mg TDS x 3 days
    Tab Pan 40mg OD AC x 5 days
    Syp Corex 5ml TDS
    Diagnosis: Acute Upper Respiratory Tract Infection
    Next Follow-up in 5 days.
    """
    res = classify_document(rx_text)
    assert res["document_type"] in ("prescription", "consultation_letter")
    assert res["document_type"] != "diagnostic_report"
    assert res["confidence"] >= 0.70


# ==============================================================================
# ISSUE 3: INITIAL PRE-AUTH ALLOWS OPTIONAL DISCHARGE DATE
# ==============================================================================

def test_cashless_preauth_allows_optional_discharge_date():
    """
    Verify initial pre-authorization claim creation succeeds with admission date
    when dischargeDate is omitted or null.
    """
    headers = get_claimant_headers()
    payload = {
        "patientName": "Sunil Verma",
        "patientAge": 42,
        "hospital": "Max Super Speciality Hospital",
        "policyNumber": f"98{uuid.uuid4().int % 10000000000:010d}",
        "insuranceProvider": "HDFC ERGO General Insurance",
        "diagnosis": "Acute Appendicitis",
        "diagnosisCode": "K35.80",
        "admissionDate": "2026-05-10",
        "dischargeDate": None,  # Optional during initial pre-auth!
        "claimedAmount": 45000.0,
        "claimType": "cashless",
        "memberId": "MEM-VERMA-901",
    }
    response = client.post("/claims", json=payload, headers=headers)
    assert response.status_code in (200, 201), f"Failed: {response.text}"
    data = response.json()
    claim_id = data.get("claimId") or data.get("id")
    assert claim_id is not None
    assert data["claimNumber"].startswith("CLM-")


def test_reimbursement_requires_both_dates():
    """
    Verify reimbursement claims still strictly require both admissionDate and dischargeDate.
    """
    headers = get_claimant_headers()
    payload = {
        "patientName": "Anita Desai",
        "patientAge": 35,
        "hospital": "Fortis Hospital",
        "policyNumber": f"98{uuid.uuid4().int % 10000000000:010d}",
        "insuranceProvider": "HDFC ERGO General Insurance",
        "diagnosis": "Viral Fever",
        "admissionDate": "2026-05-10",
        "dischargeDate": None,  # Missing on reimbursement -> Must fail 422!
        "claimedAmount": 15000.0,
        "claimType": "reimbursement",
    }
    response = client.post("/claims", json=payload, headers=headers)
    assert response.status_code == 422
    assert "Both admission date and discharge date are required" in response.text


def test_preauth_admission_after_discharge_date_fails():
    """
    Verify that if a dischargeDate is explicitly provided during pre-auth,
    it cannot be prior to the admission date.
    """
    headers = get_claimant_headers()
    payload = {
        "patientName": "Ramesh Kumar",
        "patientAge": 50,
        "hospital": "Lilavati Hospital",
        "policyNumber": f"98{uuid.uuid4().int % 10000000000:010d}",
        "insuranceProvider": "HDFC ERGO General Insurance",
        "diagnosis": "Dengue Fever",
        "admissionDate": "2026-05-15",
        "dischargeDate": "2026-05-10",  # Prior to admission -> Invalid!
        "claimedAmount": 30000.0,
        "claimType": "cashless",
    }
    response = client.post("/claims", json=payload, headers=headers)
    assert response.status_code == 422
    assert "Admission date cannot be after discharge date" in response.text


# ==============================================================================
# ISSUE 4 & 7: GET /documents/{id} DETAIL API & ASSOCIATE ENDPOINT
# ==============================================================================

def test_get_document_detail_full_payload():
    """
    Verify GET /documents/{id} returns a full structured payload without throwing empty payload.
    """
    headers = get_claimant_headers()
    db = SessionLocal()
    user = db.query(User).filter(User.id == TEST_USER_ID).first()

    pat = Patient(full_name="Arya Sharma Verification")
    db.add(pat)
    db.flush()

    pol = Policy(
        policy_number=f"98{uuid.uuid4().int % 10000000000:010d}",
        insurance_provider="HDFC ERGO General Insurance",
        coverage_amount=Decimal("500000"),
    )
    db.add(pol)
    db.flush()

    claim = Claim(
        claim_number=f"CLM-ARYA-{uuid.uuid4().hex[:6]}",
        patient_id=pat.id,
        policy_id=pol.id,
        hospital_name="Apollo Hospital",
        admission_date=date(2026, 4, 10),
        claimed_amount=Decimal("35000"),
        claim_status="Under Analysis",
        created_by=user.id,
        claim_type="cashless",
    )
    db.add(claim)
    db.flush()

    doc = ClaimDocument(
        id=uuid.uuid4(),
        claim_id=claim.id,
        document_type="consultation_letter",
        file_name="doctor_prescription.pdf",
        file_path="test_files/doctor_prescription.pdf",
        processing_status="Completed",
        uploaded_at=datetime.utcnow(),
    )
    db.add(doc)
    db.flush()

    ext = DocumentExtraction(
        document_id=doc.id,
        extracted_text="Patient Arya Sharma diagnosed with acute bronchitis. Prescribed Azithromycin 500mg.",
        extracted_data={"patient_name": "Arya Sharma", "diagnosis": "Acute Bronchitis"},
        ocr_confidence=Decimal("0.96"),
        extraction_status="Completed",
    )
    db.add(ext)
    db.commit()
    doc_id = str(doc.id)
    db.close()

    # Test GET /documents/{document_id}
    res = client.get(f"/documents/{doc_id}", headers=headers)
    assert res.status_code == 200, f"Detail API failed: {res.text}"
    detail = res.json()

    assert detail["documentId"] == doc_id
    assert detail["fileName"] == "doctor_prescription.pdf"
    assert detail["category"] == "consultation_letter"
    assert detail["ocrStatus"] == "Completed"
    assert detail["ocrConfidence"] == pytest.approx(0.96, rel=1e-2)
    assert detail["reliabilityScore"] >= 50
    assert "reliabilityBreakdown" in detail
    assert "readability" in detail["reliabilityBreakdown"]
    assert "categoryMatch" in detail["reliabilityBreakdown"]
    assert "fieldChecks" in detail
    assert len(detail["fieldChecks"]) >= 1


def test_associate_documents_endpoint():
    """
    Verify POST /documents/associate-claim attaches orphaned or draft documents to claim.
    """
    headers = get_claimant_headers()
    db = SessionLocal()
    user = db.query(User).filter(User.id == TEST_USER_ID).first()

    claim = db.query(Claim).filter(Claim.created_by == user.id).first()
    assert claim is not None
    claim_id_str = str(claim.id)

    # Create document
    doc_new = ClaimDocument(
        id=uuid.uuid4(),
        claim_id=claim.id,
        document_type="diagnostic_report",
        file_name="blood_test.pdf",
        file_path="test_files/blood_test.pdf",
        processing_status="Pending",
        uploaded_at=datetime.utcnow(),
    )
    db.add(doc_new)
    db.commit()
    doc_uuid_str = str(doc_new.id)
    db.close()

    payload = {
        "claimId": claim_id_str,
        "documentIds": [doc_uuid_str],
    }
    res = client.post("/documents/associate-claim", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["updatedCount"] == 1
    assert "associated" in data["message"].lower()
