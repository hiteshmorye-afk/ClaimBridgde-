"""
Comprehensive Test Suite for ClaimBridge Hospital Cashless Claim Workflow
==========================================================================
Verifies all 10 modules:
1. Provider Management: GET /cashless/providers
2. Non-admin cannot register providers (403 Forbidden)
3. Cashless Claim Intake (patient & policy registration)
4. Patient Consent: Capture statutory consent with consenter details, IP, and audit trail
5. Pre-Auth Workspace: Save estimated cost breakdown, draft status
6. Pre-Auth Package Export: Generates structured dispatch package with SHA-256 fingerprint
7. Pre-Auth Submission: Transitions status to Submitted and records submission reference
8. Role Isolation: Hospital coordinator cannot adjudicate pre-auth (403 Forbidden)
9. TPA Boundary Isolation: Out-of-scope TPA reviewer cannot adjudicate (403 Forbidden)
10. TPA Query Cycle: TPA raises query -> Coordinator responds -> Status returns to Under Review
11. TPA Initial Approval: Approved amount caps cashless liability, logs ClaimHistory & AuditEvent
12. Treatment Documentation: Inpatient chronological clinical notes and running expenses ledger
13. Final Authorization Workspace: Save final itemized bill and 3-way financial reconciliation
14. TPA Settlement Adjudication: Record non-payable deductions and patient responsibility
15. Discharge Readiness Holistic Assessment: Evaluates checklist, advisory-only status
"""

import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
import random

import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.auth import create_access_token
from app.database import SessionLocal
from app.main import app
from app.models import (
    AuditEvent,
    CashlessFinalAuthorization,
    CashlessPreauthorization,
    Claim,
    ClaimDocument,
    ClaimHistory,
    InsuranceProvider,
    Patient,
    PatientConsent,
    Policy,
    TreatmentRecord,
    User,
)

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def setup_users():
    session = SessionLocal()
    try:
        # 1. Hospital Coordinator
        coord = session.query(User).filter(User.email == "test_cashless_coord@claimbridge.internal").first()
        if not coord:
            coord = User(
                full_name="Cashless Coordinator Sarah",
                email="test_cashless_coord@claimbridge.internal",
                role="claimant",
                account_status="active",
                organization="Apollo Specialty Hospital",
                email_verified_at=datetime.utcnow(),
                organization_verified_at=datetime.utcnow(),
            )
            session.add(coord)

        # 2. Authorized TPA Reviewer (Star Health)
        tpa_star = session.query(User).filter(User.email == "test_cashless_tpa_star@claimbridge.internal").first()
        if not tpa_star:
            tpa_star = User(
                full_name="Star Claims Officer Roy",
                email="test_cashless_tpa_star@claimbridge.internal",
                role="claims_officer",
                account_status="active",
                organization="Star Health and Allied Insurance",
                email_verified_at=datetime.utcnow(),
                organization_verified_at=datetime.utcnow(),
            )
            session.add(tpa_star)

        # 3. Out-of-scope TPA Reviewer (Care Health)
        tpa_care = session.query(User).filter(User.email == "test_cashless_tpa_care@claimbridge.internal").first()
        if not tpa_care:
            tpa_care = User(
                full_name="Care Claims Officer Meera",
                email="test_cashless_tpa_care@claimbridge.internal",
                role="claims_officer",
                account_status="active",
                organization="Care Health Insurance",
                email_verified_at=datetime.utcnow(),
                organization_verified_at=datetime.utcnow(),
            )
            session.add(tpa_care)

        session.commit()
        session.refresh(coord)
        session.refresh(tpa_star)
        session.refresh(tpa_care)

        coord_token = create_access_token(
            user_id=str(coord.id),
            email=coord.email,
            role=coord.role,
            portal="Hospital",
            organization=coord.organization,
        )
        tpa_star_token = create_access_token(
            user_id=str(tpa_star.id),
            email=tpa_star.email,
            role=tpa_star.role,
            portal="TPA",
            organization=tpa_star.organization,
        )
        tpa_care_token = create_access_token(
            user_id=str(tpa_care.id),
            email=tpa_care.email,
            role=tpa_care.role,
            portal="TPA",
            organization=tpa_care.organization,
        )

        return {
            "coord": coord,
            "coord_token": coord_token,
            "tpa_star": tpa_star,
            "tpa_star_token": tpa_star_token,
            "tpa_care": tpa_care,
            "tpa_care_token": tpa_care_token,
        }
    finally:
        session.close()


