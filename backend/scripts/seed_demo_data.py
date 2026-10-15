"""
ClaimBridge High-Performance Demonstration Data Seeder (Phase 6)
================================================================
Populates Neon PostgreSQL with relationally consistent, idempotent
demonstration data for:
- 5 Multi-Specialty Hospitals
- 3 Licensed TPAs / Health Insurers
- 9 Scoped Users (Hospital Coordinators, TPA Reviewers, Admin)
- 80 Relationally Consistent Claims across all 4 statuses
  (Approved, Needs Review, Under Analysis, Rejected)
- 320 Linked Claim Documents across the 15 standard document categories
- 320 Document Extractions with realistic OCR text and JSON payloads
- 80 Medical Analysis records with ICD-10 clinical diagnoses and procedures
- 80 Verification Result records with readiness calculations
- 600+ Claim History audit trail records tracking the 13 pipeline stages

Features high-performance bulk operations:
- Pre-fetches existing keys in O(1) set lookups (no per-row round trips)
- Generates client-side UUIDs to eliminate network flushes
- Uses unbuffered output with flush=True
- Safe idempotency: skips already seeded records
- Supports --clean or --purge flag
"""

import sys
import os
import uuid
import json
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from pwdlib import PasswordHash

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.database import SessionLocal
from backend.app.models import (
    User,
    Patient,
    Policy,
    Claim,
    ClaimDocument,
    DocumentExtraction,
    MedicalAnalysis,
    VerificationResult,
    ClaimHistory,
)

pwd_context = PasswordHash.recommended()
DEFAULT_DEMO_PASSWORD = "DemoPassword123!"

# Master Catalogues
HOSPITALS = [
    {
        "name": "Chong Hua Hospital",
        "coord_name": "Elena Ramos",
        "coord_email": "coordinator.chonghua@claimbridge.internal",
    },
    {
        "name": "Apollo Hospitals",
        "coord_name": "Dr. Rajesh Sharma",
        "coord_email": "coordinator.apollo@claimbridge.internal",
    },
    {
        "name": "Fortis Escorts Hospital",
        "coord_name": "Priya Nair",
        "coord_email": "coordinator.fortis@claimbridge.internal",
    },
    {
        "name": "Max Super Speciality Hospital",
        "coord_name": "Amitabh Sen",
        "coord_email": "coordinator.max@claimbridge.internal",
    },
    {
        "name": "Manipal Hospital",
        "coord_name": "Kavita Reddy",
        "coord_email": "coordinator.manipal@claimbridge.internal",
    },
]

TPAS = [
    {
        "name": "Pacific Healthcare TPA",
        "reviewer_name": "Marcus Vance",
        "reviewer_email": "reviewer.pacific@claimbridge.internal",
    },
    {
        "name": "Star Health Insurance",
        "reviewer_name": "Sunita Deshmukh",
        "reviewer_email": "reviewer.star@claimbridge.internal",
    },
    {
        "name": "HDFC ERGO TPA",
        "reviewer_name": "Vikram Malhotra",
        "reviewer_email": "reviewer.hdfc@claimbridge.internal",
    },
]

POLICY_TYPES = [
    ("Comprehensive Health Shield", Decimal("1000000.00")),
    ("Family Floater Elite", Decimal("1500000.00")),
    ("Critical Illness Protection Guard", Decimal("2500000.00")),
    ("Senior Citizen Platinum Care", Decimal("750000.00")),
    ("Corporate Group Health Plan", Decimal("500000.00")),
]

