"""
ClaimBridge Form Validation & Clinical Mapping Acceptance Test Suite
Verifies backend server-side validation rules and clinical diagnosis mapping.
"""

import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Claim, Patient, Policy, ClaimHistory

client = TestClient(app)

class TestRunner:
    passed = 0
    failed = 0

    @classmethod
    def record(cls, name: str, status: str, detail: str = ""):
        if status == "PASSED":
            cls.passed += 1
            print(f"[PASS] {name} -> {detail}")
        else:
            cls.failed += 1
            print(f"[FAIL] {name} -> {detail}")


def base_payload():
    return {
        "patientName": "David Miller",
        "patientAge": 46,
        "hospital": "Apollo Hospitals International",
        "policyNumber": f"98{uuid.uuid4().int % 100000000:08d}",
        "insuranceProvider": "Pacific Healthcare TPA",
        "admissionDate": "2026-08-10",
        "dischargeDate": "2026-08-14",
        "diagnosis": "Acute Cholecystitis (ICD-10: K81.0)",
        "diagnosisCode": "K81.0",
        "diagnosisCodeSystem": "ICD-10",
        "clinicalNotes": "Documented ultrasound confirmed acute cholecystitis with gallstones.",
        "claimedAmount": 145000.0,
        "status": "Under Analysis",
        "stage": "01 Secure Document Intake",
    }