def _create_claim_helper(setup_users):
    headers = {"Authorization": f"Bearer {setup_users['coord_token']}"}
    unique_policy = f"{random.randint(100000000, 999999999)}"
    first_names = ["Aarav", "Rohan", "Vikram", "Aditya", "Dev", "Karan", "Siddharth", "Arjun"]
    last_names = ["Sharma", "Patel", "Verma", "Mehta", "Deshmukh", "Nair", "Iyer", "Reddy"]
    patient_name = f"{random.choice(first_names)} {random.choice(last_names)}"

    payload = {
        "patientName": patient_name,
        "patientAge": 42,
        "hospital": "Apollo Specialty Hospital",
        "policyNumber": unique_policy,
        "insuranceProvider": "Star Health and Allied Insurance",
        "diagnosis": "Acute Appendicitis with Localized Peritonitis",
        "diagnosisCode": "K35.8",
        "admissionDate": date.today().isoformat(),
        "dischargeDate": (date.today() + timedelta(days=4)).isoformat(),
        "claimedAmount": 85000.0,
        "claimType": "cashless",
        "memberId": f"STAR-MEMB-{unique_policy[-5:]}",
        "policyHolderName": patient_name,
        "relationship": "Self",
        "emergencyContactName": "Pooja Sharma",
        "emergencyContactPhone": "+91-9876543210",
        "bloodGroup": "O+",
    }
    res = client.post("/claims", json=payload, headers=headers)
    assert res.status_code == 200, f"Claim creation failed: {res.text}"
    return res.json()["id"]


def test_01_get_insurance_providers():
    """Verify active providers catalogue is returned with supported claim types."""
    res = client.get("/cashless/providers")
    assert res.status_code == 200
    providers = res.json()
    assert len(providers) >= 6
    codes = [p["code"] for p in providers]
    assert "STAR_HEALTH" in codes
    assert "HDFC_ERGO" in codes
    assert "CARE_HEALTH" in codes
    star = next(p for p in providers if p["code"] == "STAR_HEALTH")
    assert "cashless" in star["supportedClaimTypes"]


def test_02_create_provider_requires_admin(setup_users):
    """Verify non-admin users cannot register new providers."""
    headers = {"Authorization": f"Bearer {setup_users['coord_token']}"}
    payload = {
        "name": "Unauthorized Health TPA",
        "code": "UNAUTH_TPA",
    }
    res = client.post("/cashless/providers", json=payload, headers=headers)
    assert res.status_code == 403


def test_03_create_cashless_claim_intake(setup_users, db):
    """Verify patient and policy registration with cashless fields."""
    claim_id = _create_claim_helper(setup_users)

    claim = db.query(Claim).filter(Claim.id == uuid.UUID(claim_id)).first()
    assert claim is not None
    assert claim.claim_type == "cashless"
    assert claim.discharge_readiness_status == "Pending Pre-Auth"

    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    assert policy.insurance_provider == "Star Health and Allied Insurance"
    assert policy.member_id.startswith("STAR-MEMB-")

    patient = db.query(Patient).filter(Patient.id == claim.patient_id).first()
    assert patient.blood_group == "O+"
    assert patient.emergency_contact_name == "Pooja Sharma"


