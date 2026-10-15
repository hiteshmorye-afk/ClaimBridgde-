"""
ClaimBridge Validation Engine

Validates structured information extracted from single documents
and reconciles multiple documents for cross-document consistency
across the 15-category document intake catalogue.
"""

from typing import Any, Dict, List, Optional


# =========================================================
# REQUIRED FIELDS CONFIGURATION
# =========================================================

# Default core required fields (retained for backward compatibility)
REQUIRED_FIELDS = [
    "patient_name",
    "external_id",
    "admission_date",
    "discharge_date",
    "total_charges",
]

# Category-specific required fields for all 15 document types + legacy aliases
CATEGORY_REQUIRED_FIELDS: Dict[str, List[str]] = {
    # Section A: Core Claim Documents
    "claim_form": [
        "patient_name",
        "admission_date",
        "discharge_date",
    ],
    "insurance_card": [
        "policy_number",
    ],
    "insurance_policy": [
        "policy_number",
        "sum_insured",
    ],
    "identity_proof": [
        "holder_name",
        "masked_id_number",
    ],
    "bank_proof": [
        "bank_name",
        "ifsc_code",
        "masked_account_number",
    ],

    # Section B: Medical & Hospitalisation Documents
    "discharge_summary": [
        "patient_name",
        "admission_date",
        "discharge_date",
        "diagnosis",
    ],
    "consultation_letter": [
        "doctor_name",
    ],
    "prescription": [
        "patient_name",
        "medications",
    ],
    "diagnostic_report": [
        "test_results",
    ],
    "lab_report": [
        "patient_name",
        "test_results",
    ],

    # Section C: Financial & Billing Documents
    "hospital_bill": [
        "patient_name",
        "admission_date",
        "discharge_date",
        "total_charges",
    ],
    "payment_receipt": [
        "amount_paid",
        "receipt_number",
    ],
    "pharmacy_bill": [
        "pharmacy_name",
        "total_amount",
    ],

    # Section D: Special Circumstances
    "fir_mlc": [
        "incident_summary",
    ],
    "implant_invoice": [
        "manufacturer",
        "lot_number",
    ],
    "ambulance_receipt": [
        "provider_name",
        "amount_paid",
    ],
    "pre_authorization": [
        "preauth_number",
        "approved_amount",
    ],

    # Section E: Other Supporting Documents
    "other_medical_doc": [
        "document_title",
    ],
    "medical_report": [
        "patient_name",
        "diagnosis",
    ],
}

DOCUMENT_DEPENDENT_FIELDS = [
    "case_number",
    "customer_number",
    "billing_date",
]

EXPECTED_DATE_FORMAT = "%d.%m.%Y"


# =========================================================
# DATE VALIDATION HELPERS
# =========================================================

def _validate_date_format(value: Any, field_name: str, mismatches: list):
    """
    Validate date format when a date value is present.
    Expected format: DD.MM.YYYY
    """
    if value is None or value == "":
        return

    if not isinstance(value, str):
        mismatches.append(f"{field_name} must be a string in DD.MM.YYYY format")
        return

    parts = value.split(".")
    if len(parts) != 3:
        mismatches.append(f"{field_name} has invalid date format: {value}")
        return

    day, month, year = parts
    if (
        len(day) != 2
        or len(month) != 2
        or len(year) != 4
        or not day.isdigit()
        or not month.isdigit()
        or not year.isdigit()
    ):
        mismatches.append(f"{field_name} has invalid date format: {value}")


def _date_to_tuple(value: Any) -> Optional[tuple]:
    """
    Convert DD.MM.YYYY into a comparable (year, month, day) tuple.
    Returns None when the value cannot be parsed.
    """
    if not isinstance(value, str):
        return None

    parts = value.split(".")
    if len(parts) != 3:
        return None

    try:
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        return year, month, day
    except ValueError:
        return None


# =========================================================
# SINGLE DOCUMENT VALIDATION
# =========================================================