def run_form_validation_tests():
    print("=" * 70)
    print("CLAIMBRIDGE FORM VALIDATION & CLINICAL MAPPING SUITE")
    print("=" * 70)

    # 1. VALID SUBMISSION WITH CLINICAL DIAGNOSIS & NEON PERSISTENCE
    valid_data = base_payload()
    resp = client.post("/claims", json=valid_data)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    claim_id = resp.json()["id"]
    assert claim_id is not None
    TestRunner.record("Valid Submission", "PASSED", f"Created Claim UUID: {claim_id}")

    # Verify database persistence & metadata
    with SessionLocal() as db:
        claim_row = db.query(Claim).filter(Claim.id == uuid.UUID(claim_id)).first()
        assert claim_row is not None
        hist = db.query(ClaimHistory).filter(ClaimHistory.claim_id == claim_row.id, ClaimHistory.action == "Claim Created").first()
        assert hist is not None
        assert "K81.0" in hist.remarks
    TestRunner.record("Database Metadata Persistence", "PASSED", "Diagnosis code stored in ClaimHistory remarks")

    # Verify serialization via GET /claims/{id}
    get_res = client.get(f"/claims/{claim_id}")
    assert get_res.status_code == 200
    claim_json = get_res.json()
    assert claim_json["diagnosisCode"] == "K81.0"
    assert claim_json["diagnosisCodeSystem"] == "ICD-10"
    assert "ultrasound confirmed" in claim_json["clinicalNotes"]
    TestRunner.record("Clinical Data Serialization", "PASSED", f"ICD-10: {claim_json['diagnosisCode']}")

    # 2. PATIENT FULL NAME VALIDATION
    # 2a. Reject numbers in name
    p = base_payload()
    p["patientName"] = "David123"
    r = client.post("/claims", json=p)
    assert r.status_code == 422 and "numbers" in r.text.lower()
    TestRunner.record("Reject Name with Digits", "PASSED", "David123 -> 422 Unprocessable Entity")

    # 2b. Reject numeric only
    p = base_payload()
    p["patientName"] = "12345"
    r = client.post("/claims", json=p)
    assert r.status_code == 422
    TestRunner.record("Reject Numeric Name", "PASSED", "12345 -> 422")

    # 2c. Reject empty name
    p = base_payload()
    p["patientName"] = ""
    r = client.post("/claims", json=p)
    assert r.status_code == 422
    TestRunner.record("Reject Empty Name", "PASSED", "Empty -> 422")

    # 2d. Reject whitespace-only name
    p = base_payload()
    p["patientName"] = "   "
    r = client.post("/claims", json=p)
    assert r.status_code == 422
    TestRunner.record("Reject Whitespace Name", "PASSED", "Whitespace -> 422")

    # 2e. Accept international accents & hyphens
    p = base_payload()
    p["patientName"] = "Mary-Jane O'Neil"
    r = client.post("/claims", json=p)
    assert r.status_code == 200
    TestRunner.record("Accept International Name", "PASSED", "Mary-Jane O'Neil -> 200 OK")

    p = base_payload()
    p["patientName"] = "José García"
    r = client.post("/claims", json=p)
    assert r.status_code == 200
    TestRunner.record("Accept Accented Name", "PASSED", "José García -> 200 OK")

    # 3. POLICY NUMBER VALIDATION (8-13 DIGITS)
    # 3a. Reject 7 digits
    p = base_payload()
    p["policyNumber"] = "1234567"
    r = client.post("/claims", json=p)
    assert r.status_code == 422 and "8 and 13" in r.text
    TestRunner.record("Reject 7-digit Policy Number", "PASSED", "1234567 -> 422")

    # 3b. Reject 14 digits
    p = base_payload()
    p["policyNumber"] = "12345678901234"
    r = client.post("/claims", json=p)
    assert r.status_code == 422 and "8 and 13" in r.text
    TestRunner.record("Reject 14-digit Policy Number", "PASSED", "14 digits -> 422")

    # 3c. Reject alphanumeric policy number
    p = base_payload()
    p["policyNumber"] = "POL-12345678"
    r = client.post("/claims", json=p)
    assert r.status_code == 422
    TestRunner.record("Reject Alphanumeric Policy", "PASSED", "POL-12345678 -> 422")

    # 3d. Reject spaces or punctuation
    p = base_payload()
    p["policyNumber"] = "1234 5678"
    r = client.post("/claims", json=p)
    assert r.status_code == 422
    TestRunner.record("Reject Spaces in Policy", "PASSED", "1234 5678 -> 422")

    # 3e. Accept 8 digits
    p = base_payload()
    p["policyNumber"] = "12345678"
    r = client.post("/claims", json=p)
    assert r.status_code == 200
    TestRunner.record("Accept 8-digit Policy", "PASSED", "12345678 -> 200 OK")

    # 3f. Accept 13 digits
    p = base_payload()
    p["policyNumber"] = "1234567890123"
    r = client.post("/claims", json=p)
    assert r.status_code == 200
    TestRunner.record("Accept 13-digit Policy", "PASSED", "1234567890123 -> 200 OK")

    # 3g. Preserve leading zero
    p = base_payload()
    p["policyNumber"] = "01234567"
    r = client.post("/claims", json=p)
    assert r.status_code == 200
    assert r.json()["policyNumber"] == "01234567"
    TestRunner.record("Preserve Leading Zero Policy", "PASSED", "01234567 preserved as string")

    # 4. PATIENT AGE VALIDATION
    # 4a. Reject negative age
    p = base_payload()
    p["patientAge"] = -5
    r = client.post("/claims", json=p)
    assert r.status_code == 422
    TestRunner.record("Reject Negative Age", "PASSED", "-5 -> 422")

    # 4b. Reject age > 120
    p = base_payload()
    p["patientAge"] = 125
    r = client.post("/claims", json=p)
    assert r.status_code == 422
    TestRunner.record("Reject Age > 120", "PASSED", "125 -> 422")

    # 4c. Accept boundary ages (0 and 120)
    p = base_payload()
    p["patientAge"] = 0
    r = client.post("/claims", json=p)
    assert r.status_code == 200
    TestRunner.record("Accept Infant Age 0", "PASSED", "Age 0 -> 200 OK")

    p = base_payload()
    p["patientAge"] = 120
    r = client.post("/claims", json=p)
    assert r.status_code == 200
    TestRunner.record("Accept Maximum Age 120", "PASSED", "Age 120 -> 200 OK")

    # 5. HOSPITAL NAME VALIDATION
    p = base_payload()
    p["hospital"] = ""
    r = client.post("/claims", json=p)
    assert r.status_code == 422
    TestRunner.record("Reject Empty Hospital", "PASSED", "Empty -> 422")

    p = base_payload()
    p["hospital"] = "   "
    r = client.post("/claims", json=p)
    assert r.status_code == 422
    TestRunner.record("Reject Whitespace Hospital", "PASSED", "Whitespace -> 422")

    # 6. INSURANCE PROVIDER / TPA VALIDATION
    p = base_payload()
    p["insuranceProvider"] = ""
    r = client.post("/claims", json=p)
    assert r.status_code == 422
    TestRunner.record("Reject Empty Provider", "PASSED", "Empty -> 422")

    # 7. CLAIMED AMOUNT VALIDATION
    p = base_payload()
    p["claimedAmount"] = 0.0
    r = client.post("/claims", json=p)
    assert r.status_code == 422
    TestRunner.record("Reject Zero Amount", "PASSED", "0.0 -> 422")

    p = base_payload()
    p["claimedAmount"] = -100.0
    r = client.post("/claims", json=p)
    assert r.status_code == 422
    TestRunner.record("Reject Negative Amount", "PASSED", "-100.0 -> 422")

    # 8. ADMISSION AND DISCHARGE DATES
    # 8a. Admission after discharge
    p = base_payload()
    p["admissionDate"] = "2026-08-15"
    p["dischargeDate"] = "2026-08-10"
    r = client.post("/claims", json=p)
    assert r.status_code == 422 and "after" in r.text
    TestRunner.record("Reject Admission > Discharge", "PASSED", "2026-08-15 > 2026-08-10 -> 422")

    # 8b. Same-day admission and discharge
    p = base_payload()
    p["admissionDate"] = "2026-08-10"
    p["dischargeDate"] = "2026-08-10"
    r = client.post("/claims", json=p)
    assert r.status_code == 200
    TestRunner.record("Accept Same-day Hospitalization", "PASSED", "Daycare surgery -> 200 OK")

    # 8c. Missing admission date
    p = base_payload()
    p["admissionDate"] = None
    r = client.post("/claims", json=p)
    assert r.status_code == 422
    TestRunner.record("Reject Missing Admission Date", "PASSED", "Missing -> 422")

    # 9. DIAGNOSIS REQUIREMENT
    p = base_payload()
    p["diagnosis"] = ""
    r = client.post("/claims", json=p)
    assert r.status_code == 422
    TestRunner.record("Reject Missing Diagnosis", "PASSED", "Empty -> 422")

    p = base_payload()
    p["diagnosis"] = "Unlisted Rare Condition"
    p["diagnosisCode"] = "UNLISTED"
    p["diagnosisCodeSystem"] = "Unresolved"
    r = client.post("/claims", json=p)
    assert r.status_code == 200
    TestRunner.record("Accept Unlisted Diagnosis", "PASSED", "Unlisted pathway -> 200 OK")

    print("\n" + "=" * 70)
    print("BACKEND FORM VALIDATION SUITE SUMMARY")
    print("=" * 70)
    print(f"Total Tests Run : {TestRunner.passed + TestRunner.failed}")
    print(f"Passed          : {TestRunner.passed}")
    print(f"Failed          : {TestRunner.failed}")
    print("=" * 70)

    if TestRunner.failed > 0:
        raise SystemExit(1)
    else:
        print("ALL BACKEND VALIDATION TESTS PASSED CLEANLY!\n")


if __name__ == "__main__":
    run_form_validation_tests()
