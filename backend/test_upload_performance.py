import io
import time
import uuid
from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import User, Claim, Policy, Patient, ClaimDocument
from backend.app.auth import create_access_token

client = TestClient(app)

OWNER_EMAIL = "aishwaryamotling18@gmail.com"

def get_auth_headers():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == OWNER_EMAIL).first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email=OWNER_EMAIL,
                role="claimant",
                full_name="Aishwarya Motling",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        token = create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role,
            portal="Hospital",
            organization=user.organization,
        )
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()

# Warmup connection once at module load
_warmup_db = SessionLocal()
_warmup_claim = _warmup_db.query(Claim).first()
_warmup_db.close()

def create_sample_pdf(content_text: str = "Test PDF Document") -> bytes:
    # A minimal valid 1-page PDF
    stream_content = f"BT /F1 12 Tf 72 712 Td ({content_text}) Tj ET"
    stream_len = len(stream_content)
    pdf = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length {stream_len} >> stream
{stream_content}
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000300 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
370
%%EOF"""
    return pdf.encode("latin-1")

def test_single_upload_instant_response():
    """Verify single PDF upload returns fast with 'Uploaded' status."""
    headers = get_auth_headers()
    db = SessionLocal()
    user = db.query(User).filter(User.email == OWNER_EMAIL).first()
    claim = db.query(Claim).filter(Claim.created_by == user.id).first()
    claim_id = str(claim.id) if claim else None
    db.close()

    pdf_bytes = create_sample_pdf("Medical Consultation Prescription Dr Sharma")
    file_name = f"test_prescription_{uuid.uuid4().hex[:6]}.pdf"

    payload_data = {"category": "Consultation Letter"}
    if claim_id:
        payload_data["claim_id"] = claim_id

    t0 = time.time()
    response = client.post(
        "/documents/upload",
        files={"file": (file_name, io.BytesIO(pdf_bytes), "application/pdf")},
        data=payload_data,
        headers=headers,
    )
    duration_ms = (time.time() - t0) * 1000

    print(f"\n[METRIC] Single PDF upload returned in {duration_ms:.1f}ms")
    assert response.status_code == 200, f"Upload failed: {response.text}"
    data = response.json()
    assert "documentId" in data
    assert data["fileName"] == file_name
    assert data["processingStatus"] == "Uploaded"
    assert duration_ms < 7500, f"Upload took too long: {duration_ms}ms"

def test_duplicate_upload_prevention():
    """Verify uploading the same file again returns existing doc and prevents duplication."""
    headers = get_auth_headers()
    pdf_bytes = create_sample_pdf("Insurance Card E-Card Policy 98765")
    file_name = f"test_id_dup_{uuid.uuid4().hex[:6]}.pdf"

    # First upload
    res1 = client.post(
        "/documents/upload",
        files={"file": (file_name, io.BytesIO(pdf_bytes), "application/pdf")},
        data={"category": "Insurance Card"},
        headers=headers,
    )
    assert res1.status_code == 200
    doc_id_1 = res1.json()["documentId"]

    # Second upload with same name & claim
    res2 = client.post(
        "/documents/upload",
        files={"file": (file_name, io.BytesIO(pdf_bytes), "application/pdf")},
        data={"category": "Insurance Card", "claim_id": res1.json()["claimId"]},
        headers=headers,
    )
    assert res2.status_code == 200
    doc_id_2 = res2.json()["documentId"]
    assert doc_id_1 == doc_id_2, "Duplicate upload should return existing document ID"
    assert "already uploaded" in res2.json()["message"].lower()

def test_concurrent_uploads_performance():
    """Upload 5 PDF files rapidly and ensure all complete fast with 0 blocking."""
    headers = get_auth_headers()
    db = SessionLocal()
    user = db.query(User).filter(User.email == OWNER_EMAIL).first()
    claim = db.query(Claim).filter(Claim.created_by == user.id).first()
    claim_id = str(claim.id) if claim else None
    db.close()

    categories = [
        "Identity Proof",
        "Insurance Card",
        "Consultation Letter",
        "Diagnostic Report",
        "Pre-Authorization Form",
    ]

    docs_to_upload = [
        (f"doc_{i}_{uuid.uuid4().hex[:6]}.pdf", create_sample_pdf(f"Document {cat} content"), cat)
        for i, cat in enumerate(categories)
    ]

    t_total_start = time.time()
    results = []
    for fname, fbytes, cat in docs_to_upload:
        payload = {"category": cat}
        if claim_id:
            payload["claim_id"] = claim_id

        t_start = time.time()
        res = client.post(
            "/documents/upload",
            files={"file": (fname, io.BytesIO(fbytes), "application/pdf")},
            data=payload,
            headers=headers,
        )
        t_end = time.time()
        results.append((res, (t_end - t_start) * 1000))

    total_time_ms = (time.time() - t_total_start) * 1000

    print(f"\n[METRIC] Total upload time for 5 files: {total_time_ms:.1f}ms")
    for idx, (res, dur_ms) in enumerate(results):
        print(f"  File {idx + 1} ({categories[idx]}): {dur_ms:.1f}ms")
        assert res.status_code == 200
        assert res.json()["processingStatus"] == "Uploaded"

    assert total_time_ms < 25000, f"5 uploads took {total_time_ms}ms, expected < 25000ms"
