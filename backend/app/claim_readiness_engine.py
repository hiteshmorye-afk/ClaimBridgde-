"""
ClaimBridge Explainable Claim Readiness Assessment & Scoring System

Deterministic, evidence-grounded scoring engine evaluating claim completeness,
document reliability, and readiness for pre-authorization or reimbursement.

Seven Configurable Categories & Default Weights:
1. Patient Identity & Details: 15 pts
2. Insurance Policy Information: 20 pts
3. Medical Diagnosis & ICD-10: 20 pts
4. Required Documents: 20 pts (stage-specific: preauth vs final_auth vs reimbursement)
5. Document Quality & Correctness: 10 pts
6. Cross-Document Consistency: 10 pts
7. Consent & Authorization: 5 pts
Total: 100 pts

Readiness Levels:
- 90 - 100: Excellent Readiness
- 75 - 89: Good Readiness
- 50 - 74: Needs Attention
- 0 - 49: Incomplete

DISCLAIMER:
ClaimBridge Claim Readiness is an internal preparation and documentation assessment.
It is NOT a guarantee of approval, probability, medical diagnosis, or insurer official decision.
"""

from typing import Any, Dict, List, Optional
import json


# =========================================================================
# CONFIGURABLE CATEGORY WEIGHTS (Sum = 100.0)
# =========================================================================

DEFAULT_CATEGORY_WEIGHTS: Dict[str, float] = {
    "patient_identity": 15.0,
    "policy_information": 20.0,
    "medical_diagnosis": 20.0,
    "required_documents": 20.0,
    "document_quality": 10.0,
    "cross_document_consistency": 10.0,
    "consent_authorization": 5.0,
}

# =========================================================================
# STAGE-SPECIFIC REQUIRED DOCUMENTS
# =========================================================================

STAGE_REQUIRED_DOCUMENTS: Dict[str, List[str]] = {
    # Initial Pre-Authorization:
    # Requires identity, insurance card, doctor recommendation, pre-auth form.
    # CRITICAL: Final hospital bill and discharge summary are NOT required!
    "preauth": [
        "identity_proof",
        "insurance_card",
        "consultation_letter",
        "pre_authorization",
    ],
    "initial_preauth": [
        "identity_proof",
        "insurance_card",
        "consultation_letter",
        "pre_authorization",
    ],
    "cashless": [
        "identity_proof",
        "insurance_card",
        "consultation_letter",
        "pre_authorization",
    ],
    # Final Authorization / Discharge Clearance:
    # Requires detailed final bill, discharge summary, indoor case papers, pre-auth
    "final_auth": [
        "hospital_bill",
        "discharge_summary",
        "indoor_case_papers",
        "pre_authorization",
    ],
    "discharge": [
        "hospital_bill",
        "discharge_summary",
        "indoor_case_papers",
        "pre_authorization",
    ],
    "final_discharge": [
        "hospital_bill",
        "discharge_summary",
        "indoor_case_papers",
        "pre_authorization",
    ],
    # Post-Hospitalization Reimbursement Claim:
    "reimbursement": [
        "hospital_bill",
        "payment_receipt",
        "discharge_summary",
        "claim_form",
        "consultation_letter",
    ],
}

DOCUMENT_CATEGORY_ALIASES: Dict[str, List[str]] = {
    "identity_proof": ["identity_proof", "aadhaar", "pan", "passport", "voter_id", "kyc"],
    "insurance_card": ["insurance_card", "policy_schedule", "e_card", "health_card"],
    "consultation_letter": ["consultation_letter", "prescription", "doctor_note", "opd_slip"],
    "pre_authorization": ["pre_authorization", "preauth_form", "preauth_request", "estimate"],
    "hospital_bill": ["hospital_bill", "final_bill", "detailed_bill", "indoor_bill"],
    "discharge_summary": ["discharge_summary", "discharge_card"],
    "indoor_case_papers": ["indoor_case_papers", "clinical_notes", "ot_notes", "nursing_chart"],
    "payment_receipt": ["payment_receipt", "receipt", "settlement_voucher"],
    "claim_form": ["claim_form", "tpa_claim_form"],
    "diagnostic_report": ["diagnostic_report", "lab_report", "radiology_report"],
}

READINESS_DISCLAIMER = (
    "ClaimBridge Claim Readiness is an internal readiness assessment of documentation "
    "completeness, quality, and cross-consistency. It is NOT a guarantee of claim approval, "
    "approval probability, medical diagnosis, or official decision by the insurer or IRDAI. "
    "Final adjudication is solely subject to the insurer's policy terms and TPA evaluation."
)


# =========================================================================
# HELPER FUNCTIONS
# =========================================================================

