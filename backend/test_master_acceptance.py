"""
ClaimBridge Master End-to-End Acceptance Test Suite
===================================================
Tests the entire end-to-end integration:
1. Claim Creation in Neon PostgreSQL
2. Searchable PDF Hospital Bill Upload & AI Pipeline Execution
3. Scanned Image-Only PDF Discharge Summary Upload & OCR Execution
4. Multi-Document Cross-Reconciliation
5. Idempotent Retry Safety
6. GET /claims/{id} Real Data Serialization
7. Corrupted / Invalid Document Rejection without state corruption
"""

import io
import json
import os
import shutil
import sys
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
import pymupdf as fitz

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.database import SessionLocal
from app.models import (
    Claim,
    Patient,
    Policy,
    ClaimDocument,
    DocumentExtraction,
    MedicalAnalysis,
    AIAnalysis,
    VerificationResult,
    ClaimHistory,
)

client = TestClient(app)

TMP_DIR = backend_dir / "test_tmp_acceptance"
TMP_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_tmp():
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR, ignore_errors=True)


class AcceptanceRunner:
    passed = 0
    failed = 0
    errors = []

    @classmethod
    def record(cls, step: str, status: str, detail: str = ""):
        if status == "PASSED":
            cls.passed += 1
            print(f"[PASSED] {step} -> {detail}")
        else:
            cls.failed += 1
            cls.errors.append((step, detail))
            print(f"[FAILED] {step} -> {detail}")


