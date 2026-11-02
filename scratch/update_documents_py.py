import re

with open("backend/app/documents.py", "r", encoding="utf-8") as f:
    code = f.read()

# Add imports
if "from .document_reliability import calculate_document_reliability" not in code:
    import_target = "from .validation_engine import validate_cross_document_consistency"
    import_replacement = """from .document_classifier import normalize_category_name
from .document_reliability import calculate_document_reliability
from .validation_engine import validate_cross_document_consistency"""
    assert import_target in code, "import_target not found"
    code = code.replace(import_target, import_replacement, 1)

# Helper definitions for category compatibility
compatibility_code = '''
COMPATIBLE_CATEGORIES = {
    "identity_proof": {"identity_proof", "aadhaar", "pan", "passport", "voter_id", "kyc"},
    "insurance_card": {"insurance_card", "insurance_policy", "policy_schedule", "health_card"},
    "claim_form": {"claim_form", "part_a", "part_b", "duly_filled_claim_form"},
    "consultation_letter": {"consultation_letter", "prescription", "opd_slip", "referral_letter"},
    "diagnostic_report": {"diagnostic_report", "lab_report", "investigation_report", "pathology_report", "radiology_report"},
    "hospital_bill": {"hospital_bill", "final_hospital_bill", "bill", "invoice"},
    "discharge_summary": {"discharge_summary", "discharge_card"},
    "payment_receipt": {"payment_receipt", "receipt", "advance_receipt"},
    "pharmacy_bill": {"pharmacy_bill", "medical_store_bill"},
    "fir_mlc": {"fir_mlc", "fir", "mlc"},
    "implant_invoice": {"implant_invoice", "implant_sticker"},
    "ambulance_receipt": {"ambulance_receipt", "ambulance_certificate"},
    "pre_authorization": {"pre_authorization", "pre_auth_form", "pre_auth_approval"},
    "other_medical_doc": {"other_medical_doc", "medical_report", "consent_form"},
}

CATEGORY_DISPLAY_NAMES = {
    "identity_proof": "Identity Proof (Aadhaar / ID)",
    "insurance_card": "Health Insurance Card / Policy",
    "claim_form": "Duly Filled Claim Form",
    "consultation_letter": "Doctor's Consultation / Prescription",
    "diagnostic_report": "Diagnostic / Lab Report",
    "hospital_bill": "Final Hospital Bill",
    "discharge_summary": "Discharge Summary",
    "payment_receipt": "Payment Receipt",
    "pharmacy_bill": "Pharmacy Bill",
    "fir_mlc": "Medico-Legal Certificate / FIR",
    "implant_invoice": "Implant Invoice & Sticker",
    "ambulance_receipt": "Ambulance Receipt",
    "pre_authorization": "Pre-Authorization Document",
    "other_medical_doc": "Supporting Medical Document",
}
'''

if "COMPATIBLE_CATEGORIES" not in code:
    code = code.replace("def safe_decimal(val, default=0.0) -> Decimal:", compatibility_code + "\ndef safe_decimal(val, default=0.0) -> Decimal:", 1)

# Fix lines 815-818: Do not unconditionally overwrite document.document_type
old_category_overwrite = """    detected_category = classification_result.get("document_type")
    if detected_category and detected_category != "unknown":
        document.document_type = detected_category"""

new_category_check = """    detected_category = classification_result.get("document_type")
    classification_conf = float(classification_result.get("confidence", 0.0) or 0.0)
    user_category = document.document_type or "Auto-Detect"
    
    category_match = True
    category_status = "Correct Document Type"
    category_mismatch_warning = None
    
    if user_category and user_category.lower() not in {"auto-detect", "unknown", "other_medical_doc", "document"}:
        norm_selected = normalize_category_name(user_category)
        norm_detected = normalize_category_name(detected_category)
        
        if norm_detected and norm_detected != "unknown" and classification_conf >= 0.60:
            is_compat = False
            for cat_key, cat_group in COMPATIBLE_CATEGORIES.items():
                if norm_selected == cat_key or norm_selected in cat_group:
                    if norm_detected == cat_key or norm_detected in cat_group:
                        is_compat = True
                        break
            if not is_compat:
                category_match = False
                category_status = "Incorrect Document Type"
                sel_display = CATEGORY_DISPLAY_NAMES.get(norm_selected, user_category)
                det_display = CATEGORY_DISPLAY_NAMES.get(norm_detected, detected_category)
                category_mismatch_warning = f"Incorrect Document Type – This file appears to be a {det_display}, not a {sel_display}."
                document.validation_status = "Incorrect Document Type"
            else:
                category_match = True
                category_status = "Correct Document Type"
        elif classification_conf < 0.50:
            category_match = None
            category_status = "Manual Review Required"
            category_mismatch_warning = "Document Type Could Not Be Confirmed. Please check whether you selected the correct category."
            document.validation_status = "Needs Review"
    else:
        if detected_category and detected_category != "unknown":
            document.document_type = detected_category

    classification_result["category_match"] = category_match
    classification_result["category_status"] = category_status
    if category_mismatch_warning:
        classification_result["mismatch_warning"] = category_mismatch_warning
        mismatches_list = validation_result.setdefault("mismatches", [])
        if category_mismatch_warning not in mismatches_list:
            mismatches_list.append(category_mismatch_warning)"""

assert old_category_overwrite in code, "old_category_overwrite not found"
code = code.replace(old_category_overwrite, new_category_check, 1)

with open("backend/app/documents.py", "w", encoding="utf-8") as f:
    f.write(code)

print("backend/app/documents.py classification logic updated!")