CLINICAL_CASES = [
    {
        "diagnosis": "Acute Appendicitis with Localized Peritonitis",
        "icd10": "K35.80",
        "procedure": "Laparoscopic Appendectomy",
        "avg_stay_days": 3,
        "base_cost": 85000.0,
        "medical_risk": 15.0,
    },
    {
        "diagnosis": "Coronary Artery Disease - Single Vessel",
        "icd10": "I25.10",
        "procedure": "Percutaneous Transluminal Coronary Angioplasty with DES",
        "avg_stay_days": 4,
        "base_cost": 235000.0,
        "medical_risk": 25.0,
    },
    {
        "diagnosis": "Bilateral Osteoarthritis of Knee Grade 3",
        "icd10": "M17.11",
        "procedure": "Unilateral Total Knee Replacement",
        "avg_stay_days": 5,
        "base_cost": 290000.0,
        "medical_risk": 20.0,
    },
    {
        "diagnosis": "Dengue Fever with Severe Thrombocytopenia",
        "icd10": "A90",
        "procedure": "Medical Inpatient Management & Platelet Transfusion",
        "avg_stay_days": 4,
        "base_cost": 62000.0,
        "medical_risk": 30.0,
    },
    {
        "diagnosis": "Acute Cholecystitis with Cholelithiasis",
        "icd10": "K80.00",
        "procedure": "Laparoscopic Cholecystectomy",
        "avg_stay_days": 3,
        "base_cost": 115000.0,
        "medical_risk": 18.0,
    },
    {
        "diagnosis": "Type 2 Diabetes Mellitus with Diabetic Foot Ulcer",
        "icd10": "E11.621",
        "procedure": "Surgical Debridement and Antibiotic Therapy",
        "avg_stay_days": 6,
        "base_cost": 78000.0,
        "medical_risk": 28.0,
    },
    {
        "diagnosis": "Community-Acquired Lobar Pneumonia",
        "icd10": "J18.1",
        "procedure": "IV Antimicrobial Therapy & High-Flow Oxygen Support",
        "avg_stay_days": 5,
        "base_cost": 94000.0,
        "medical_risk": 22.0,
    },
    {
        "diagnosis": "Lumbar Disc Herniation with Radiculopathy L4-L5",
        "icd10": "M51.26",
        "procedure": "Lumbar Microdiscectomy",
        "avg_stay_days": 4,
        "base_cost": 175000.0,
        "medical_risk": 20.0,
    },
    {
        "diagnosis": "Renal Calculus with Hydronephrosis",
        "icd10": "N20.0",
        "procedure": "Retrograde Intrarenal Surgery (RIRS) with DJ Stenting",
        "avg_stay_days": 2,
        "base_cost": 105000.0,
        "medical_risk": 15.0,
    },
    {
        "diagnosis": "Acute Gastroenteritis with Severe Dehydration",
        "icd10": "A09",
        "procedure": "Intravenous Fluid Rehydration & Enteric Monitoring",
        "avg_stay_days": 2,
        "base_cost": 38000.0,
        "medical_risk": 12.0,
    },
]

DOCUMENT_TYPES = [
    "Duly Filled Claim Form",
    "Health Insurance Card",
    "KYC / Identity Proof",
    "Cancelled Cheque",
    "Discharge Summary",
    "Final Hospital Bill",
    "Payment Receipts",
    "Doctor Consultation & Prescription",
    "Diagnostic & Investigation Report",
    "Pharmacy Bill",
    "Implant Invoice",
    "Ambulance Receipt",
    "Pre-authorization Approval",
    "FIR / Medico-legal Certificate",
    "Other Supporting Document",
]

PATIENT_NAMES = [
    ("Aarav Mehta", "Male", 34),
    ("Ananya Sharma", "Female", 29),
    ("Rohan Patel", "Male", 45),
    ("Sneha Deshmukh", "Female", 52),
    ("Vikram Singhania", "Male", 61),
    ("Deepika Nair", "Female", 38),
    ("Arjun Kapoor", "Male", 41),
    ("Pooja Verma", "Female", 33),
    ("Sanjay Gupta", "Male", 58),
    ("Meera Kulkarni", "Female", 49),
    ("Rahul Chatterjee", "Male", 26),
    ("Priyanka Rao", "Female", 37),
    ("Gautam Joshi", "Male", 64),
    ("Swati Iyer", "Female", 42),
    ("Nitin Agarwal", "Male", 50),
    ("Divya Menon", "Female", 31),
    ("Karan Malhotra", "Male", 39),
    ("Sunita Pillai", "Female", 56),
    ("Aditya Saxena", "Male", 47),
    ("Ritu Banerjee", "Female", 35),
]