def run_master_acceptance():
    print("\n" + "=" * 70)
    print("CLAIMBRIDGE MASTER END-TO-END ACCEPTANCE SUITE")
    print("=" * 70)

    claim_id = None
    doc1_id = None
    doc2_id = None

    try:
        # -----------------------------------------------------------------
        # STEP 1: CREATE CLAIM VIA API & VERIFY DATABASE PERSISTENCE
        # -----------------------------------------------------------------
        claim_payload = {
            "patientName": "Edward Acceptance Patient",
            "patientAge": 47,
            "hospital": "Apollo Hospitals International",
            "policyNumber": f"98{uuid.uuid4().int % 100000000:08d}",
            "insuranceProvider": "Care Health Insurance",
            "claimedAmount": 125000.0,
            "admissionDate": "2026-09-01",
            "dischargeDate": "2026-09-05",
            "diagnosis": "Acute Cholecystitis",
            "status": "Under Analysis",
            "stage": "01 Secure Document Intake",
        }

        resp = client.post("/claims", json=claim_payload)
        assert resp.status_code == 200, f"Claim creation returned {resp.status_code}: {resp.text}"
        created_data = resp.json()
        claim_id = created_data["id"]
        assert claim_id, "Missing claim UUID in response"
        assert created_data["patientName"] == "Edward Acceptance Patient"

        # Verify database state in Neon
        with SessionLocal() as db:
            db_claim = db.query(Claim).filter(Claim.id == uuid.UUID(claim_id)).first()
            assert db_claim is not None, "Claim not persisted in database"
            assert db_claim.claim_status == "Under Analysis"

            db_patient = db.query(Patient).filter(Patient.id == db_claim.patient_id).first()
            assert db_patient is not None, "Patient not persisted"
            assert db_patient.full_name == "Edward Acceptance Patient"
            assert db_patient.date_of_birth is not None, "Patient DOB should be calculated from age"

            db_history = (
                db.query(ClaimHistory)
                .filter(ClaimHistory.claim_id == db_claim.id, ClaimHistory.action == "Claim Created")
                .first()
            )
            assert db_history is not None, "Creation history record missing"

        AcceptanceRunner.record(
            "Step 1: Claim Creation & Neon Persistence",
            "PASSED",
            f"Created Claim UUID: {claim_id}",
        )

        # -----------------------------------------------------------------
        # STEP 2: CREATE & UPLOAD SEARCHABLE PDF HOSPITAL BILL
        # -----------------------------------------------------------------
        bill_pdf_path = TMP_DIR / "searchable_hospital_bill.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        bill_text = (
            "APOLLO HOSPITALS INTERNATIONAL\n"
            "TAX INVOICE / HOSPITAL BILL\n"
            "INVOICE NO: INV-APP-2026-001\n"
            "PATIENT NAME: Edward Acceptance Patient\n"
            "ADMISSION DATE: 01.09.2026\n"
            "DISCHARGE DATE: 05.09.2026\n"
            "ROOM CHARGES: 35000.00\n"
            "PHARMACY CHARGES: 25000.00\n"
            "SURGERY CHARGES: 45000.00\n"
            "TOTAL CHARGES: 105000.00\n"
            "AMOUNT PAYABLE: 105000.00"
        )
        page.insert_text((50, 70), bill_text, fontsize=12)
        doc.save(str(bill_pdf_path))
        doc.close()

        with open(bill_pdf_path, "rb") as f:
            up_resp = client.post(
                "/documents/upload",
                data={"claim_id": claim_id, "category": "Auto-Detect"},
                files={"file": ("searchable_hospital_bill.pdf", f, "application/pdf")},
            )

        assert up_resp.status_code == 200, f"Upload returned {up_resp.status_code}: {up_resp.text}"
        doc1_data = up_resp.json()
        doc1_id = doc1_data["documentId"]
        assert doc1_id, "Missing documentId"

        AcceptanceRunner.record(
            "Step 2: Searchable PDF Hospital Bill Upload",
            "PASSED",
            f"Document UUID: {doc1_id}",
        )

        # -----------------------------------------------------------------
        # STEP 3: RUN AI PIPELINE ON DOCUMENT 1
        # -----------------------------------------------------------------
        proc1_resp = client.post(f"/documents/{doc1_id}/process")
        assert proc1_resp.status_code == 200, f"Processing failed: {proc1_resp.text}"
        proc1_data = proc1_resp.json()
        pipeline1 = proc1_data["pipeline"]

        # Validate pipeline stages
        assert pipeline1["ocr"]["confidence"] == 1.0, "Native PDF extraction should yield 1.0 confidence"
        assert pipeline1["classification"]["document_type"] == "hospital_bill"
        assert pipeline1["extracted_information"]["total_charges"] == 105000.0
        assert pipeline1["extracted_information"]["hospital_name"] == "APOLLO HOSPITALS INTERNATIONAL"
        assert pipeline1["claim_readiness"]["readiness_score"] >= 60.0

        # Validate database records
        with SessionLocal() as db:
            ext1 = db.query(DocumentExtraction).filter(DocumentExtraction.document_id == uuid.UUID(doc1_id)).first()
            assert ext1 is not None, "DocumentExtraction record not found"
            assert ext1.extraction_status == "Completed"

            ai1 = db.query(AIAnalysis).filter(AIAnalysis.document_id == uuid.UUID(doc1_id)).all()
            assert len(ai1) >= 5, f"Expected AI analysis records, got {len(ai1)}"

        AcceptanceRunner.record(
            "Step 3: Document 1 Pipeline & Persistence",
            "PASSED",
            f"Type: {pipeline1['classification']['document_type']}, Charges: 105000.0, Readiness: {pipeline1['claim_readiness']['readiness_score']}%",
        )

        # -----------------------------------------------------------------
        # STEP 4: CREATE & UPLOAD SCANNED IMAGE-ONLY PDF DISCHARGE SUMMARY
        # -----------------------------------------------------------------
        discharge_img_path = TMP_DIR / "discharge_summary_scan.png"
        img = Image.new("RGB", (900, 450), color="white")
        draw = ImageDraw.Draw(img)
        scan_text = (
            "APOLLO HOSPITALS INTERNATIONAL\n"
            "DISCHARGE SUMMARY\n"
            "PATIENT NAME: Edward Acceptance Patient\n"
            "ADMISSION DATE: 01.09.2026\n"
            "DISCHARGE DATE: 05.09.2026\n"
            "DIAGNOSIS: ACUTE CHOLECYSTITIS\n"
            "PROCEDURE: LAPAROSCOPIC CHOLECYSTECTOMY\n"
            "CONDITION: STABLE"
        )
        draw.text((40, 40), scan_text, fill="black")
        img.save(str(discharge_img_path))

        # Embed into PDF with NO selectable text stream
        discharge_pdf_path = TMP_DIR / "scanned_discharge_summary.pdf"
        doc = fitz.open()
        page = doc.new_page(width=900, height=450)
        page.insert_image(page.rect, filename=str(discharge_img_path))
        doc.save(str(discharge_pdf_path))
        doc.close()

        # Confirm 0 embedded text
        chk = fitz.open(str(discharge_pdf_path))
        assert chk[0].get_text().strip() == "", "Must be scanned PDF with no text stream"
        chk.close()

        with open(discharge_pdf_path, "rb") as f:
            up_resp2 = client.post(
                "/documents/upload",
                data={"claim_id": claim_id, "category": "Auto-Detect"},
                files={"file": ("scanned_discharge_summary.pdf", f, "application/pdf")},
            )

        assert up_resp2.status_code == 200, f"Upload 2 returned {up_resp2.status_code}: {up_resp2.text}"
        doc2_id = up_resp2.json()["documentId"]

        AcceptanceRunner.record(
            "Step 4: Scanned Image-Only PDF Upload",
            "PASSED",
            f"Document UUID: {doc2_id} (0 embedded digital text)",
        )

        # -----------------------------------------------------------------
        # STEP 5: RUN AI PIPELINE & OCR ON DOCUMENT 2 (SCANNED PDF)
        # -----------------------------------------------------------------
        proc2_resp = client.post(f"/documents/{doc2_id}/process")
        assert proc2_resp.status_code == 200, f"Processing Doc 2 failed: {proc2_resp.text}"
        proc2_data = proc2_resp.json()
        pipeline2 = proc2_data["pipeline"]

        # Validate OCR recognition
        assert "lines" in pipeline2["ocr"]
        assert pipeline2["classification"]["document_type"] == "discharge_summary"
        assert pipeline2["ocr"]["confidence"] > 0.0

        # Validate cross-document reconciliation
        with SessionLocal() as db:
            v_res = db.query(VerificationResult).filter(VerificationResult.claim_id == uuid.UUID(claim_id)).first()
            assert v_res is not None, "VerificationResult missing"
            # Since patient name and dates match, no cross-document mismatches should exist
            assert v_res.mismatches == [], f"Unexpected mismatches: {v_res.mismatches}"

        AcceptanceRunner.record(
            "Step 5: Scanned PDF OCR & Cross-Reconciliation",
            "PASSED",
            f"Classified: {pipeline2['classification']['document_type']}, Mismatches: 0 (Consistent)",
        )

        # -----------------------------------------------------------------
        # STEP 6: IDEMPOTENT RETRY PROCESSING
        # -----------------------------------------------------------------
        retry_resp = client.post(f"/documents/{doc1_id}/process")
        assert retry_resp.status_code == 200, f"Retry failed: {retry_resp.text}"

        with SessionLocal() as db:
            # Verify no duplicate DocumentExtraction rows
            ext_count = db.query(DocumentExtraction).filter(DocumentExtraction.document_id == uuid.UUID(doc1_id)).count()
            assert ext_count == 1, f"Expected 1 extraction record, found {ext_count}"

            # Verify no duplicate AIAnalysis rows per type
            ai_cls_count = (
                db.query(AIAnalysis)
                .filter(
                    AIAnalysis.document_id == uuid.UUID(doc1_id),
                    AIAnalysis.analysis_type == "Document Classification",
                )
                .count()
            )
            assert ai_cls_count == 1, f"Expected 1 classification analysis row, found {ai_cls_count}"

        AcceptanceRunner.record(
            "Step 6: Idempotent Retry Safety",
            "PASSED",
            "Re-processed document without duplicate database entries or 500 error",
        )

        # -----------------------------------------------------------------
        # STEP 7: GET /claims/{id} REAL DATA SERIALIZATION & ZERO FABRICATION
        # -----------------------------------------------------------------
        get_resp = client.get(f"/claims/{claim_id}")
        assert get_resp.status_code == 200, f"GET claim failed: {get_resp.text}"
        claim_detail = get_resp.json()

        assert claim_detail["id"] == claim_id
        assert claim_detail["patientName"] == "Edward Acceptance Patient"
        assert claim_detail["patientAge"] == 47
        assert "apollo hospitals" in claim_detail["hospital"].lower()
        assert len(claim_detail["documents"]) == 2
        assert claim_detail["readiness"] > 0
        assert claim_detail["ocrConfidence"] > 0
        assert len(claim_detail["findings"]) > 0

        # Assert zero fabricated placeholder strings
        raw_json = json.dumps(claim_detail)
        assert "Mrs. Tuhod" not in raw_json
        assert "184000" not in raw_json
        assert "Medical Claim Assessment Protocol" not in raw_json

        AcceptanceRunner.record(
            "Step 7: Real Data Serialization & Zero Fabrication",
            "PASSED",
            f"Hospital: {claim_detail['hospital']}, Age: {claim_detail['patientAge']}, Findings: {len(claim_detail['findings'])}",
        )

        # -----------------------------------------------------------------
        # STEP 8: REJECT MALFORMED / INVALID FILES WITHOUT CORRUPTING STATE
        # -----------------------------------------------------------------
        # A. Fake PDF header
        bad_pdf = client.post(
            "/documents/upload",
            data={"claim_id": claim_id, "category": "Hospital Bill"},
            files={"file": ("fake_header.pdf", b"NOT_A_PDF_STREAM", "application/pdf")},
        )
        assert bad_pdf.status_code == 400
        assert "Invalid PDF" in bad_pdf.json()["detail"]

        # B. 0-byte file
        empty_upload = client.post(
            "/documents/upload",
            data={"claim_id": claim_id, "category": "Hospital Bill"},
            files={"file": ("zero_bytes.pdf", b"", "application/pdf")},
        )
        assert empty_upload.status_code == 400
        assert "empty" in empty_upload.json()["detail"].lower()

        # Verify claim remains intact
        get_after = client.get(f"/claims/{claim_id}")
        assert get_after.status_code == 200
        assert len(get_after.json()["documents"]) == 2

        AcceptanceRunner.record(
            "Step 8: Malformed File Rejection & State Safety",
            "PASSED",
            "400 Bad Request enforced for invalid inputs without corrupting claim state",
        )

    except Exception as exc:
        import traceback
        traceback.print_exc()
        AcceptanceRunner.record("Acceptance Suite Exception", "FAILED", str(exc))

    finally:
        cleanup_tmp()

    print("\n" + "=" * 70)
    print("MASTER ACCEPTANCE SUITE EXECUTION SUMMARY")
    print("=" * 70)
    print(f"Total Steps : {AcceptanceRunner.passed + AcceptanceRunner.failed}")
    print(f"Passed      : {AcceptanceRunner.passed}")
    print(f"Failed      : {AcceptanceRunner.failed}")
    print("=" * 70)

    if AcceptanceRunner.failed == 0:
        print("ALL ACCEPTANCE CRITERIA PASSED SUCCESSFULLY!")
        return 0
    else:
        print(f"FAILURES DETECTED: {AcceptanceRunner.errors}")
        return 1


if __name__ == "__main__":
    code = run_master_acceptance()
    sys.exit(code)