def _get_val(obj: Any, *keys: str, default: Any = None) -> Any:
    """Extract a value from a dictionary, SQLAlchemy model, or object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and obj[k] is not None:
                return obj[k]
        return default
    for k in keys:
        if hasattr(obj, k):
            v = getattr(obj, k)
            if v is not None:
                return v
    return default


def _matches_category(doc_type: str, target_cat: str) -> bool:
    """Check if document type matches target category directly or via alias."""
    if not doc_type:
        return False
    norm_doc = doc_type.strip().lower()
    norm_target = target_cat.strip().lower()
    if norm_doc == norm_target:
        return True
    aliases = DOCUMENT_CATEGORY_ALIASES.get(norm_target, [norm_target])
    return norm_doc in aliases


def determine_readiness_level(score: float) -> str:
    """Map numeric score (0-100) to standard readiness level."""
    if score >= 90.0:
        return "Excellent Readiness"
    elif score >= 75.0:
        return "Good Readiness"
    elif score >= 50.0:
        return "Needs Attention"
    else:
        return "Incomplete"


# =========================================================================
# MAIN DETERMINISTIC CLAIM READINESS ENGINE
# =========================================================================

def calculate_explainable_claim_readiness(
    claim: Optional[Any] = None,
    patient: Optional[Any] = None,
    policy: Optional[Any] = None,
    documents: Optional[List[Any]] = None,
    extractions: Optional[Dict[str, Any]] = None,
    medical_analysis: Optional[Any] = None,
    verification_result: Optional[Any] = None,
    consents: Optional[List[Any]] = None,
    stage: str = "preauth",
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Calculate deterministic, transparent, and explainable Claim Readiness Assessment.

    Returns:
    - readiness_score (float 0-100)
    - readiness_level (Excellent / Good / Needs Attention / Incomplete)
    - is_provisional (bool)
    - provisional_reasons (list)
    - categories (dict of 7 categories with score, max, checks, deductions, actions)
    - missing_requirements (list)
    - recommended_actions (list of prioritized actions)
    - disclaimer (str)
    """
    active_weights = dict(DEFAULT_CATEGORY_WEIGHTS)
    if weights and isinstance(weights, dict):
        for k, v in weights.items():
            if k in active_weights:
                active_weights[k] = float(v)

    norm_stage = (stage or "preauth").strip().lower()
    if norm_stage not in STAGE_REQUIRED_DOCUMENTS:
        norm_stage = "preauth"

    documents_list = documents or []
    extractions_map = extractions or {}
    consents_list = consents or []

    categories_out: Dict[str, Any] = {}
    missing_requirements: List[str] = []
    recommended_actions: List[Dict[str, Any]] = []

    # ---------------------------------------------------------------------
    # 1. CATEGORY: PATIENT IDENTITY & DETAILS (Weight: 15 pts)
    # ---------------------------------------------------------------------
    cat1_weight = active_weights["patient_identity"]
    cat1_checks = []

    # Check 1.1: Patient Full Name (4 pts)
    pat_name = (
        _get_val(patient, "full_name", "name")
        or _get_val(claim, "patient_name")
        or ""
    )
    if pat_name and str(pat_name).strip():
        cat1_checks.append({
            "name": "Patient Full Name",
            "max_points": 4.0,
            "earned_points": 4.0,
            "status": "Passed",
            "identified_info": f"Patient name identified: '{pat_name}'",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat1_checks.append({
            "name": "Patient Full Name",
            "max_points": 4.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Patient Full Name",
            "deduction_reason": "Patient full name is missing from claim intake record.",
            "recommended_action": "Enter the patient's full legal name as per government ID in Step 2.",
        })

    # Check 1.2: Date of Birth or Age (3 pts)
    dob = _get_val(patient, "date_of_birth", "dob", "age") or _get_val(claim, "patient_dob", "patient_age")
    if dob:
        cat1_checks.append({
            "name": "Date of Birth / Age",
            "max_points": 3.0,
            "earned_points": 3.0,
            "status": "Passed",
            "identified_info": f"Patient DOB/Age recorded: {dob}",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat1_checks.append({
            "name": "Date of Birth / Age",
            "max_points": 3.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Patient Date of Birth / Age",
            "deduction_reason": "Patient date of birth or age is not recorded.",
            "recommended_action": "Provide the patient's date of birth in Step 2.",
        })

    # Check 1.3: Gender (2 pts)
    gender = _get_val(patient, "gender") or _get_val(claim, "patient_gender")
    if gender and str(gender).strip():
        cat1_checks.append({
            "name": "Patient Gender",
            "max_points": 2.0,
            "earned_points": 2.0,
            "status": "Passed",
            "identified_info": f"Gender recorded: {gender}",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat1_checks.append({
            "name": "Patient Gender",
            "max_points": 2.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Patient Gender",
            "deduction_reason": "Patient gender not recorded.",
            "recommended_action": "Specify the patient's gender.",
        })

    # Check 1.4: Contact Information (2 pts)
    contact = (
        _get_val(patient, "contact_number", "phone")
        or _get_val(patient, "emergency_contact_phone")
        or _get_val(claim, "contact_number")
    )
    if contact and str(contact).strip():
        cat1_checks.append({
            "name": "Contact Number",
            "max_points": 2.0,
            "earned_points": 2.0,
            "status": "Passed",
            "identified_info": f"Contact phone recorded: {contact}",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat1_checks.append({
            "name": "Contact Number",
            "max_points": 2.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Contact Number",
            "deduction_reason": "Patient primary contact number is missing.",
            "recommended_action": "Provide a valid 10-digit mobile contact number.",
        })

    # Check 1.5: Identity Proof & Aadhaar Verification (4 pts)
    has_id_doc = any(_matches_category(_get_val(d, "document_type"), "identity_proof") for d in documents_list)
    aadhaar_status = (
        _get_val(claim, "aadhaar_verification_status", "aadhaarVerificationStatus")
        or _get_val(patient, "aadhaar_verification_status")
        or ""
    )

    if aadhaar_status in ["Verified via Aadhaar QR/XML", "Cryptographically Verified", "Verified"]:
        cat1_checks.append({
            "name": "Identity Proof & Verification",
            "max_points": 4.0,
            "earned_points": 4.0,
            "status": "Passed",
            "identified_info": f"Identity verified via secure credential: {aadhaar_status}",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    elif has_id_doc:
        cat1_checks.append({
            "name": "Identity Proof & Verification",
            "max_points": 4.0,
            "earned_points": 2.5,
            "status": "Needs Attention",
            "identified_info": "Government identity proof document uploaded (pending Aadhaar QR/XML verification).",
            "missing_info": "Formal Aadhaar Digital Verification",
            "deduction_reason": "Identity document uploaded, but formal digital cryptographic verification has not been completed.",
            "recommended_action": "Complete Aadhaar QR/XML verification in Step 2 for high confidence.",
        })
    elif aadhaar_status in ["Name Mismatch", "Invalid Credential"]:
        cat1_checks.append({
            "name": "Identity Proof & Verification",
            "max_points": 4.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Matching Identity Proof",
            "deduction_reason": f"Aadhaar verification failed with status: '{aadhaar_status}'.",
            "recommended_action": "Verify patient name matches Aadhaar exactly or request manual coordinator review.",
        })
    else:
        cat1_checks.append({
            "name": "Identity Proof & Verification",
            "max_points": 4.0,
            "earned_points": 0.0,
            "status": "Pending",
            "identified_info": "",
            "missing_info": "Government Identity Proof",
            "deduction_reason": "Government identity proof (Aadhaar, Passport, Voter ID) not provided or verified.",
            "recommended_action": "Upload patient identity proof (Aadhaar card) in Step 5 or verify credential in Step 2.",
        })

    cat1_score = round(min(cat1_weight, sum(c["earned_points"] for c in cat1_checks)), 1)
    categories_out["patient_identity"] = {
        "name": "Patient Identity & Details",
        "key": "patient_identity",
        "weight": cat1_weight,
        "score": cat1_score,
        "status": "Passed" if cat1_score >= cat1_weight else ("Needs Attention" if cat1_score >= cat1_weight * 0.5 else "Incomplete"),
        "checks": cat1_checks,
        "identified_info": [c["identified_info"] for c in cat1_checks if c["identified_info"]],
        "missing_info": [c["missing_info"] for c in cat1_checks if c["missing_info"]],
        "deductions": [c["deduction_reason"] for c in cat1_checks if c["deduction_reason"]],
        "recommended_actions": [c["recommended_action"] for c in cat1_checks if c["recommended_action"]],
    }

    # ---------------------------------------------------------------------
    # 2. CATEGORY: INSURANCE POLICY INFORMATION (Weight: 20 pts)
    # ---------------------------------------------------------------------
    cat2_weight = active_weights["policy_information"]
    cat2_checks = []

    # Check 2.1: Policy / Member Number (5 pts)
    pol_num = (
        _get_val(policy, "policy_number")
        or _get_val(claim, "policy_number")
        or _get_val(policy, "member_id")
        or ""
    )
    if pol_num and str(pol_num).strip():
        cat2_checks.append({
            "name": "Policy / Member Number",
            "max_points": 5.0,
            "earned_points": 5.0,
            "status": "Passed",
            "identified_info": f"Policy number recorded: '{pol_num}'",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat2_checks.append({
            "name": "Policy / Member Number",
            "max_points": 5.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Insurance Policy Number",
            "deduction_reason": "Insurance policy or member ID is missing.",
            "recommended_action": "Enter active policy number in Step 2.",
        })

    # Check 2.2: Insurance Provider / TPA Name (4 pts)
    insurer = (
        _get_val(policy, "insurance_provider")
        or _get_val(policy, "tpa_name")
        or _get_val(claim, "insurance_provider")
        or ""
    )
    if insurer and str(insurer).strip():
        cat2_checks.append({
            "name": "Insurance Company / TPA",
            "max_points": 4.0,
            "earned_points": 4.0,
            "status": "Passed",
            "identified_info": f"Insurer / TPA identified: '{insurer}'",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat2_checks.append({
            "name": "Insurance Company / TPA",
            "max_points": 4.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Insurance Company / TPA",
            "deduction_reason": "Insurance provider or Third-Party Administrator not selected.",
            "recommended_action": "Select the patient's insurance company in Step 1.",
        })

    # Check 2.3: Policy Validity Period (4 pts)
    start_date = _get_val(policy, "policy_start_date")
    end_date = _get_val(policy, "policy_end_date")
    adm_date = _get_val(claim, "admission_date")

    if start_date and end_date:
        if adm_date and (adm_date < start_date or adm_date > end_date):
            cat2_checks.append({
                "name": "Policy Active Period",
                "max_points": 4.0,
                "earned_points": 0.0,
                "status": "Failed",
                "identified_info": f"Policy term: {start_date} to {end_date}",
                "missing_info": "Active Coverage on Admission Date",
                "deduction_reason": f"Admission date ({adm_date}) falls outside the policy term ({start_date} - {end_date}).",
                "recommended_action": "Verify admission date or provide proof of policy renewal.",
            })
        else:
            cat2_checks.append({
                "name": "Policy Active Period",
                "max_points": 4.0,
                "earned_points": 4.0,
                "status": "Passed",
                "identified_info": f"Policy validity confirmed active: {start_date} to {end_date}",
                "missing_info": "",
                "deduction_reason": "",
                "recommended_action": "",
            })
    else:
        cat2_checks.append({
            "name": "Policy Active Period",
            "max_points": 4.0,
            "earned_points": 1.5,
            "status": "Needs Attention",
            "identified_info": "Policy record present without complete start/end dates.",
            "missing_info": "Policy Start / Expiry Dates",
            "deduction_reason": "Policy start and end dates are not fully specified.",
            "recommended_action": "Verify policy start and expiry dates from the insurance schedule.",
        })

    # Check 2.4: Sum Insured / Coverage Limit (4 pts)
    cov_amt = _get_val(policy, "coverage_amount") or _get_val(claim, "coverage_amount")
    claimed_amt = _get_val(claim, "claimed_amount") or _get_val(claim, "preauth_amount")

    if cov_amt and float(cov_amt) > 0:
        if claimed_amt and float(claimed_amt) > float(cov_amt):
            cat2_checks.append({
                "name": "Sum Insured Adequacy",
                "max_points": 4.0,
                "earned_points": 2.0,
                "status": "Needs Attention",
                "identified_info": f"Sum Insured: ₹{float(cov_amt):,.2f}",
                "missing_info": "",
                "deduction_reason": f"Claimed amount (₹{float(claimed_amt):,.2f}) exceeds sum insured (₹{float(cov_amt):,.2f}).",
                "recommended_action": "Obtain patient co-payment consent for amount exceeding sum insured.",
            })
        else:
            cat2_checks.append({
                "name": "Sum Insured Adequacy",
                "max_points": 4.0,
                "earned_points": 4.0,
                "status": "Passed",
                "identified_info": f"Sum Insured (₹{float(cov_amt):,.2f}) adequate for estimate.",
                "missing_info": "",
                "deduction_reason": "",
                "recommended_action": "",
            })
    else:
        cat2_checks.append({
            "name": "Sum Insured Adequacy",
            "max_points": 4.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Policy Sum Insured",
            "deduction_reason": "Policy coverage amount or sum insured limit is not recorded.",
            "recommended_action": "Enter the total sum insured limit from the policy schedule.",
        })

    # Check 2.5: Insurance Card / Policy Schedule Uploaded (3 pts)
    has_card = any(_matches_category(_get_val(d, "document_type"), "insurance_card") for d in documents_list)
    if has_card:
        cat2_checks.append({
            "name": "Policy Document / E-Card",
            "max_points": 3.0,
            "earned_points": 3.0,
            "status": "Passed",
            "identified_info": "Insurance card or policy schedule document uploaded.",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat2_checks.append({
            "name": "Policy Document / E-Card",
            "max_points": 3.0,
            "earned_points": 0.0,
            "status": "Pending",
            "identified_info": "",
            "missing_info": "Insurance Card / Policy Schedule Document",
            "deduction_reason": "Insurance card or policy schedule document is missing.",
            "recommended_action": "Upload the patient's insurance e-card or policy schedule in Step 5.",
        })

    cat2_score = round(min(cat2_weight, sum(c["earned_points"] for c in cat2_checks)), 1)
    categories_out["policy_information"] = {
        "name": "Insurance Policy Information",
        "key": "policy_information",
        "weight": cat2_weight,
        "score": cat2_score,
        "status": "Passed" if cat2_score >= cat2_weight else ("Needs Attention" if cat2_score >= cat2_weight * 0.5 else "Incomplete"),
        "checks": cat2_checks,
        "identified_info": [c["identified_info"] for c in cat2_checks if c["identified_info"]],
        "missing_info": [c["missing_info"] for c in cat2_checks if c["missing_info"]],
        "deductions": [c["deduction_reason"] for c in cat2_checks if c["deduction_reason"]],
        "recommended_actions": [c["recommended_action"] for c in cat2_checks if c["recommended_action"]],
    }

    # ---------------------------------------------------------------------
    # 3. CATEGORY: MEDICAL DIAGNOSIS & ICD-10 (Weight: 20 pts)
    # ---------------------------------------------------------------------
    cat3_weight = active_weights["medical_diagnosis"]
    cat3_checks = []

    # Check 3.1: Primary Clinical Diagnosis (6 pts)
    diag = (
        _get_val(medical_analysis, "diagnosis")
        or _get_val(claim, "diagnosis")
        or ""
    )
    if diag and str(diag).strip():
        cat3_checks.append({
            "name": "Primary Clinical Diagnosis",
            "max_points": 6.0,
            "earned_points": 6.0,
            "status": "Passed",
            "identified_info": f"Diagnosis documented: '{diag}'",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat3_checks.append({
            "name": "Primary Clinical Diagnosis",
            "max_points": 6.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Primary Clinical Diagnosis",
            "deduction_reason": "Primary clinical diagnosis is not documented.",
            "recommended_action": "Enter the primary provisional medical diagnosis in Step 4.",
        })

    # Check 3.2: ICD-10 Coding (6 pts)
    icd10 = (
        _get_val(medical_analysis, "icd10_code")
        or _get_val(claim, "diagnosis_code")
        or ""
    )
    if icd10 and str(icd10).strip() and str(icd10).upper() not in ["UNSPECIFIED", "NONE", ""]:
        cat3_checks.append({
            "name": "ICD-10 Code Mapping",
            "max_points": 6.0,
            "earned_points": 6.0,
            "status": "Passed",
            "identified_info": f"Mapped to standard ICD-10 code: {str(icd10).upper()}",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat3_checks.append({
            "name": "ICD-10 Code Mapping",
            "max_points": 6.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Standard ICD-10 Code",
            "deduction_reason": "No valid ICD-10 code mapped to the clinical diagnosis.",
            "recommended_action": "Map the clinical condition to an ICD-10 code using the diagnosis search in Step 4.",
        })

    # Check 3.3: Proposed Treatment / Procedure (4 pts)
    proc = (
        _get_val(medical_analysis, "procedure")
        or _get_val(claim, "procedure")
        or _get_val(claim, "treatment_type")
        or ""
    )
    if proc and str(proc).strip():
        cat3_checks.append({
            "name": "Proposed Treatment / Line of Care",
            "max_points": 4.0,
            "earned_points": 4.0,
            "status": "Passed",
            "identified_info": f"Line of treatment / procedure documented: '{proc}'",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat3_checks.append({
            "name": "Proposed Treatment / Line of Care",
            "max_points": 4.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Treatment / Procedure Information",
            "deduction_reason": "Proposed treatment, surgical procedure or medical line not specified.",
            "recommended_action": "Specify whether treatment is surgical or medical management in Step 4.",
        })

    # Check 3.4: Admission Necessity Justification (4 pts)
    clinical_notes = _get_val(claim, "clinical_notes") or _get_val(medical_analysis, "clinical_narrative")
    med_conf = _get_val(medical_analysis, "confidence_score")
    if clinical_notes or (med_conf is not None and float(med_conf) >= 0.70):
        cat3_checks.append({
            "name": "Inpatient Medical Necessity",
            "max_points": 4.0,
            "earned_points": 4.0,
            "status": "Passed",
            "identified_info": "Medical necessity and inpatient admission justified by clinical documentation.",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat3_checks.append({
            "name": "Inpatient Medical Necessity",
            "max_points": 4.0,
            "earned_points": 1.0,
            "status": "Needs Attention",
            "identified_info": "",
            "missing_info": "Clinical Rationale for Admission",
            "deduction_reason": "Clinical justification for inpatient stay vs daycare/OPD is minimal.",
            "recommended_action": "Provide treating doctor clinical notes explaining the necessity of admission.",
        })

    cat3_score = round(min(cat3_weight, sum(c["earned_points"] for c in cat3_checks)), 1)
    categories_out["medical_diagnosis"] = {
        "name": "Medical Diagnosis & ICD-10",
        "key": "medical_diagnosis",
        "weight": cat3_weight,
        "score": cat3_score,
        "status": "Passed" if cat3_score >= cat3_weight else ("Needs Attention" if cat3_score >= cat3_weight * 0.5 else "Incomplete"),
        "checks": cat3_checks,
        "identified_info": [c["identified_info"] for c in cat3_checks if c["identified_info"]],
        "missing_info": [c["missing_info"] for c in cat3_checks if c["missing_info"]],
        "deductions": [c["deduction_reason"] for c in cat3_checks if c["deduction_reason"]],
        "recommended_actions": [c["recommended_action"] for c in cat3_checks if c["recommended_action"]],
    }

    # ---------------------------------------------------------------------
    # 4. CATEGORY: REQUIRED DOCUMENTS BY STAGE (Weight: 20 pts)
    # ---------------------------------------------------------------------
    cat4_weight = active_weights["required_documents"]
    required_doc_types = STAGE_REQUIRED_DOCUMENTS.get(norm_stage, STAGE_REQUIRED_DOCUMENTS["preauth"])
    cat4_checks = []
    points_per_doc = round(cat4_weight / max(1, len(required_doc_types)), 2)

    for doc_req in required_doc_types:
        # Find matching documents in claim
        matching_docs = [
            d for d in documents_list
            if _matches_category(_get_val(d, "document_type"), doc_req)
        ]

        readable_name = doc_req.replace("_", " ").title()

        if not matching_docs:
            cat4_checks.append({
                "name": f"Document: {readable_name}",
                "max_points": points_per_doc,
                "earned_points": 0.0,
                "status": "Failed",
                "identified_info": "",
                "missing_info": readable_name,
                "deduction_reason": f"Mandatory document '{readable_name}' is missing for {norm_stage} stage.",
                "recommended_action": f"Upload {readable_name} in Step 5 (Document Upload).",
            })
            missing_requirements.append(f"Upload {readable_name}")
        else:
            primary_doc = matching_docs[0]
            cat_status = _get_val(primary_doc, "category_status", "categoryStatus") or ""
            cat_match = _get_val(primary_doc, "category_match", "categoryMatch")

            if cat_status == "Incorrect Document Type" or cat_match is False:
                cat4_checks.append({
                    "name": f"Document: {readable_name}",
                    "max_points": points_per_doc,
                    "earned_points": 0.0,
                    "status": "Failed",
                    "identified_info": f"File uploaded: '{_get_val(primary_doc, 'file_name')}'",
                    "missing_info": f"Valid {readable_name}",
                    "deduction_reason": f"Uploaded file was flagged as Incorrect Document Type for {readable_name}.",
                    "recommended_action": f"Replace with an actual {readable_name} document.",
                })
                missing_requirements.append(f"Correct {readable_name} (Category Mismatch)")
            elif cat_status == "Category Unconfirmed" or cat_match is None:
                earned = round(points_per_doc * 0.6, 2)
                cat4_checks.append({
                    "name": f"Document: {readable_name}",
                    "max_points": points_per_doc,
                    "earned_points": earned,
                    "status": "Needs Attention",
                    "identified_info": f"File uploaded: '{_get_val(primary_doc, 'file_name')}'",
                    "missing_info": "",
                    "deduction_reason": f"Document content could not be confirmed as {readable_name} with high confidence.",
                    "recommended_action": f"Verify OCR readability of {readable_name}.",
                })
            else:
                cat4_checks.append({
                    "name": f"Document: {readable_name}",
                    "max_points": points_per_doc,
                    "earned_points": points_per_doc,
                    "status": "Passed",
                    "identified_info": f"Verified {readable_name} uploaded: '{_get_val(primary_doc, 'file_name')}'",
                    "missing_info": "",
                    "deduction_reason": "",
                    "recommended_action": "",
                })

    cat4_score = round(min(cat4_weight, sum(c["earned_points"] for c in cat4_checks)), 1)
    categories_out["required_documents"] = {
        "name": f"Required Documents ({norm_stage.replace('_', ' ').title()})",
        "key": "required_documents",
        "weight": cat4_weight,
        "score": cat4_score,
        "status": "Passed" if cat4_score >= cat4_weight else ("Needs Attention" if cat4_score >= cat4_weight * 0.5 else "Incomplete"),
        "checks": cat4_checks,
        "identified_info": [c["identified_info"] for c in cat4_checks if c["identified_info"]],
        "missing_info": [c["missing_info"] for c in cat4_checks if c["missing_info"]],
        "deductions": [c["deduction_reason"] for c in cat4_checks if c["deduction_reason"]],
        "recommended_actions": [c["recommended_action"] for c in cat4_checks if c["recommended_action"]],
    }

    # ---------------------------------------------------------------------
    # 5. CATEGORY: DOCUMENT QUALITY & CORRECTNESS (Weight: 10 pts)
    # ---------------------------------------------------------------------
    cat5_weight = active_weights["document_quality"]
    cat5_checks = []

    if not documents_list:
        cat5_checks.append({
            "name": "Document Inventory",
            "max_points": cat5_weight,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "All Claim Documents",
            "deduction_reason": "No documents uploaded to assess OCR quality or document type correctness.",
            "recommended_action": "Upload required claim documents in Step 5.",
        })
        cat5_score = 0.0
    else:
        # Check 5.1: OCR Readability & Text Legibility (4 pts)
        ocr_confidences = []
        unreadable_docs = []
        for d in documents_list:
            d_id = str(_get_val(d, "id"))
            ext = extractions_map.get(d_id)
            conf = _get_val(ext, "ocr_confidence") or _get_val(d, "ocr_confidence")
            has_txt = bool(_get_val(ext, "extracted_text") or _get_val(d, "extracted_text"))
            if conf is not None:
                val = float(conf)
                if val <= 1.0:
                    val = val * 100.0
                ocr_confidences.append(val)
            if not has_txt:
                unreadable_docs.append(_get_val(d, "file_name", default="File"))

        avg_ocr = (sum(ocr_confidences) / len(ocr_confidences)) if ocr_confidences else 0.0

        if not unreadable_docs and avg_ocr >= 75.0:
            cat5_checks.append({
                "name": "OCR Readability & Legibility",
                "max_points": 4.0,
                "earned_points": 4.0,
                "status": "Passed",
                "identified_info": f"High OCR legibility across {len(documents_list)} documents (avg {avg_ocr:.1f}%).",
                "missing_info": "",
                "deduction_reason": "",
                "recommended_action": "",
            })
        elif avg_ocr >= 50.0:
            cat5_checks.append({
                "name": "OCR Readability & Legibility",
                "max_points": 4.0,
                "earned_points": 2.5,
                "status": "Needs Attention",
                "identified_info": f"Moderate OCR legibility (avg {avg_ocr:.1f}%).",
                "missing_info": "",
                "deduction_reason": "Some documents contain faded or handwritten regions requiring verification.",
                "recommended_action": "Review extracted fields for low-confidence documents.",
            })
        else:
            cat5_checks.append({
                "name": "OCR Readability & Legibility",
                "max_points": 4.0,
                "earned_points": 0.0,
                "status": "Failed",
                "identified_info": "",
                "missing_info": "Legible Document Scans",
                "deduction_reason": f"Poor OCR legibility detected (avg {avg_ocr:.1f}%).",
                "recommended_action": "Re-upload clean, high-resolution scans of unreadable documents.",
            })

        # Check 5.2: Document Category Correctness (4 pts)
        incorrect_docs = []
        for d in documents_list:
            c_stat = _get_val(d, "category_status", "categoryStatus")
            c_match = _get_val(d, "category_match", "categoryMatch")
            if c_stat == "Incorrect Document Type" or c_match is False:
                incorrect_docs.append(_get_val(d, "file_name", default="File"))

        if not incorrect_docs:
            cat5_checks.append({
                "name": "Document Category Classification",
                "max_points": 4.0,
                "earned_points": 4.0,
                "status": "Passed",
                "identified_info": "All uploaded documents match their assigned categories.",
                "missing_info": "",
                "deduction_reason": "",
                "recommended_action": "",
            })
        else:
            cat5_checks.append({
                "name": "Document Category Classification",
                "max_points": 4.0,
                "earned_points": 0.0,
                "status": "Failed",
                "identified_info": "",
                "missing_info": "Correct Document Categories",
                "deduction_reason": f"{len(incorrect_docs)} file(s) flagged as 'Incorrect Document Type': {', '.join(incorrect_docs[:2])}.",
                "recommended_action": "Re-upload the correct files matching the required document types.",
            })

        # Check 5.3: File Integrity & PDF Parsing (2 pts)
        failed_processing = [
            _get_val(d, "file_name", default="File")
            for d in documents_list
            if _get_val(d, "processing_status") in ["Failed", "Error"]
        ]
        if not failed_processing:
            cat5_checks.append({
                "name": "File Integrity & Parsing",
                "max_points": 2.0,
                "earned_points": 2.0,
                "status": "Passed",
                "identified_info": "All files parsed and structurally validated without corruption.",
                "missing_info": "",
                "deduction_reason": "",
                "recommended_action": "",
            })
        else:
            cat5_checks.append({
                "name": "File Integrity & Parsing",
                "max_points": 2.0,
                "earned_points": 0.0,
                "status": "Failed",
                "identified_info": "",
                "missing_info": "Intact PDF Files",
                "deduction_reason": f"File parsing failed for: {', '.join(failed_processing)}.",
                "recommended_action": "Re-upload uncorrupted PDF documents.",
            })

        cat5_score = round(min(cat5_weight, sum(c["earned_points"] for c in cat5_checks)), 1)

    categories_out["document_quality"] = {
        "name": "Document Quality & Correctness",
        "key": "document_quality",
        "weight": cat5_weight,
        "score": cat5_score,
        "status": "Passed" if cat5_score >= cat5_weight else ("Needs Attention" if cat5_score >= cat5_weight * 0.5 else "Incomplete"),
        "checks": cat5_checks,
        "identified_info": [c["identified_info"] for c in cat5_checks if c["identified_info"]],
        "missing_info": [c["missing_info"] for c in cat5_checks if c["missing_info"]],
        "deductions": [c["deduction_reason"] for c in cat5_checks if c["deduction_reason"]],
        "recommended_actions": [c["recommended_action"] for c in cat5_checks if c["recommended_action"]],
    }

    # ---------------------------------------------------------------------
    # 6. CATEGORY: CROSS-DOCUMENT CONSISTENCY (Weight: 10 pts)
    # ---------------------------------------------------------------------
    cat6_weight = active_weights["cross_document_consistency"]
    cat6_checks = []

    mismatches = _get_val(verification_result, "mismatches") or []
    if isinstance(mismatches, str):
        try:
            mismatches = json.loads(mismatches)
        except Exception:
            mismatches = []

    # Check 6.1: Patient Name Reconciliation (3 pts)
    has_name_mismatch = any(
        "name" in str(m).lower() or "patient" in str(m).lower()
        for m in mismatches
    )
    if not has_name_mismatch:
        cat6_checks.append({
            "name": "Patient Name Cross-Reconciliation",
            "max_points": 3.0,
            "earned_points": 3.0,
            "status": "Passed",
            "identified_info": "Patient name matches consistently across all uploaded records.",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat6_checks.append({
            "name": "Patient Name Cross-Reconciliation",
            "max_points": 3.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Consistent Patient Name",
            "deduction_reason": "Patient name differs between uploaded document and claim record.",
            "recommended_action": "Reconcile patient name between ID proof and hospital admission record.",
        })

    # Check 6.2: Policy Number Cross-Reconciliation (3 pts)
    has_pol_mismatch = any(
        "policy" in str(m).lower() or "member" in str(m).lower()
        for m in mismatches
    )
    if not has_pol_mismatch:
        cat6_checks.append({
            "name": "Policy Identifier Cross-Reconciliation",
            "max_points": 3.0,
            "earned_points": 3.0,
            "status": "Passed",
            "identified_info": "Policy number is consistent across all uploaded documents.",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat6_checks.append({
            "name": "Policy Identifier Cross-Reconciliation",
            "max_points": 3.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Consistent Policy Number",
            "deduction_reason": "Policy number on uploaded document does not match active policy.",
            "recommended_action": "Verify and align policy number with the insurance card.",
        })

    # Check 6.3: Financial Amount Reconciliation (2 pts)
    has_amt_mismatch = any(
        "amount" in str(m).lower() or "cost" in str(m).lower() or "bill" in str(m).lower()
        for m in mismatches
    )
    if not has_amt_mismatch:
        cat6_checks.append({
            "name": "Financial Arithmetic & Total Reconciliation",
            "max_points": 2.0,
            "earned_points": 2.0,
            "status": "Passed",
            "identified_info": "Claimed amount matches document estimates and bill figures.",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat6_checks.append({
            "name": "Financial Arithmetic & Total Reconciliation",
            "max_points": 2.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Consistent Financial Amount",
            "deduction_reason": "Discrepancy detected between claimed amount and document financial figures.",
            "recommended_action": "Reconcile claimed amount with the hospital estimate / bill breakdown.",
        })

    # Check 6.4: Date Chronology (2 pts)
    adm_d = _get_val(claim, "admission_date")
    dis_d = _get_val(claim, "discharge_date")
    if adm_d and dis_d and dis_d < adm_d:
        cat6_checks.append({
            "name": "Hospitalization Date Chronology",
            "max_points": 2.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Valid Chronological Dates",
            "deduction_reason": f"Discharge date ({dis_d}) precedes admission date ({adm_d}).",
            "recommended_action": "Correct admission and discharge dates.",
        })
    else:
        cat6_checks.append({
            "name": "Hospitalization Date Chronology",
            "max_points": 2.0,
            "earned_points": 2.0,
            "status": "Passed",
            "identified_info": "Admission and discharge dates follow valid chronological sequence.",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })

    cat6_score = round(min(cat6_weight, sum(c["earned_points"] for c in cat6_checks)), 1)
    categories_out["cross_document_consistency"] = {
        "name": "Cross-Document Consistency",
        "key": "cross_document_consistency",
        "weight": cat6_weight,
        "score": cat6_score,
        "status": "Passed" if cat6_score >= cat6_weight else ("Needs Attention" if cat6_score >= cat6_weight * 0.5 else "Incomplete"),
        "checks": cat6_checks,
        "identified_info": [c["identified_info"] for c in cat6_checks if c["identified_info"]],
        "missing_info": [c["missing_info"] for c in cat6_checks if c["missing_info"]],
        "deductions": [c["deduction_reason"] for c in cat6_checks if c["deduction_reason"]],
        "recommended_actions": [c["recommended_action"] for c in cat6_checks if c["recommended_action"]],
    }

    # ---------------------------------------------------------------------
    # 7. CATEGORY: CONSENT & AUTHORIZATION (Weight: 5 pts)
    # ---------------------------------------------------------------------
    cat7_weight = active_weights["consent_authorization"]
    cat7_checks = []

    # Check 7.1: Patient / Attendant Cashless Consent (3 pts)
    has_consent = (
        bool(consents_list and any(_get_val(c, "status") in ["Given", "Signed", "Approved"] for c in consents_list))
        or bool(_get_val(claim, "patient_consent_given", "consent_given"))
        or any(_matches_category(_get_val(d, "document_type"), "patient_consent") for d in documents_list)
    )

    if has_consent:
        cat7_checks.append({
            "name": "Patient / Attendant Cashless Consent",
            "max_points": 3.0,
            "earned_points": 3.0,
            "status": "Passed",
            "identified_info": "Signed patient / attendant cashless consent verified.",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat7_checks.append({
            "name": "Patient / Attendant Cashless Consent",
            "max_points": 3.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Signed Patient Consent",
            "deduction_reason": "Signed patient cashless consent declaration is missing.",
            "recommended_action": "Record signed patient / guardian cashless consent in Step 2 or upload consent form.",
        })

    # Check 7.2: Treating Doctor Declaration / Registration (2 pts)
    has_doctor = bool(
        _get_val(claim, "doctor_name")
        or _get_val(claim, "treating_doctor")
        or _get_val(medical_analysis, "doctor_name")
        or any(_matches_category(_get_val(d, "document_type"), "consultation_letter") for d in documents_list)
    )

    if has_doctor:
        cat7_checks.append({
            "name": "Treating Doctor Declaration & Authorization",
            "max_points": 2.0,
            "earned_points": 2.0,
            "status": "Passed",
            "identified_info": "Treating doctor authorization and clinical declaration recorded.",
            "missing_info": "",
            "deduction_reason": "",
            "recommended_action": "",
        })
    else:
        cat7_checks.append({
            "name": "Treating Doctor Declaration & Authorization",
            "max_points": 2.0,
            "earned_points": 0.0,
            "status": "Failed",
            "identified_info": "",
            "missing_info": "Treating Doctor Declaration",
            "deduction_reason": "Treating doctor declaration or clinical signature is missing.",
            "recommended_action": "Ensure treating doctor's name, registration, and declaration are recorded.",
        })

    cat7_score = round(min(cat7_weight, sum(c["earned_points"] for c in cat7_checks)), 1)
    categories_out["consent_authorization"] = {
        "name": "Consent & Authorization",
        "key": "consent_authorization",
        "weight": cat7_weight,
        "score": cat7_score,
        "status": "Passed" if cat7_score >= cat7_weight else ("Needs Attention" if cat7_score >= cat7_weight * 0.5 else "Incomplete"),
        "checks": cat7_checks,
        "identified_info": [c["identified_info"] for c in cat7_checks if c["identified_info"]],
        "missing_info": [c["missing_info"] for c in cat7_checks if c["missing_info"]],
        "deductions": [c["deduction_reason"] for c in cat7_checks if c["deduction_reason"]],
        "recommended_actions": [c["recommended_action"] for c in cat7_checks if c["recommended_action"]],
    }

    # =====================================================================
    # TOTAL DETERMINISTIC SCORE (0 - 100)
    # =====================================================================
    raw_total = sum(cat["score"] for cat in categories_out.values())
    total_score = round(max(0.0, min(100.0, raw_total)), 1)

    readiness_level = determine_readiness_level(total_score)

    # ---------------------------------------------------------------------
    # PROVISIONAL FLAG & CRITICAL PREREQUISITES
    # ---------------------------------------------------------------------
    is_provisional = False
    provisional_reasons: List[str] = []

    if not pat_name:
        is_provisional = True
        provisional_reasons.append("Patient full legal name is missing.")
    if not pol_num:
        is_provisional = True
        provisional_reasons.append("Insurance policy number is missing.")
    if not diag:
        is_provisional = True
        provisional_reasons.append("Primary medical diagnosis is missing.")
    if not documents_list:
        is_provisional = True
        provisional_reasons.append("No claim documents have been uploaded.")
    if total_score < 40.0:
        is_provisional = True
        provisional_reasons.append(f"Score ({total_score}%) is below minimum baseline readiness threshold (40%).")

    # High-level operational readiness status
    if total_score >= 85.0 and not is_provisional:
        readiness_status = "Ready for TPA Pre-Auth Submission"
    elif total_score >= 70.0 and not is_provisional:
        readiness_status = "Conditionally Ready (Minor Gaps)"
    else:
        readiness_status = "Needs Human Review & Corrections"

    # Compile prioritized recommended actions with workflow step targets
    step_targets = {
        "patient_identity": {"step": 2, "tab": "patient", "title": "Step 2: Patient & Policy"},
        "policy_information": {"step": 2, "tab": "policy", "title": "Step 2: Patient & Policy"},
        "medical_diagnosis": {"step": 4, "tab": "diagnosis", "title": "Step 4: Medical Diagnosis & ICD-10"},
        "required_documents": {"step": 5, "tab": "documents", "title": "Step 5: Document Upload"},
        "document_quality": {"step": 5, "tab": "documents", "title": "Step 5: Document Upload"},
        "cross_document_consistency": {"step": 5, "tab": "reconciliation", "title": "Document Reconciliation"},
        "consent_authorization": {"step": 2, "tab": "consent", "title": "Step 2: Patient Consent"},
    }

    seen_actions = set()
    for cat_key, cat_data in categories_out.items():
        for action in cat_data["recommended_actions"]:
            if action and action not in seen_actions:
                seen_actions.add(action)
                target_meta = step_targets.get(cat_key, {"step": 1, "tab": "general", "title": "Claim Wizard"})
                recommended_actions.append({
                    "action": action,
                    "category": cat_data["name"],
                    "categoryKey": cat_key,
                    "targetStep": target_meta["step"],
                    "targetTab": target_meta["tab"],
                    "targetTitle": target_meta["title"],
                })

    category_list = [
        categories_out["patient_identity"],
        categories_out["policy_information"],
        categories_out["medical_diagnosis"],
        categories_out["required_documents"],
        categories_out["document_quality"],
        categories_out["cross_document_consistency"],
        categories_out["consent_authorization"],
    ]

    return {
        "readiness_score": total_score,
        "readiness_level": readiness_level,
        "readiness_status": readiness_status,
        "stage": norm_stage,
        "is_provisional": is_provisional,
        "provisional_reasons": provisional_reasons,
        "categories": categories_out,
        "category_list": category_list,
        "missing_requirements": missing_requirements,
        "recommended_actions": recommended_actions,
        "disclaimer": READINESS_DISCLAIMER,
        "total_weight": 100.0,
    }


# =========================================================================
# BACKWARDS COMPATIBILITY WRAPPERS FOR PIPELINE
# =========================================================================

def calculate_validation_score(validation_result: Dict[str, Any]) -> float:
    readiness_score = validation_result.get("readiness_score", 0.0)
    return max(0.0, min(float(readiness_score), 100.0))


def calculate_medical_score(medical_result: Dict[str, Any]) -> float:
    confidence = medical_result.get("confidence_score", 0.0)
    score = float(confidence) * 100
    if not medical_result.get("medical_terms"):
        score = min(score, 30.0)
    return max(0.0, min(score, 100.0))


def calculate_policy_score(policy_result: Dict[str, Any]) -> float:
    retrieval_confidence = policy_result.get("retrieval_confidence", 0.0)
    score = float(retrieval_confidence) * 100
    status = policy_result.get("policy_status", "")
    if status == "Potentially Covered":
        score += 20.0
    elif status == "Relevant Exclusion Detected":
        score += 10.0
    elif status == "Insufficient Policy Evidence":
        score = min(score, 30.0)
    return max(0.0, min(score, 100.0))


def calculate_ocr_score(ocr_result: Dict[str, Any]) -> float:
    confidence = ocr_result.get("confidence", 0.0)
    return max(0.0, min(float(confidence) * 100, 100.0))


def calculate_overall_readiness(
    validation_score: float,
    medical_score: float,
    policy_score: float,
    ocr_score: float,
) -> float:
    return round(
        validation_score * 0.35
        + medical_score * 0.25
        + policy_score * 0.25
        + ocr_score * 0.15,
        2,
    )


def determine_readiness_status(
    overall_score: float,
    validation_result: Dict[str, Any],
    medical_result: Dict[str, Any],
    policy_result: Dict[str, Any],
) -> str:
    ver_status = validation_result.get("verification_status", "")
    pol_status = policy_result.get("policy_status", "")
    med_status = medical_result.get("processing_status", "")

    if ver_status == "Needs Review":
        return "Needs Human Review"
    if pol_status in ["Relevant Exclusion Detected", "Insufficient Policy Evidence"]:
        return "Needs Human Review"
    if med_status == "Insufficient Data":
        return "Needs Human Review"
    if overall_score >= 80:
        return "Ready for Next Stage"
    if overall_score >= 60:
        return "Conditionally Ready"
    return "Needs Human Review"


def generate_readiness_reasons(
    validation_result: Dict[str, Any],
    medical_result: Dict[str, Any],
    policy_result: Dict[str, Any],
    overall_score: float,
) -> List[str]:
    reasons = []
    if validation_result.get("missing_fields"):
        reasons.append("Required claim information is incomplete.")
    if validation_result.get("mismatches"):
        reasons.append("Consistency mismatches were detected.")
    if not validation_result.get("missing_fields") and not validation_result.get("mismatches"):
        reasons.append("Required claim information passed structural validation.")

    if medical_result.get("diagnosis"):
        reasons.append("Diagnosis information was identified.")
    else:
        reasons.append("Diagnosis information was not confidently identified.")

    if policy_result.get("policy_status") == "Potentially Covered":
        reasons.append("Relevant policy coverage evidence was identified.")
    elif policy_result.get("relevant_exclusions"):
        reasons.append("A policy exclusion may be relevant to the claim.")

    reasons.append(f"Overall claim readiness score: {overall_score:.2f}%.")
    return reasons


def evaluate_claim_readiness(
    ocr_result: Dict[str, Any],
    validation_result: Dict[str, Any],
    medical_result: Dict[str, Any],
    policy_result: Dict[str, Any],
    stage: str = "preauth",
) -> Dict[str, Any]:
    """
    Backwards-compatible wrapper used by pipeline.py.
    Calculates explainable readiness while returning legacy component fields.
    """
    validation_score = calculate_validation_score(validation_result)
    medical_score = calculate_medical_score(medical_result)
    policy_score = calculate_policy_score(policy_result)
    ocr_score = calculate_ocr_score(ocr_result)

    overall_score = calculate_overall_readiness(
        validation_score=validation_score,
        medical_score=medical_score,
        policy_score=policy_score,
        ocr_score=ocr_score,
    )

    readiness_status = determine_readiness_status(
        overall_score=overall_score,
        validation_result=validation_result,
        medical_result=medical_result,
        policy_result=policy_result,
    )

    reasons = generate_readiness_reasons(
        validation_result=validation_result,
        medical_result=medical_result,
        policy_result=policy_result,
        overall_score=overall_score,
    )

    # Also compute 7-category explainable readiness
    explainable = calculate_explainable_claim_readiness(
        medical_analysis=medical_result,
        verification_result=validation_result,
        stage=stage,
    )

    return {
        "readiness_score": overall_score,
        "readiness_status": readiness_status,
        "component_scores": {
            "validation_score": round(validation_score, 2),
            "medical_score": round(medical_score, 2),
            "policy_score": round(policy_score, 2),
            "ocr_score": round(ocr_score, 2),
        },
        "readiness_reasons": reasons,
        "processing_status": "Analyzed",
        "explainable_assessment": explainable,
    }