def seed_demo_data(purge_existing: bool = False):
    db = SessionLocal()
    try:
        print("[*] ClaimBridge Demonstration Data Seeder Starting...", flush=True)

        if purge_existing:
            print("[*] Purging prior demo claims (CLM-2026-DEMO-%)...", flush=True)
            demo_claims = db.query(Claim).filter(Claim.claim_number.like("CLM-2026-DEMO-%")).all()
            for dc in demo_claims:
                db.delete(dc)
            db.commit()
            print(f"[+] Purged {len(demo_claims)} demo claims.", flush=True)

        # 1. Users
        print("[1/5] Checking and seeding scoped user accounts...", flush=True)
        existing_users = {u.email: u for u in db.query(User).all()}
        hashed_pwd = pwd_context.hash(DEFAULT_DEMO_PASSWORD)

        user_cache = {}
        if "admin@claimbridge.internal" not in existing_users:
            admin = User(
                id=uuid.uuid4(),
                full_name="ClaimBridge System Administrator",
                email="admin@claimbridge.internal",
                role="Admin",
                portal="Hospital",
                organization="ClaimBridge Core",
                password_hash=hashed_pwd,
            )
            db.add(admin)
            user_cache["admin"] = admin
        else:
            user_cache["admin"] = existing_users["admin@claimbridge.internal"]

        for h in HOSPITALS:
            em = h["coord_email"]
            if em not in existing_users:
                coord = User(
                    id=uuid.uuid4(),
                    full_name=h["coord_name"],
                    email=em,
                    role="Coordinator",
                    portal="Hospital",
                    organization=h["name"],
                    password_hash=hashed_pwd,
                )
                db.add(coord)
                user_cache[f"coord_{h['name']}"] = coord
            else:
                coord = existing_users[em]
                coord.organization = h["name"]
                coord.portal = "Hospital"
                user_cache[f"coord_{h['name']}"] = coord

        for t in TPAS:
            em = t["reviewer_email"]
            if em not in existing_users:
                rev = User(
                    id=uuid.uuid4(),
                    full_name=t["reviewer_name"],
                    email=em,
                    role="Reviewer",
                    portal="TPA",
                    organization=t["name"],
                    password_hash=hashed_pwd,
                )
                db.add(rev)
                user_cache[f"reviewer_{t['name']}"] = rev
            else:
                rev = existing_users[em]
                rev.organization = t["name"]
                rev.portal = "TPA"
                user_cache[f"reviewer_{t['name']}"] = rev

        db.commit()
        print(f"  [+] Active user accounts verified: {len(user_cache)}", flush=True)

        # 2. Patients
        print("[2/5] Checking and seeding patients...", flush=True)
        existing_patients = {p.full_name: p for p in db.query(Patient).all()}
        patient_cache = []
        for i, (name, gender, age) in enumerate(PATIENT_NAMES):
            if name in existing_patients:
                patient_cache.append(existing_patients[name])
            else:
                birth_year = date.today().year - age
                dob = date(birth_year, ((i % 12) + 1), ((i * 3 % 27) + 1))
                phone = f"+91 98{i:02d}4 5{i:02d}10"
                pat = Patient(
                    id=uuid.uuid4(),
                    full_name=name,
                    gender=gender,
                    date_of_birth=dob,
                    contact_number=phone,
                )
                db.add(pat)
                patient_cache.append(pat)
        db.commit()
        print(f"  [+] Active patients verified: {len(patient_cache)}", flush=True)

        # 3. Policies
        print("[3/5] Checking and seeding policies...", flush=True)
        existing_policies = {p.policy_number: p for p in db.query(Policy).all()}
        policy_cache = []
        for idx in range(80):
            pol_num = f"POL-2026-DEMO-{idx+1:03d}"
            if pol_num in existing_policies:
                policy_cache.append(existing_policies[pol_num])
            else:
                tpa_obj = TPAS[idx % len(TPAS)]
                ptype, coverage = POLICY_TYPES[idx % len(POLICY_TYPES)]
                start_date = date.today() - timedelta(days=200 + (idx * 5 % 150))
                end_date = start_date + timedelta(days=365)
                pol = Policy(
                    id=uuid.uuid4(),
                    policy_number=pol_num,
                    insurance_provider=tpa_obj["name"],
                    policy_type=ptype,
                    coverage_amount=coverage,
                    policy_start_date=start_date,
                    policy_end_date=end_date,
                )
                db.add(pol)
                policy_cache.append(pol)
        db.commit()
        print(f"  [+] Active policies verified: {len(policy_cache)}", flush=True)

        # 4. Claims & Related Trees
        print("[4/5] Checking and seeding 80 demonstration claims...", flush=True)
        existing_claims = set(r[0] for r in db.query(Claim.claim_number).all())
        
        claims_created = 0
        docs_created = 0

        # Pre-assign everything in memory, commit in batches of 20 claims
        batch_claims = []
        for i in range(80):
            claim_num = f"CLM-2026-DEMO-{i+1:03d}"
            if claim_num in existing_claims:
                continue

            claim_id = uuid.uuid4()
            h_obj = HOSPITALS[i % len(HOSPITALS)]
            pol_obj = policy_cache[i]
            patient_obj = patient_cache[i % len(patient_cache)]
            coord_user = user_cache[f"coord_{h_obj['name']}"]
            reviewer_user = user_cache[f"reviewer_{pol_obj.insurance_provider}"]
            clinical = CLINICAL_CASES[i % len(CLINICAL_CASES)]

            admit_offset = 10 + (i % 60)
            stay_days = clinical["avg_stay_days"]
            admission = date.today() - timedelta(days=admit_offset)
            discharge = admission + timedelta(days=stay_days)
            claimed_amount = Decimal(str(clinical["base_cost"] + (i * 1250 % 15000)))

            if i < 35:
                status = "Approved"
                stage = "12 Final Claim Decision"
                readiness = Decimal(str(round(86.50 + (i % 10) * 1.05, 2)))
                verif_status = "Passed"
                missing_docs = []
                mismatches = []
                risks = []
                pol_status = "Potentially Covered"
            elif i < 60:
                status = "Needs Review"
                stage = "11 Human Review Triage"
                readiness = Decimal(str(round(62.00 + (i % 12) * 1.25, 2)))
                verif_status = "Action Required"
                missing_docs = ["Pre-authorization Approval"] if i % 2 == 0 else []
                mismatches = [
                    f"Claimed amount (₹{float(claimed_amount):,.2f}) has minor discrepancy with pharmacy breakdown"
                ]
                risks = ["Readiness score requires manual verification before final sign-off"]
                pol_status = "Requires Verification"
            elif i < 70:
                status = "Rejected"
                stage = "12 Final Claim Decision"
                readiness = Decimal(str(round(31.50 + (i % 8) * 1.5, 2)))
                verif_status = "Failed"
                missing_docs = ["Discharge Summary", "Final Hospital Bill"]
                mismatches = ["Patient identity mismatch between Aadhaar KYC and Hospital Admission Register"]
                risks = ["Critical policy clause 4.2 exclusion violated: unverified elective cosmetic procedure"]
                pol_status = "Relevant Exclusion Detected"
            else:
                status = "Under Analysis"
                stage = random.choice([
                    "03 OCR & Text Extraction",
                    "05 Information Extraction",
                    "06 Medical Intelligence",
                    "08 Validation Engine",
                ])
                readiness = Decimal(str(round(50.00 + (i % 15) * 1.5, 2)))
                verif_status = "Requires Attention"
                missing_docs = []
                mismatches = []
                risks = ["Processing pipeline in progress"]
                pol_status = "Under Review"

            new_claim = Claim(
                id=claim_id,
                claim_number=claim_num,
                patient_id=patient_obj.id,
                policy_id=pol_obj.id,
                hospital_name=h_obj["name"],
                admission_date=admission,
                discharge_date=discharge,
                claimed_amount=claimed_amount,
                claim_status=status,
                current_stage=stage,
                readiness_score=readiness,
                created_by=coord_user.id,
            )
            db.add(new_claim)

            # Documents & Extractions (4 per claim)
            doc_specs = [
                ("Duly Filled Claim Form", f"claim_form_{claim_num}.pdf"),
                ("Discharge Summary", f"discharge_summary_{claim_num}.pdf"),
                ("Final Hospital Bill", f"final_hospital_bill_{claim_num}.pdf"),
            ]
            rot_doc_type = DOCUMENT_TYPES[3 + (i % (len(DOCUMENT_TYPES) - 3))]
            doc_specs.append((rot_doc_type, f"{rot_doc_type.lower().replace(' ', '_').replace('/', '_')}_{claim_num}.pdf"))

            for dtype, fname in doc_specs:
                doc_id = uuid.uuid4()
                cdoc = ClaimDocument(
                    id=doc_id,
                    claim_id=claim_id,
                    document_type=dtype,
                    file_name=fname,
                    file_path=f"/uploads/demo/{fname}",
                    processing_status="Completed",
                )
                db.add(cdoc)

                ext_data = {
                    "patient_name": patient_obj.full_name,
                    "age": date.today().year - patient_obj.date_of_birth.year,
                    "gender": patient_obj.gender,
                    "hospital_name": h_obj["name"],
                    "document_type": dtype,
                    "admission_date": str(admission),
                    "discharge_date": str(discharge),
                }

                if dtype == "Final Hospital Bill":
                    room_rent = float(claimed_amount) * 0.25
                    dr_fees = float(claimed_amount) * 0.30
                    pharm = float(claimed_amount) * 0.20
                    inv = float(claimed_amount) * 0.15
                    other = float(claimed_amount) * 0.10
                    ext_data.update({
                        "bill_number": f"BILL-{h_obj['name'][:3].upper()}-{i+1000}",
                        "room_charges": round(room_rent, 2),
                        "doctor_consultation_fees": round(dr_fees, 2),
                        "pharmacy_charges": round(pharm, 2),
                        "investigation_charges": round(inv, 2),
                        "tax_amount": round(other, 2),
                        "total_amount": float(claimed_amount),
                        "grand_total": float(claimed_amount),
                    })
                    raw_text = (
                        f"TAX INVOICE - {h_obj['name']}\n"
                        f"Patient: {patient_obj.full_name} | Admission: {admission} | Discharge: {discharge}\n"
                        f"Total Amount Payable: Rs {float(claimed_amount):,.2f}\n"
                    )
                elif dtype == "Discharge Summary":
                    ext_data.update({
                        "diagnosis": clinical["diagnosis"],
                        "procedure": clinical["procedure"],
                        "icd10_code": clinical["icd10"],
                        "treating_doctor": "Dr. A. K. Sen, Senior Consultant",
                    })
                    raw_text = (
                        f"DISCHARGE SUMMARY - {h_obj['name']}\n"
                        f"Diagnosis: {clinical['diagnosis']} (ICD-10: {clinical['icd10']})\n"
                        f"Procedure: {clinical['procedure']}\n"
                    )
                else:
                    ext_data.update({
                        "policy_number": pol_obj.policy_number,
                        "insurance_provider": pol_obj.insurance_provider,
                        "claimed_amount": float(claimed_amount),
                    })
                    raw_text = f"{dtype.upper()} - {patient_obj.full_name} - {pol_obj.policy_number}"

                dext = DocumentExtraction(
                    id=uuid.uuid4(),
                    document_id=doc_id,
                    extracted_text=raw_text,
                    extracted_data=ext_data,
                    ocr_confidence=Decimal(str(round(93.50 + (i % 6) * 1.0, 2))),
                    extraction_status="Completed",
                )
                db.add(dext)
                docs_created += 1

            # Medical Analysis
            med = MedicalAnalysis(
                id=uuid.uuid4(),
                claim_id=claim_id,
                diagnosis=clinical["diagnosis"],
                procedure=clinical["procedure"],
                analysis_result={
                    "icd10_code": clinical["icd10"],
                    "diagnosis_system": "ICD-10",
                    "clinical_necessity": "Confirmed",
                    "severity": "Moderate",
                },
                confidence_score=Decimal(str(round(88.00 + (i % 8) * 1.2, 2))),
                risk_score=Decimal(str(clinical["medical_risk"])),
                processing_status="Completed",
            )
            db.add(med)

            # Verification Result
            summary_payload = {
                "policy_intelligence": {
                    "policy_status": pol_status,
                    "relevant_exclusions": ["Cosmetic procedure exclusion (Clause 4.2)"] if status == "Rejected" else [],
                    "relevant_clauses": [
                        {"clause_id": "SEC-01", "clause_title": "Inpatient Hospitalization Coverage", "similarity": 0.94},
                    ],
                },
                "medical_intelligence": {
                    "processing_status": "Completed",
                    "diagnosis": clinical["diagnosis"],
                    "risk_score": clinical["medical_risk"],
                },
                "claim_readiness": {
                    "readiness_status": verif_status,
                    "readiness_score": float(readiness),
                },
            }

            v_res = VerificationResult(
                id=uuid.uuid4(),
                claim_id=claim_id,
                readiness_score=readiness,
                verification_status=verif_status,
                missing_documents=missing_docs,
                mismatches=mismatches,
                risk_indicators=risks,
                verification_summary=json.dumps(summary_payload),
            )
            db.add(v_res)

            # Claim History
            stages_trail = [
                ("Claim Created", "Under Analysis", "01 Secure Document Intake", "Intake form initialized by Hospital Coordinator"),
                ("Documents Uploaded", "Under Analysis", "02 Image/PDF Preprocessing", "4 package documents uploaded and converted"),
                ("OCR Processed", "Under Analysis", "03 OCR & Text Extraction", "Tesseract & LayoutLM extraction completed"),
                ("Validation Done", "Under Analysis", "08 Validation Engine", "Field validation & arithmetic reconciled"),
                ("Readiness Scored", "Under Analysis", "09 Claim Readiness Engine", f"Readiness assessed at {readiness}%"),
            ]
            if status == "Needs Review":
                stages_trail.append(("Escalated for Human Review", "Needs Review", "11 Human Review Triage", "Flagged for adjudicator inspection"))
            elif status == "Approved":
                stages_trail.append(("Final Claim Approved", "Approved", "12 Final Claim Decision", "Full approval granted by authorized TPA reviewer."))
            elif status == "Rejected":
                stages_trail.append(("Claim Rejected", "Rejected", "12 Final Claim Decision", "Rejected by TPA reviewer. Mandatory rationale recorded."))

            hist_time = datetime.now() - timedelta(hours=len(stages_trail) * 4)
            for action_name, s_val, stg_val, remark in stages_trail:
                hist_entry = ClaimHistory(
                    id=uuid.uuid4(),
                    claim_id=claim_id,
                    previous_status="Under Analysis",
                    new_status=s_val,
                    previous_stage="Intake",
                    new_stage=stg_val,
                    action=action_name,
                    remarks=remark,
                    performed_by=reviewer_user.id if "Approved" in action_name or "Rejected" in action_name else coord_user.id,
                    created_at=hist_time,
                )
                db.add(hist_entry)
                hist_time += timedelta(hours=3)

            claims_created += 1

            if (i + 1) % 20 == 0:
                db.commit()
                print(f"  [+] Committed batch {i+1}/80 demo claims to Neon...", flush=True)

        db.commit()
        print(f"\n[5/5] Demonstration Seeding Complete!", flush=True)
        print(f"  - New Claims Created: {claims_created}", flush=True)
        print(f"  - New Documents Created: {docs_created}", flush=True)

    except Exception as e:
        db.rollback()
        print(f"[!] Error: {e}", flush=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    purge = "--clean" in sys.argv or "--purge" in sys.argv
    seed_demo_data(purge_existing=purge)