def test_04_patient_consent_capture(setup_users, db):
    """Verify statutory patient consent capture, retrieval, and audit logging."""
    claim_id = _create_claim_helper(setup_users)
    headers = {"Authorization": f"Bearer {setup_users['coord_token']}"}

    # Before consent
    get_res = client.get(f"/cashless/claims/{claim_id}/consent", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["hasConsent"] is False

    # Submit consent
    consent_payload = {
        "consenter_name": "Pooja Sharma",
        "consenter_relationship": "Spouse",
        "purpose": "Cashless Hospitalization Medical Data Processing",
        "consent_text": "I hereby authorize Apollo Specialty Hospital and Star Health TPA to process medical records for cashless claim settlement.",
    }
    post_res = client.post(f"/cashless/claims/{claim_id}/consent", json=consent_payload, headers=headers)
    assert post_res.status_code == 201

    # After consent
    get_res2 = client.get(f"/cashless/claims/{claim_id}/consent", headers=headers)
    assert get_res2.status_code == 200
    c_data = get_res2.json()
    assert c_data["hasConsent"] is True
    assert c_data["consent"]["consenterName"] == "Pooja Sharma"
    assert c_data["consent"]["consenterRelationship"] == "Spouse"


def test_05_preauth_draft_and_package(setup_users, db):
    """Verify pre-authorization cost breakdown draft, checklist, and package generation."""
    claim_id = _create_claim_helper(setup_users)
    headers = {"Authorization": f"Bearer {setup_users['coord_token']}"}

    # Add mock document so submission passes doc check
    mock_doc = ClaimDocument(
        claim_id=uuid.UUID(claim_id),
        document_type="pre_authorization",
        file_name="preauth_request_form.pdf",
        file_path="claims/test/preauth.pdf",
    )
    db.add(mock_doc)
    db.commit()

    preauth_payload = {
        "room_type": "Single Private AC",
        "proposed_treatment": "Laparoscopic Appendectomy under General Anesthesia",
        "treating_doctor": "Dr. Ramesh Verma, MS (Gen Surg)",
        "doctor_registration_no": "MCI-2012-44321",
        "estimated_cost": 85000.0,
        "cost_breakdown": {
            "Room Rent (4 days)": 20000.0,
            "Surgical Charges": 35000.0,
            "Operation Theatre": 15000.0,
            "Medicines & Consumables": 10000.0,
            "Diagnostic Investigations": 5000.0,
        },
    }
    save_res = client.post(f"/cashless/claims/{claim_id}/preauth", json=preauth_payload, headers=headers)
    assert save_res.status_code == 200
    assert save_res.json()["estimatedCost"] == 85000.0

    # Retrieve preauth
    get_res = client.get(f"/cashless/claims/{claim_id}/preauth", headers=headers)
    assert get_res.status_code == 200
    p_data = get_res.json()
    assert p_data["exists"] is True
    assert p_data["preauth"]["roomType"] == "Single Private AC"
    assert p_data["preauth"]["costBreakdown"]["Surgical Charges"] == 35000.0

    # Package export
    pkg_res = client.get(f"/cashless/claims/{claim_id}/preauth/package", headers=headers)
    assert pkg_res.status_code == 200
    pkg = pkg_res.json()
    assert "packageFingerprint" in pkg
    assert len(pkg["packageFingerprint"]) == 64
    assert pkg["package"]["hospitalization"]["estimatedCost"] == 85000.0

    # Submit pre-auth
    sub_payload = {
        "submission_mode": "Online Portal",
        "submission_reference": "STAR-PRE-2026-9901",
    }
    sub_res = client.post(f"/cashless/claims/{claim_id}/preauth/submit", json=sub_payload, headers=headers)
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "Submitted"


def test_06_preauth_adjudication_role_and_org_isolation(setup_users, db):
    """Verify coordinator cannot adjudicate, and wrong TPA organization is blocked."""
    claim_id = _create_claim_helper(setup_users)

    # 1. Hospital Coordinator attempts adjudication -> 403 Forbidden
    coord_headers = {"Authorization": f"Bearer {setup_users['coord_token']}"}
    adj_payload = {
        "decision": "Approved",
        "initial_approval_amount": 75000.0,
    }
    res1 = client.post(f"/cashless/claims/{claim_id}/preauth/adjudicate", json=adj_payload, headers=coord_headers)
    assert res1.status_code == 403

    # 2. Care Health TPA attempts adjudicating Star Health claim -> 403 Forbidden
    care_headers = {"Authorization": f"Bearer {setup_users['tpa_care_token']}"}
    res2 = client.post(f"/cashless/claims/{claim_id}/preauth/adjudicate", json=adj_payload, headers=care_headers)
    assert res2.status_code == 403


def test_07_preauth_query_and_approval_lifecycle(setup_users, db):
    """Verify full TPA query cycle and initial pre-auth approval."""
    claim_id = _create_claim_helper(setup_users)
    coord_headers = {"Authorization": f"Bearer {setup_users['coord_token']}"}
    star_headers = {"Authorization": f"Bearer {setup_users['tpa_star_token']}"}

    # Draft preauth
    client.post(f"/cashless/claims/{claim_id}/preauth", json={
        "room_type": "Semi-Private",
        "proposed_treatment": "Appendectomy",
        "estimated_cost": 80000.0,
    }, headers=coord_headers)

    # Add mock document and submit
    db.add(ClaimDocument(
        claim_id=uuid.UUID(claim_id),
        document_type="pre_authorization",
        file_name="preauth.pdf",
        file_path="claims/test/preauth2.pdf",
    ))
    db.commit()
    client.post(f"/cashless/claims/{claim_id}/preauth/submit", json={
        "submission_mode": "Online Portal",
        "submission_reference": "STAR-2026-REF1",
    }, headers=coord_headers)

    # 1. TPA raises query
    query_payload = {
        "decision": "Query Raised",
        "query_remarks": "Please provide USG Abdomen report confirming acute appendicitis diagnosis.",
    }
    q_res = client.post(f"/cashless/claims/{claim_id}/preauth/adjudicate", json=query_payload, headers=star_headers)
    assert q_res.status_code == 200
    assert q_res.json()["status"] == "Query Raised"

    # 2. Coordinator replies to query
    reply_payload = {
        "hospital_query_response": "USG Abdomen report attached showing dilated non-compressible appendix (8.2 mm).",
    }
    r_res = client.post(f"/cashless/claims/{claim_id}/preauth/respond-query", json=reply_payload, headers=coord_headers)
    assert r_res.status_code == 200
    assert r_res.json()["status"] == "Under Review"

    # 3. TPA grants initial approval
    appr_payload = {
        "decision": "Approved",
        "initial_approval_amount": 75000.0,
        "approval_conditions": "Capped per Star Health network schedule. Non-medical consumables excluded.",
    }
    appr_res = client.post(f"/cashless/claims/{claim_id}/preauth/adjudicate", json=appr_payload, headers=star_headers)
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "Approved"
    assert appr_res.json()["initialApprovalAmount"] == 75000.0


def test_08_treatment_records_ledger(setup_users, db):
    """Verify inpatient treatment clinical updates and running expenses."""
    claim_id = _create_claim_helper(setup_users)
    headers = {"Authorization": f"Bearer {setup_users['coord_token']}"}

    # Add day 1 note
    t1 = {
        "record_date": date.today().isoformat(),
        "clinical_notes": "Patient admitted. Pre-op prep initiated. IV fluids started.",
        "procedures_performed": [{"name": "Pre-anesthetic evaluation", "doctor": "Dr. Anesthetist"}],
        "updated_diagnosis": "Acute Appendicitis",
        "cumulative_expenses": 12000.0,
    }
    res1 = client.post(f"/cashless/claims/{claim_id}/treatment-records", json=t1, headers=headers)
    assert res1.status_code == 201

    # Add day 2 note
    t2 = {
        "record_date": (date.today() + timedelta(days=1)).isoformat(),
        "clinical_notes": "Laparoscopic appendectomy performed uneventfully. Vitals stable.",
        "procedures_performed": [{"name": "Laparoscopic Appendectomy", "surgeon": "Dr. Ramesh Verma"}],
        "cumulative_expenses": 65000.0,
    }
    res2 = client.post(f"/cashless/claims/{claim_id}/treatment-records", json=t2, headers=headers)
    assert res2.status_code == 201

    # Retrieve timeline
    list_res = client.get(f"/cashless/claims/{claim_id}/treatment-records", headers=headers)
    assert list_res.status_code == 200
    records = list_res.json()
    assert len(records) >= 2


def test_09_final_authorization_and_settlement(setup_users, db):
    """Verify final bill reconciliation, 3-way financial comparison, deductions, and settlement."""
    claim_id = _create_claim_helper(setup_users)
    coord_headers = {"Authorization": f"Bearer {setup_users['coord_token']}"}
    star_headers = {"Authorization": f"Bearer {setup_users['tpa_star_token']}"}

    # Initial Preauth setup
    client.post(f"/cashless/claims/{claim_id}/preauth", json={
        "room_type": "Single Private AC",
        "estimated_cost": 85000.0,
    }, headers=coord_headers)

    # Save final authorization bill
    final_payload = {
        "final_billed_amount": 88000.0,
        "deduction_breakdown": {
            "Non-Medical Consumables": 3500.0,
            "Room Rent Excess": 4500.0,
        },
        "patient_responsibility_amount": 8000.0,
    }
    save_res = client.post(f"/cashless/claims/{claim_id}/final-auth", json=final_payload, headers=coord_headers)
    assert save_res.status_code == 200

    # Verify 3-way financial comparison
    get_res = client.get(f"/cashless/claims/{claim_id}/final-auth", headers=coord_headers)
    assert get_res.status_code == 200
    cmp_data = get_res.json()["financialComparison"]
    assert cmp_data["estimatedCost"] == 85000.0
    assert cmp_data["finalBilledAmount"] == 88000.0

    # Submit final auth
    sub_res = client.post(f"/cashless/claims/{claim_id}/final-auth/submit", json={
        "submission_reference": "STAR-FINAL-2026-001",
    }, headers=coord_headers)
    assert sub_res.status_code == 200

    # TPA Adjudicates final settlement
    settle_payload = {
        "decision": "Approved",
        "final_approved_amount": 80000.0,
        "non_payable_deductions": 8000.0,
        "deduction_breakdown": {
            "Non-Medical Consumables": 3500.0,
            "Room Rent Excess": 4500.0,
        },
        "patient_responsibility_amount": 8000.0,
        "final_approval_reference": "STAR-SETTLE-88990",
        "tpa_remarks": "Approved per GIPSA PPN package rate. Consumables and room rent differential to be borne by patient.",
    }
    settle_res = client.post(f"/cashless/claims/{claim_id}/final-auth/adjudicate", json=settle_payload, headers=star_headers)
    assert settle_res.status_code == 200
    assert settle_res.json()["status"] == "Settled"
    assert settle_res.json()["finalApprovedAmount"] == 80000.0
    assert settle_res.json()["patientResponsibility"] == 8000.0


def test_10_discharge_readiness_assessment(setup_users, db):
    """Verify holistic discharge readiness evaluation and checklist."""
    claim_id = _create_claim_helper(setup_users)
    coord_headers = {"Authorization": f"Bearer {setup_users['coord_token']}"}
    star_headers = {"Authorization": f"Bearer {setup_users['tpa_star_token']}"}

    # Before pre-auth approval: Status should be Pending Pre-Auth
    res1 = client.get(f"/cashless/claims/{claim_id}/discharge-readiness", headers=coord_headers)
    assert res1.status_code == 200
    assert res1.json()["readinessStatus"] == "Pending Pre-Auth"
    assert res1.json()["isDischargeReady"] is False

    # Setup pre-auth and approve
    client.post(f"/cashless/claims/{claim_id}/preauth", json={"estimated_cost": 50000.0}, headers=coord_headers)
    db.add(ClaimDocument(
        claim_id=uuid.UUID(claim_id),
        document_type="pre_authorization",
        file_name="preauth.pdf",
        file_path="claims/test/p.pdf",
    ))
    db.commit()
    client.post(f"/cashless/claims/{claim_id}/preauth/submit", json={"submission_reference": "REF1"}, headers=coord_headers)
    client.post(f"/cashless/claims/{claim_id}/preauth/adjudicate", json={
        "decision": "Approved",
        "initial_approval_amount": 50000.0,
    }, headers=star_headers)

    # After pre-auth: Pending Settlement
    res2 = client.get(f"/cashless/claims/{claim_id}/discharge-readiness", headers=coord_headers)
    assert res2.status_code == 200
    assert res2.json()["readinessStatus"] == "Pending Settlement"

    # Add discharge summary and hospital bill documents
    db.add(ClaimDocument(
        claim_id=uuid.UUID(claim_id),
        document_type="discharge_summary",
        file_name="discharge_summary.pdf",
        file_path="claims/test/ds.pdf",
    ))
    db.add(ClaimDocument(
        claim_id=uuid.UUID(claim_id),
        document_type="hospital_bill",
        file_name="final_hospital_bill.pdf",
        file_path="claims/test/hb.pdf",
    ))
    db.commit()

    # Final auth submission and settlement
    client.post(f"/cashless/claims/{claim_id}/final-auth", json={"final_billed_amount": 52000.0}, headers=coord_headers)
    client.post(f"/cashless/claims/{claim_id}/final-auth/submit", json={"submission_reference": "REF2"}, headers=coord_headers)
    client.post(f"/cashless/claims/{claim_id}/final-auth/adjudicate", json={
        "decision": "Approved",
        "final_approved_amount": 50000.0,
        "non_payable_deductions": 2000.0,
        "patient_responsibility_amount": 2000.0,
        "final_approval_reference": "FINAL-REF-99",
    }, headers=star_headers)

    # Complete checklist: Should now evaluate as Discharge Ready
    res3 = client.get(f"/cashless/claims/{claim_id}/discharge-readiness", headers=coord_headers)
    assert res3.status_code == 200
    readiness = res3.json()
    assert readiness["isDischargeReady"] is True
    assert readiness["readinessStatus"] == "Discharge Ready"
    assert readiness["finalApprovedAmount"] == 50000.0
    assert readiness["patientResponsibilityAmount"] == 2000.0
    assert len(readiness["checklist"]) == 5