def validate_extracted_information(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate structured information extracted from a claim document.
    Adapts required field checks to the document type while preserving
    backward compatibility with existing consumers.
    """
    missing_fields = []
    optional_missing_fields = []
    mismatches = []
    risk_indicators = []

    doc_type = extracted_data.get("document_type")
    required = CATEGORY_REQUIRED_FIELDS.get(doc_type, REQUIRED_FIELDS)

    # 1. Check core required fields
    for field in required:
        value = extracted_data.get(field)
        if value is None or value == "" or (isinstance(value, list) and len(value) == 0):
            missing_fields.append(field)

    # 2. Check document-dependent fields separately
    for field in DOCUMENT_DEPENDENT_FIELDS:
        value = extracted_data.get(field)
        if value is None or value == "":
            optional_missing_fields.append(field)

    # 3. Validate date formats
    date_fields = ["admission_date", "discharge_date", "billing_date", "receipt_date", "valid_from", "valid_thru"]
    for field in date_fields:
        _validate_date_format(extracted_data.get(field), field, mismatches)

    # 4. Validate admission and discharge date consistency
    admission_date = _date_to_tuple(extracted_data.get("admission_date"))
    discharge_date = _date_to_tuple(extracted_data.get("discharge_date"))
    billing_date = _date_to_tuple(extracted_data.get("billing_date"))

    if admission_date and discharge_date:
        if admission_date > discharge_date:
            mismatches.append("Admission date cannot be later than discharge date")
            risk_indicators.append("Invalid admission/discharge date sequence")

    # 5. Validate billing date when available
    if discharge_date and billing_date:
        if discharge_date > billing_date:
            mismatches.append("Billing date cannot be earlier than discharge date")
            risk_indicators.append("Billing date occurs before discharge date")

    # 6. Validate total charges
    total_charges = extracted_data.get("total_charges")
    if total_charges is not None and total_charges != "":
        try:
            amount = float(total_charges)
            if amount <= 0:
                mismatches.append("Total charges must be greater than zero")
                risk_indicators.append("Invalid total charges amount")
        except (TypeError, ValueError):
            mismatches.append("Total charges must be a valid numeric value")
            risk_indicators.append("Invalid total charges format")

    # 7. Validate arithmetic consistency for hospital bills
    arithmetic = extracted_data.get("arithmetic_validation")
    if arithmetic and isinstance(arithmetic, dict):
        if not arithmetic.get("is_valid", True):
            for disc in arithmetic.get("discrepancies", []):
                mismatches.append(disc)
            risk_indicators.append("Itemized billing charges do not match billed total amount")

    # 8. Validate external ID
    external_id = extracted_data.get("external_id")
    if external_id is not None and external_id != "":
        if not isinstance(external_id, str):
            mismatches.append("External ID must be stored as a string")

    # 9. Validate customer number only when present
    customer_number = extracted_data.get("customer_number")
    if customer_number is not None and customer_number != "":
        if not str(customer_number).isdigit():
            mismatches.append("Customer number must contain only digits")

    # 10. Determine verification status
    if mismatches:
        verification_status = "Needs Review"
    elif missing_fields:
        verification_status = "Incomplete"
    else:
        verification_status = "Validated"

    # 11. Calculate validation readiness score
    total_required = len(required)
    present_required = total_required - len(missing_fields)
    completeness_score = (present_required / total_required) * 100 if total_required > 0 else 100.0

    mismatch_penalty = min(len(mismatches) * 10, 40)
    readiness_score = max(0.0, completeness_score - mismatch_penalty)

    # 12. Informational indicators
    if optional_missing_fields and doc_type == "hospital_bill":
        risk_indicators.append(
            "Document-dependent fields not present: " + ", ".join(optional_missing_fields)
        )

    # 13. Verification summary
    if verification_status == "Validated":
        verification_summary = "All required claim fields are present and consistent."
    elif verification_status == "Incomplete":
        verification_summary = f"One or more required fields ({', '.join(missing_fields)}) are missing."
    else:
        verification_summary = "Validation inconsistencies were detected and the claim requires review."

    return {
        "verification_status": verification_status,
        "readiness_score": round(readiness_score, 2),
        "missing_fields": missing_fields,
        "optional_missing_fields": optional_missing_fields,
        "mismatches": mismatches,
        "risk_indicators": risk_indicators,
        "verification_summary": verification_summary,
    }


# =========================================================
# CROSS-DOCUMENT RECONCILIATION
# =========================================================

def _clean_person_name(name: Optional[str]) -> str:
    """Normalize a person's name for comparison."""
    if not name:
        return ""
    cleaned = name.lower()
    for prefix in ["mr.", "mrs.", "ms.", "dr.", "master", "baby"]:
        cleaned = cleaned.replace(prefix, "")
    cleaned = "".join(c for c in cleaned if c.isalnum() or c.isspace())
    return " ".join(cleaned.split())


def validate_cross_document_consistency(
    documents_extractions: List[Dict[str, Any]],
    claim_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Reconciles multiple extracted document records belonging to the same claim.
    Identifies:
    1. Patient name discrepancies across documents.
    2. Date discrepancies (admission/discharge dates).
    3. Financial discrepancies (bill total vs payment receipts vs policy limit).
    4. Missing essential claim documents according to claim context (Cashless,
       Reimbursement, Accident, Surgery, Ambulance).
    """
    mismatches: List[str] = []
    risk_indicators: List[str] = []
    missing_documents: List[str] = []

    if not documents_extractions:
        return {
            "cross_document_status": "No Documents",
            "mismatches": [],
            "risk_indicators": ["No documents available for cross-validation"],
            "missing_documents": ["hospital_bill", "discharge_summary"],
            "reconciliation_summary": "No documents uploaded for this claim.",
        }

    # Extract context settings
    ctx = claim_context or {}
    claim_type = ctx.get("claim_type", "reimbursement")
    is_accident = ctx.get("is_accident", False)
    has_implant = ctx.get("has_implant", False)
    has_ambulance = ctx.get("has_ambulance", False)
    entered_data = ctx.get("entered_claim_data") or {}

    # 1. Track present document categories
    detected_types = {
        d.get("document_type")
        for d in documents_extractions
        if d.get("document_type")
    }

    has_bill = any(t in {"hospital_bill", "bill"} for t in detected_types)
    has_discharge = any(t in {"discharge_summary", "discharge"} for t in detected_types)
    has_card = any(t in {"insurance_card", "insurance_policy", "policy"} for t in detected_types)
    has_form = any(t in {"claim_form"} for t in detected_types)
    has_identity = any(t in {"identity_proof"} for t in detected_types)
    has_bank = any(t in {"bank_proof"} for t in detected_types)
    has_receipts = any(t in {"payment_receipt"} for t in detected_types)
    has_fir = any(t in {"fir_mlc"} for t in detected_types)
    has_implant_doc = any(t in {"implant_invoice"} for t in detected_types)
    has_ambulance_doc = any(t in {"ambulance_receipt"} for t in detected_types)
    has_preauth = any(t in {"pre_authorization"} for t in detected_types)

    # Core requirements
    if not has_bill:
        missing_documents.append("hospital_bill")
        risk_indicators.append("Claim does not contain an itemized hospital bill")

    if not has_discharge:
        missing_documents.append("discharge_summary")
        risk_indicators.append("Claim contains hospital bill but lacks discharge summary")

    # Contextual requirements (evaluated when claim_context is explicitly provided)
    if claim_context is not None:
        if not has_form and "claim_form" not in missing_documents:
            missing_documents.append("claim_form")
        if not has_card and "insurance_card" not in missing_documents:
            missing_documents.append("insurance_card")
        if not has_identity and "identity_proof" not in missing_documents:
            missing_documents.append("identity_proof")

        if claim_type == "reimbursement":
            if not has_bank and "bank_proof" not in missing_documents:
                missing_documents.append("bank_proof")
                risk_indicators.append("Bank details proof missing for reimbursement payout")
            if not has_receipts and "payment_receipt" not in missing_documents:
                missing_documents.append("payment_receipt")
                risk_indicators.append("Payment receipts missing for reimbursement claim")
        elif claim_type == "cashless":
            if not has_preauth and "pre_authorization" not in missing_documents:
                missing_documents.append("pre_authorization")
                risk_indicators.append("Pre-authorization approval letter missing for cashless claim")

        if is_accident and not has_fir:
            missing_documents.append("fir_mlc")
            risk_indicators.append("Accident case lacks mandatory MLC / FIR certificate")

        if has_implant and not has_implant_doc:
            missing_documents.append("implant_invoice")
            risk_indicators.append("Surgical implant used but manufacturer invoice/sticker is missing")

        if has_ambulance and not has_ambulance_doc:
            missing_documents.append("ambulance_receipt")
            risk_indicators.append("Ambulance charges claimed without ambulance receipt")

    # 2. Cross-document patient name verification
    patient_names: Dict[str, List[str]] = {}
    for doc in documents_extractions:
        p_name = doc.get("patient_name") or doc.get("holder_name") or doc.get("member_name")
        doc_type = doc.get("document_type", "document")
        if p_name:
            norm_name = _clean_person_name(p_name)
            if norm_name:
                if norm_name not in patient_names:
                    patient_names[norm_name] = []
                patient_names[norm_name].append(f"{p_name} ({doc_type})")

    # Include entered patient name if available
    entered_patient = entered_data.get("patient_name")
    if entered_patient:
        norm_entered = _clean_person_name(entered_patient)
        if norm_entered:
            if norm_entered not in patient_names:
                patient_names[norm_entered] = []
            patient_names[norm_entered].append(f"{entered_patient} (Entered Record)")

    if len(patient_names) > 1:
        distinct_names = [items[0] for items in patient_names.values()]
        mismatches.append(
            f"Patient name discrepancy across documents: " + " vs ".join(distinct_names)
        )
        risk_indicators.append("Conflicting patient identities in claim package")

    # 3. Cross-document date consistency
    admission_dates: Dict[str, str] = {}
    discharge_dates: Dict[str, str] = {}

    for doc in documents_extractions:
        doc_type = doc.get("document_type", "document")
        adm = doc.get("admission_date")
        dis = doc.get("discharge_date")
        if adm:
            admission_dates[doc_type] = adm
        if dis:
            discharge_dates[doc_type] = dis

    if len(set(admission_dates.values())) > 1:
        details = ", ".join([f"{t}: {d}" for t, d in admission_dates.items()])
        mismatches.append(f"Conflicting admission dates across documents: {details}")

    if len(set(discharge_dates.values())) > 1:
        details = ", ".join([f"{t}: {d}" for t, d in discharge_dates.items()])
        mismatches.append(f"Conflicting discharge dates across documents: {details}")

    # 4. Cross-document financial reconciliation
    total_billed = 0.0
    total_receipts = 0.0
    policy_sum_insured: Optional[float] = None
    preauth_approved: Optional[float] = None

    for doc in documents_extractions:
        doc_type = doc.get("document_type", "")
        chg = doc.get("total_charges")
        if chg is not None:
            try:
                amt = float(chg)
                if doc_type in {"hospital_bill", "bill", "pharmacy_bill"}:
                    total_billed += amt
                elif doc_type == "payment_receipt":
                    total_receipts += amt
            except (ValueError, TypeError):
                pass

        # Check explicit receipt payment
        if doc.get("amount_paid") is not None and doc_type == "payment_receipt":
            try:
                amt_paid = float(doc["amount_paid"])
                if amt_paid not in [total_receipts]:
                    total_receipts = max(total_receipts, amt_paid)
            except (ValueError, TypeError):
                pass

        if doc.get("sum_insured") is not None:
            try:
                policy_sum_insured = float(doc["sum_insured"])
            except (ValueError, TypeError):
                pass

        if doc.get("approved_amount") is not None:
            try:
                preauth_approved = float(doc["approved_amount"])
            except (ValueError, TypeError):
                pass

    # Compare billed total vs policy sum insured
    if policy_sum_insured is not None and total_billed > policy_sum_insured:
        mismatches.append(
            f"Total billed charges (${total_billed:,.2f}) exceed policy sum insured (${policy_sum_insured:,.2f})"
        )
        risk_indicators.append("Claimed amount exceeds policy coverage limit")

    # Compare billed total vs pre-authorized amount
    if preauth_approved is not None and total_billed > preauth_approved:
        diff_auth = total_billed - preauth_approved
        mismatches.append(
            f"Total billed charges (${total_billed:,.2f}) exceed pre-authorized cashless limit "
            f"(${preauth_approved:,.2f}) by ${diff_auth:,.2f}"
        )
        risk_indicators.append("Billed amount exceeds authorized cashless cap")

    # Compare payment receipts vs billed amount for reimbursement claims
    if claim_type == "reimbursement" and has_receipts and has_bill:
        if total_receipts < total_billed:
            shortfall = total_billed - total_receipts
            if shortfall > 5.0:
                mismatches.append(
                    f"Receipt reconciliation shortfall: Total receipts submitted (${total_receipts:,.2f}) "
                    f"is less than billed amount (${total_billed:,.2f}). Unreconciled balance: ${shortfall:,.2f}"
                )
                risk_indicators.append("Payment receipts do not fully cover billed expenditure")

    # 5. Reconciliation status
    if mismatches:
        cross_status = "Discrepancy Detected"
        summary = (
            f"Cross-document reconciliation detected {len(mismatches)} contradiction(s). "
            "Claim requires human review."
        )
    elif missing_documents:
        cross_status = "Incomplete Package"
        summary = (
            "Cross-document consistency verified, but required documents are missing: "
            + ", ".join(missing_documents)
        )
    else:
        cross_status = "Consistent"
        summary = "All documents in the claim package are consistent and cross-reconciled."

    return {
        "cross_document_status": cross_status,
        "mismatches": mismatches,
        "risk_indicators": risk_indicators,
        "missing_documents": missing_documents,
        "reconciliation_summary": summary,
        "financial_summary": {
            "total_billed": round(total_billed, 2),
            "total_receipts": round(total_receipts, 2),
            "policy_sum_insured": round(policy_sum_insured, 2) if policy_sum_insured else None,
            "preauth_approved": round(preauth_approved, 2) if preauth_approved else None,
        },
    }