"""
ClaimBridge Information Extraction

Extracts structured claim and clinical information from OCR text.
Adapts extraction according to the 15 supported document types:
- Section A: Core (claim_form, insurance_card, identity_proof, bank_proof)
- Section B: Medical (discharge_summary, consultation_letter, diagnostic_report)
- Section C: Financial (hospital_bill, payment_receipt, pharmacy_bill)
- Section D: Special (fir_mlc, implant_invoice, ambulance_receipt, pre_authorization)
- Section E: Other (other_medical_doc)

Features:
- Arithmetic validation for itemized bills
- Sensitive data masking for KYC (Aadhaar, PAN, Passport) and Bank details
- Backward compatibility with existing downstream consumers
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from .document_classifier import normalize_category_name


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text: str) -> str:
    """Normalize OCR text while preserving line structure."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = text.replace("–", "-").replace("—", "-")

    # Normalize horizontal whitespace
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def get_lines(text: str) -> List[str]:
    """Return cleaned non-empty OCR lines."""
    return [
        line.strip()
        for line in normalize_text(text).split("\n")
        if line.strip()
    ]


# =========================================================
# DATE PARSING & NORMALIZATION
# =========================================================

MONTHS = {
    "JAN": 1, "JANUARY": 1,
    "FEB": 2, "FEBRUARY": 2,
    "MAR": 3, "MARCH": 3,
    "APR": 4, "APRIL": 4,
    "MAY": 5,
    "JUN": 6, "JUNE": 6,
    "JUL": 7, "JULY": 7,
    "AUG": 8, "AUGUST": 8,
    "SEP": 9, "SEPT": 9, "SEPTEMBER": 9,
    "OCT": 10, "OCTOBER": 10,
    "NOV": 11, "NOVEMBER": 11,
    "DEC": 12, "DECEMBER": 12,
}


def normalize_date(date_text: Optional[str]) -> Optional[str]:
    """
    Convert supported date formats to DD.MM.YYYY.
    Examples:
    MAY 16, 2019 -> 16.05.2019
    16.05.2019   -> 16.05.2019
    2026-07-01   -> 01.07.2026
    """
    if not date_text:
        return None

    value = date_text.strip()

    # ISO format YYYY-MM-DD
    iso_match = re.fullmatch(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", value)
    if iso_match:
        year, month, day = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        try:
            return datetime(year, month, day).strftime("%d.%m.%Y")
        except ValueError:
            return None

    # Numeric format DD.MM.YYYY or DD/MM/YYYY
    numeric_match = re.fullmatch(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", value)
    if numeric_match:
        day, month, year = int(numeric_match.group(1)), int(numeric_match.group(2)), int(numeric_match.group(3))
        try:
            return datetime(year, month, day).strftime("%d.%m.%Y")
        except ValueError:
            return None

    # Month-name format e.g. "MAY 16, 2019" or "16 MAY 2019"
    month_match1 = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", value)
    if month_match1:
        month_name = month_match1.group(1).upper()
        day, year = int(month_match1.group(2)), int(month_match1.group(3))
        month = MONTHS.get(month_name)
        if month:
            try:
                return datetime(year, month, day).strftime("%d.%m.%Y")
            except ValueError:
                return None

    month_match2 = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})", value)
    if month_match2:
        day = int(month_match2.group(1))
        month_name = month_match2.group(2).upper()
        year = int(month_match2.group(3))
        month = MONTHS.get(month_name)
        if month:
            try:
                return datetime(year, month, day).strftime("%d.%m.%Y")
            except ValueError:
                return None

    return None


# =========================================================
# SENSITIVE DATA MASKING HELPERS
# =========================================================

def mask_aadhaar(val: Optional[str]) -> Optional[str]:
    """Mask 12-digit Aadhaar number as XXXX-XXXX-1234."""
    if not val:
        return None
    digits = re.sub(r"\D", "", val)
    if len(digits) == 12:
        return f"XXXX-XXXX-{digits[-4:]}"
    if len(digits) >= 4:
        return f"XXXX-XXXX-{digits[-4:]}"
    return "XXXX-XXXX-XXXX"


def mask_pan(val: Optional[str]) -> Optional[str]:
    """Mask 10-character PAN as ABCDE****F."""
    if not val:
        return None
    cleaned = val.strip().upper()
    if len(cleaned) == 10:
        return f"{cleaned[:5]}****{cleaned[-1]}"
    if len(cleaned) > 5:
        return f"{cleaned[:5]}****"
    return "ABCDE****F"


def mask_bank_account(val: Optional[str]) -> Optional[str]:
    """Mask bank account number showing only last 4 digits."""
    if not val:
        return None
    digits = re.sub(r"\D", "", val)
    if len(digits) >= 4:
        return f"XXXXXX{digits[-4:]}"
    return "XXXXXX0000"


def mask_passport(val: Optional[str]) -> Optional[str]:
    """Mask passport number showing first 2 and last 2 characters."""
    if not val:
        return None
    cleaned = val.strip().upper()
    if len(cleaned) >= 6:
        return f"{cleaned[:2]}****{cleaned[-2:]}"
    return "XX****XX"


# =========================================================
# COMMON ENTITY EXTRACTORS
# =========================================================

def extract_hospital_name(text: str) -> Optional[str]:
    """Extract hospital or clinic name."""
    lines = get_lines(text)
    for line in lines[:15]:
        clean = line.strip()
        if not clean:
            continue
        if re.search(r"\b(?:Tax\s+Invoice|Bill|Discharge|Prescription|Receipt|Statement|Summary|Claim\s+Form)\b", clean, flags=re.IGNORECASE):
            continue
        if re.search(r"\b(?:Hospitals?|Clinics?|Medical\s+Centers?|Health\s*care|Nursing\s+Homes?|Infirmary)\b", clean, flags=re.IGNORECASE):
            clean_name = re.sub(r"^(?:Hospital\s+Name|Facility|Provider)\s*[:\-]\s*", "", clean, flags=re.IGNORECASE).strip()
            if clean_name and len(clean_name) >= 3:
                return clean_name

    for line in lines:
        clean = line.strip()
        if re.search(r"\b(?:Hospitals?|Clinics?)\b", clean, flags=re.IGNORECASE):
            clean_name = re.sub(r"^(?:Hospital\s+Name|Facility|Provider)\s*[:\-]\s*", "", clean, flags=re.IGNORECASE).strip()
            if clean_name and len(clean_name) >= 3:
                return clean_name

    return None


def extract_patient_name(text: str) -> Optional[str]:
    """Extract patient name from labelled fields."""
    normalized_text = normalize_text(text)
    patterns = [
        r"(?:Patient\s+Name|Name\s+of\s+Patient|Patient|Insured\s+Person|Member\s+Name)\s*[:\-]\s*([^\n]+)",
        r"(?:Claimant\s+Name|Name\s+of\s+Claimant)\s*[:\-]\s*([^\n]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized_text, flags=re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            val = re.split(r"\s+(?:Age|Gender|Sex|DOB|Bed|Room|IPD|OPD|MRN|UHID|Policy)\s*[:\-]", val, flags=re.IGNORECASE)[0].strip()
            if val and len(val) >= 2:
                return val

    return None


def extract_external_id(text: str) -> Optional[str]:
    """Extract external patient identifier or UHID/MRN/Patient No."""
    normalized_text = normalize_text(text)
    patterns = [
        r"External\s+ID\s*[:\-]\s*([A-Za-z0-9\-]+)",
        r"(?:UHID|MRN|IPD|OPD)\s*No\.?\s*[:\-]\s*([A-Za-z0-9\-]+)",
        r"Patient\s+(?:No|Number|ID)\.?\s*[:\-]\s*([A-Za-z0-9\-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def extract_case_number(text: str) -> Optional[str]:
    """Extract case number."""
    normalized_text = normalize_text(text)
    patterns = [
        r"Case\s+(?:No|Number|#)\.?\s*[:\-]\s*([A-Za-z0-9\-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def extract_customer_number(text: str) -> Optional[str]:
    """Extract customer number."""
    normalized_text = normalize_text(text)
    patterns = [
        r"Customer\s+(?:No|Number|#)\.?\s*[:\-]\s*([A-Za-z0-9\-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def extract_admission_date(text: str) -> Optional[str]:
    """Extract admission date."""
    normalized_text = normalize_text(text)
    patterns = [
        r"(?:Date\s+admitted|Admission\s+Date|Date\s+of\s+Admission|DOA)\s*[:\-]\s*([A-Za-z0-9.,/\- ]+?)(?=\s+(?:TIME|Time|Ward|Bed|Doctor)\b|\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text, flags=re.IGNORECASE)
        if match:
            res = normalize_date(match.group(1).strip())
            if res:
                return res

    return None


def extract_discharge_date(text: str) -> Optional[str]:
    """Extract discharge date."""
    normalized_text = normalize_text(text)
    patterns = [
        r"(?:Date\s+discharged?|Discharge\s+Date|Date\s+of\s+Discharge|DOD)\s*[:\-]\s*([A-Za-z0-9.,/\- ]+?)(?=\s+(?:TIME|Time|Condition|Doctor)\b|\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text, flags=re.IGNORECASE)
        if match:
            res = normalize_date(match.group(1).strip())
            if res:
                return res

    return None


def extract_billing_date(text: str) -> Optional[str]:
    """Extract billing date."""
    normalized_text = normalize_text(text)
    patterns = [
        r"(?:Billing\s+Date|Bill\s+Date|Date\s+of\s+Billing|Invoice\s+Date)\s*[:\-]\s*([A-Za-z0-9.,/\- ]+?)(?=\s+(?:TIME|Time)\b|\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text, flags=re.IGNORECASE)
        if match:
            res = normalize_date(match.group(1).strip())
            if res:
                return res

    return None


def extract_total_charges(text: str) -> Optional[float]:
    """Extract final bill or total charges amount."""
    normalized_text = normalize_text(text)
    patterns = [
        r"AMOUNT\s+DUE\s*-\s*HOSPITAL\s+BILL\s*\n?\s*([\d,]+\.?\d*)",
        r"(?:AMOUNT\s+DUE|AMOUNT\s+PAYABLE|TOTAL\s+CHARGES|TOTAL\s+AMOUNT|FINAL\s+AMOUNT|NET\s+AMOUNT|CLAIMED\s+AMOUNT)\s*[:\-]?\s*(?:Rs\.?|\$|INR|₱)?\s*([\d,]+\.?\d*)",
        r"TOTAL\s*[:\-]\s*(?:Rs\.?|\$|INR|₱)?\s*([\d,]+\.?\d*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text, flags=re.IGNORECASE)
        if match:
            val_str = match.group(1).replace(",", "").strip()
            try:
                val = float(val_str)
                if val > 0:
                    return val
            except ValueError:
                pass

    return None


# =========================================================
# DOCUMENT-SPECIFIC EXTRACTORS
# =========================================================

# --- 1. Duly Filled Claim Form ---
def extract_claim_form_details(text: str) -> Dict[str, Any]:
    """Extract fields from Duly Filled Claim Form (Part A / Part B)."""
    norm = normalize_text(text)

    # Claim Number
    claim_no = None
    m_claim = re.search(r"(?:Claim\s+(?:No|Number|ID|Reference))\s*[:\-]\s*([A-Za-z0-9\-]+)", norm, flags=re.IGNORECASE)
    if m_claim:
        claim_no = m_claim.group(1).strip()

    # Policy Number
    policy_no = None
    m_pol = re.search(r"(?:Policy\s+(?:No|Number|ID))\s*[:\-]\s*([A-Za-z0-9\-]+)", norm, flags=re.IGNORECASE)
    if m_pol:
        policy_no = m_pol.group(1).strip()

    # Hospitalization section
    hospital = extract_hospital_name(norm)
    patient = extract_patient_name(norm)
    doa = extract_admission_date(norm)
    dod = extract_discharge_date(norm)

    # Requested amount
    claimed_amount = None
    m_amt = re.search(r"(?:Total\s+Claimed\s+Amount|Claimed\s+Amount|Estimated\s+Expenses|Net\s+Claim\s+Amount)\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)", norm, flags=re.IGNORECASE)
    if m_amt:
        try:
            claimed_amount = float(m_amt.group(1).replace(",", ""))
        except ValueError:
            pass

    # Signature / declaration flag
    has_declaration = bool(re.search(r"\b(?:declare|declaration|hereby\s+confirm|signature\s+of\s+claimant|signature\s+of\s+insured)\b", norm, flags=re.IGNORECASE))

    return {
        "claim_number": claim_no,
        "policy_number": policy_no,
        "patient_name": patient,
        "hospital_name": hospital,
        "admission_date": doa,
        "discharge_date": dod,
        "claimed_amount": claimed_amount,
        "declaration_present": has_declaration,
    }


# --- 2. Health Insurance Card / Policy Schedule ---
def extract_card_details(text: str) -> Dict[str, Any]:
    """Extract fields from Health Insurance Card or Policy Schedule."""
    norm = normalize_text(text)

    # Policy Number
    policy_no = None
    p_match = re.search(r"(?:Policy\s+(?:Number|No|#)|Member\s+ID|Card\s+No\.?)\s*[:\-]\s*([A-Za-z0-9\-#\[\]]+)", norm, flags=re.IGNORECASE)
    if p_match:
        policy_no = p_match.group(1).strip()

    # Insurer / TPA Name
    insurer = None
    ins_match = re.search(r"(?:Insurance\s+Company|Insurer|Provider|Insurance\s+Provider|TPA)\s*[:\-]\s*([A-Za-z\s.'’]+?)(?=\s+(?:Policy|Date|Card|\n|$))", norm, flags=re.IGNORECASE)
    if ins_match:
        insurer = ins_match.group(1).strip()

    # Policyholder / Insured Member
    holder = extract_patient_name(norm)

    # Validity period
    valid_from = None
    valid_thru = None
    m_from = re.search(r"(?:Valid\s+From|Policy\s+Start|Inception\s+Date)\s*[:\-]\s*([A-Za-z0-9.,/\- ]+?)(?=\s+(?:Valid|Thru|To|\n|$))", norm, flags=re.IGNORECASE)
    if m_from:
        valid_from = normalize_date(m_from.group(1).strip())
    m_thru = re.search(r"(?:Valid\s+(?:Thru|Through|To|Upto)|Expiry\s+Date)\s*[:\-]\s*([A-Za-z0-9.,/\- ]+?)(?=\s+(?:Sum|Policy|\n|$))", norm, flags=re.IGNORECASE)
    if m_thru:
        valid_thru = normalize_date(m_thru.group(1).strip())

    # Sum insured
    sum_insured = None
    sum_match = re.search(r"(?:Sum\s+Insured|Coverage\s+Amount|Policy\s+Limit)\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)", norm, flags=re.IGNORECASE)
    if sum_match:
        try:
            sum_insured = float(sum_match.group(1).replace(",", ""))
        except ValueError:
            pass

    return {
        "policy_number": policy_no,
        "insurer_name": insurer,
        "member_name": holder,
        "valid_from": valid_from,
        "valid_thru": valid_thru,
        "sum_insured": sum_insured,
    }


# --- 3. KYC / Identity Proof ---
def extract_identity_proof_details(text: str) -> Dict[str, Any]:
    """Extract fields from KYC identity proofs with sensitive data masking."""
    norm = normalize_text(text)

    id_type = "Unknown ID"
    masked_number = None
    holder_name = None
    dob_or_yob = None

    # Check for Aadhaar
    if re.search(r"\b(?:Aadhaar|UIDAI|Unique\s+Identification)\b", norm, flags=re.IGNORECASE):
        id_type = "Aadhaar Card"
        # 12 digits
        m_aadh = re.search(r"\b(\d{4}\s*\d{4}\s*\d{4})\b", norm)
        if m_aadh:
            masked_number = mask_aadhaar(m_aadh.group(1))

    # Check for PAN
    elif re.search(r"\b(?:Permanent\s+Account\s+Number|PAN\s+Card|Income\s+Tax\s+Department)\b", norm, flags=re.IGNORECASE):
        id_type = "PAN Card"
        # 10 chars: 5 letters, 4 digits, 1 letter
        m_pan = re.search(r"\b([A-Z]{5}\d{4}[A-Z])\b", norm, flags=re.IGNORECASE)
        if m_pan:
            masked_number = mask_pan(m_pan.group(1))

    # Check for Passport
    elif re.search(r"\b(?:Passport|Republic\s+of\s+India\s+Passport)\b", norm, flags=re.IGNORECASE):
        id_type = "Passport"
        m_pass = re.search(r"\b([A-PR-WYa-pr-wy]\d{7})\b", norm)
        if m_pass:
            masked_number = mask_passport(m_pass.group(1))

    # Check for Voter ID
    elif re.search(r"\b(?:Election\s+Commission|Voter\s+ID|EPIC)\b", norm, flags=re.IGNORECASE):
        id_type = "Voter ID"
        m_voter = re.search(r"\b([A-Z]{3}\d{7})\b", norm, flags=re.IGNORECASE)
        if m_voter:
            masked_number = f"{m_voter.group(1)[:3]}****{m_voter.group(1)[-2:]}"

    # Extract name on ID
    m_name = re.search(r"(?:Name|To\s*[:\-]|Holder\s*[:\-])\s*([A-Za-z\s.'’]+?)(?=\s+(?:S/O|D/O|W/O|DOB|Father|Gender|\n|$))", norm, flags=re.IGNORECASE)
    if m_name:
        holder_name = m_name.group(1).strip()
    else:
        holder_name = extract_patient_name(norm)

    # DOB / YOB
    m_dob = re.search(r"(?:DOB|Date\s+of\s+Birth|Year\s+of\s+Birth|YOB)\s*[:\-]\s*([A-Za-z0-9.,/\- ]+?)(?=\s+(?:Gender|Male|Female|\n|$))", norm, flags=re.IGNORECASE)
    if m_dob:
        dob_or_yob = m_dob.group(1).strip()

    return {
        "identity_type": id_type,
        "masked_id_number": masked_number or "XXXX-XXXX-XXXX",
        "holder_name": holder_name,
        "dob_or_yob": dob_or_yob,
    }


# --- 4. Bank Details Proof ---
def extract_bank_proof_details(text: str) -> Dict[str, Any]:
    """Extract bank details with sensitive account masking."""
    norm = normalize_text(text)

    # IFSC Code (4 letters + 0 + 6 alphanumeric)
    ifsc = None
    m_ifsc = re.search(r"\bIFSC\s*(?:Code)?\s*[:\-]?\s*([A-Z]{4}0[A-Z0-9]{6})\b", norm, flags=re.IGNORECASE)
    if m_ifsc:
        ifsc = m_ifsc.group(1).upper().strip()
    else:
        m_ifsc_gen = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", norm)
        if m_ifsc_gen:
            ifsc = m_ifsc_gen.group(1).upper().strip()

    # Bank Name
    bank_name = None
    m_bank = re.search(r"(?:Bank\s+Name|Bank)\s*[:\-]\s*([A-Za-z\s.'’]+?)(?=\s+(?:Branch|IFSC|A/c|\n|$))", norm, flags=re.IGNORECASE)
    if m_bank:
        bank_name = m_bank.group(1).strip()
    else:
        for b in ["State Bank of India", "HDFC Bank", "ICICI Bank", "Axis Bank", "Punjab National Bank", "Bank of Baroda", "Kotak Mahindra Bank"]:
            if b.lower() in norm.lower():
                bank_name = b
                break

    # Account Number (masked)
    masked_account = None
    m_acc = re.search(r"(?:Account\s+(?:No|Number)|A/c\s+(?:No|Number)?)\s*[:\-]?\s*(\d{9,18})", norm, flags=re.IGNORECASE)
    if m_acc:
        masked_account = mask_bank_account(m_acc.group(1).strip())
    else:
        m_digits = re.search(r"\b(\d{9,18})\b", norm)
        if m_digits:
            masked_account = mask_bank_account(m_digits.group(1))

    # Account Holder
    account_holder = None
    m_holder = re.search(r"(?:Account\s+Holder|Pay\s+to|Name)\s*[:\-]\s*([A-Za-z\s.'’]+?)(?=\s+(?:A/c|Account|Rupees|\n|$))", norm, flags=re.IGNORECASE)
    if m_holder:
        account_holder = m_holder.group(1).strip()

    return {
        "bank_name": bank_name,
        "ifsc_code": ifsc,
        "masked_account_number": masked_account or "XXXXXX0000",
        "account_holder": account_holder,
    }


# --- 5. Hospital Bill with Arithmetic Validation ---
def extract_bill_details(text: str) -> Dict[str, Any]:
    """Extract specialized fields for Hospital Bills and perform arithmetic validation."""
    normalized_text = normalize_text(text)

    # Invoice / Bill Number
    invoice_no = None
    inv_match = re.search(r"(?:Invoice|Bill)\s+(?:No|Number|#)\.?\s*[:\-]\s*([A-Za-z0-9\-]+)", normalized_text, flags=re.IGNORECASE)
    if inv_match:
        invoice_no = inv_match.group(1).strip()

    # Subtotal
    subtotal = None
    sub_match = re.search(r"Subtotal\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)", normalized_text, flags=re.IGNORECASE)
    if sub_match:
        try:
            subtotal = float(sub_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Tax / GST
    tax = None
    tax_match = re.search(r"(?:Tax|GST|VAT)\s*(?:\(\d+%\))?\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)", normalized_text, flags=re.IGNORECASE)
    if tax_match:
        try:
            tax = float(tax_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Discount
    discount = None
    disc_match = re.search(r"Discount\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)", normalized_text, flags=re.IGNORECASE)
    if disc_match:
        try:
            discount = float(disc_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Itemized service charges
    itemized: Dict[str, float] = {}
    service_patterns = {
        "room_charges": r"(?:Room\s+(?:Charges|Rent|Accommodation)|Ward\s+Charges)\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)",
        "pharmacy_charges": r"(?:Pharmacy|Medicine|Medication)\s+(?:Charges)?\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)",
        "consultation_charges": r"(?:Doctor|Consultation|Professional)\s+(?:Fee|Charges)\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)",
        "investigation_charges": r"(?:Investigation|Diagnostic|Laboratory|Radiology)\s+(?:Charges|Fee)\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)",
        "ot_charges": r"(?:OT|Operating\s+(?:Room|Theater)|Surgical)\s+(?:Charges|Fee)\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)",
        "nursing_charges": r"Nursing\s+(?:Charges|Care)\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)",
    }

    for key, pattern in service_patterns.items():
        m = re.search(pattern, normalized_text, flags=re.IGNORECASE)
        if m:
            try:
                itemized[key] = float(m.group(1).replace(",", ""))
            except ValueError:
                pass

    # Total charges extracted from bill
    total_charges = extract_total_charges(normalized_text)

    # --- ARITHMETIC VALIDATION ---
    arithmetic_validation: Dict[str, Any] = {
        "is_valid": True,
        "itemized_sum": 0.0,
        "calculated_total": 0.0,
        "discrepancies": [],
    }

    if itemized:
        itemized_sum = round(sum(itemized.values()), 2)
        arithmetic_validation["itemized_sum"] = itemized_sum

        calc_subtotal = subtotal if subtotal is not None else itemized_sum
        calc_total = calc_subtotal + (tax or 0.0) - (discount or 0.0)
        calc_total = round(calc_total, 2)
        arithmetic_validation["calculated_total"] = calc_total

        # Compare calculated total against printed total
        if total_charges is not None:
            diff = round(abs(total_charges - calc_total), 2)
            if diff > 1.0:
                arithmetic_validation["is_valid"] = False
                msg = (
                    f"Bill total discrepancy: Printed total ({total_charges:,.2f}) does not match "
                    f"itemized sum + tax - discount ({calc_total:,.2f}). Variance: {diff:,.2f}."
                )
                arithmetic_validation["discrepancies"].append(msg)

    return {
        "invoice_number": invoice_no,
        "subtotal": subtotal,
        "tax": tax,
        "discount": discount,
        "itemized_charges": itemized,
        "arithmetic_validation": arithmetic_validation,
    }


# --- 6. Discharge Summary ---
def extract_discharge_details(text: str) -> Dict[str, Any]:
    """Extract specialized fields for Discharge Summaries."""
    normalized_text = normalize_text(text)

    # Doctor / Consultant
    doctor = None
    doc_match = re.search(r"(?:Doctor|Physician|Consultant|Dr\.?)\s*(?:Name)?\s*[:\-]\s*(?:Dr\.?\s*)?([^\n]+)", normalized_text, flags=re.IGNORECASE)
    if doc_match:
        doctor = re.split(r"\s+(?:Reg|Department|Date)\s*[:\-]", doc_match.group(1).strip(), flags=re.IGNORECASE)[0].strip()

    # Diagnosis
    diagnosis = None
    diag_match = re.search(r"(?:Discharge\s+Diagnosis|Final\s+Diagnosis|Provisional\s+Diagnosis|Diagnosis)\s*[:\-]\s*([^\n]+)", normalized_text, flags=re.IGNORECASE)
    if diag_match:
        diagnosis = re.split(r"\s+(?:ICD|Procedure|Treatment|Condition)\s*[:\-]", diag_match.group(1).strip(), flags=re.IGNORECASE)[0].strip()

    # Procedure
    procedure = None
    proc_match = re.search(r"(?:Procedure\s+Performed|Surgical\s+Procedure|Operation|Procedure)\s*[:\-]\s*([^\n]+)", normalized_text, flags=re.IGNORECASE)
    if proc_match:
        procedure = re.split(r"\s+(?:Date|Findings|Hospital|Advice)\s*[:\-]", proc_match.group(1).strip(), flags=re.IGNORECASE)[0].strip()

    # Hospital course
    hospital_course = None
    course_match = re.search(r"(?:Hospital\s+Course|Course\s+in\s+Hospital)\s*[:\-]\s*(.+?)(?=\s+(?:Condition|Advice|\n\n|$))", normalized_text, flags=re.IGNORECASE | re.DOTALL)
    if course_match:
        hospital_course = course_match.group(1).strip()[:300]

    # Condition at discharge
    condition = None
    cond_match = re.search(r"Condition\s+at\s+Discharge\s*[:\-]\s*(.+?)(?=\s+(?:Advice|Follow|\n|$))", normalized_text, flags=re.IGNORECASE)
    if cond_match:
        condition = cond_match.group(1).strip()

    # Advice on discharge
    advice = None
    adv_match = re.search(r"(?:Advice\s+on\s+Discharge|Discharge\s+Advice|Follow\s*-\s*up)\s*[:\-]\s*(.+?)(?=\s+(?:Dr\.|\n\n|$))", normalized_text, flags=re.IGNORECASE | re.DOTALL)
    if adv_match:
        advice = adv_match.group(1).strip()[:300]

    return {
        "doctor_name": doctor,
        "diagnosis": diagnosis,
        "procedure": procedure,
        "hospital_course": hospital_course,
        "condition_at_discharge": condition,
        "advice_on_discharge": advice,
    }


# --- 7. Doctor's Consultation Papers & Prescriptions ---
def extract_consultation_details(text: str) -> Dict[str, Any]:
    """Extract specialized fields for Consultation Papers & Prescriptions."""
    normalized_text = normalize_text(text)
    lines = get_lines(text)

    # Doctor
    doctor = None
    doc_match = re.search(r"(?:Dr\.?|Doctor|Consultant)\s*[:\-]?\s*([^\n]+)", normalized_text, flags=re.IGNORECASE)
    if doc_match:
        doctor = re.split(r"\s+(?:MBBS|MD|MS|Reg|Date|Rx)\s*[:\-]", doc_match.group(1).strip(), flags=re.IGNORECASE)[0].strip()

    # Clinic / OPD
    clinic = extract_hospital_name(normalized_text)

    # Date
    presc_date = None
    date_match = re.search(r"(?:Date|Prescription\s+Date|OPD\s+Date)\s*[:\-]\s*([^\n]+)", normalized_text, flags=re.IGNORECASE)
    if date_match:
        presc_date = normalize_date(date_match.group(1).strip())

    # Symptoms / Complaints
    symptoms = None
    sym_match = re.search(r"(?:Chief\s+Complaints?|Symptoms?|History)\s*[:\-]\s*(.+?)(?=\s+(?:O/E|Examination|Rx|Diagnosis|\n|$))", normalized_text, flags=re.IGNORECASE)
    if sym_match:
        symptoms = sym_match.group(1).strip()

    # Medications
    medications: List[Dict[str, str]] = []
    med_pattern = re.compile(
        r"(?:Tab(?:let)?|Cap(?:sule)?|Syp(?:rup)?|Inj(?:ection)?)\.?\s+([A-Za-z0-9\-\s]+?)(?:\s+(\d+\s*(?:mg|ml|gm)))?(?:\s+([0-1]-[0-1]-[0-1]|once|twice|thrice|daily|od|bd|tds|sos))?(?:\s+for\s+(\d+\s+(?:days|weeks|months)))?",
        flags=re.IGNORECASE,
    )

    for line in lines:
        for match in med_pattern.finditer(line):
            name = match.group(1).strip()
            dosage = match.group(2).strip() if match.group(2) else ""
            freq = match.group(3).strip() if match.group(3) else ""
            dur = match.group(4).strip() if match.group(4) else ""
            medications.append({
                "name": name,
                "dosage": dosage,
                "frequency": freq,
                "duration": dur,
                "raw": match.group(0),
            })

    return {
        "doctor_name": doctor,
        "clinic_name": clinic,
        "prescription_date": presc_date,
        "symptoms": symptoms,
        "medications": medications,
    }


def extract_prescription_details(text: str) -> Dict[str, Any]:
    """Preserve backward compatibility for prescription details."""
    return extract_consultation_details(text)


# --- 8. Investigation / Diagnostic Reports ---
def extract_diagnostic_report_details(text: str) -> Dict[str, Any]:
    """Extract specialized fields for Diagnostic Reports (Lab, Pathology, Radiology)."""
    lines = get_lines(text)
    tests: List[Dict[str, Any]] = []
    abnormal: List[str] = []

    # Common lab pattern: Test Name | Result | Unit | Reference Range
    test_pattern = re.compile(
        r"([A-Za-z\s]+?)\s*[:\-]\s*([\d.]+|Positive|Negative|Reactive|Non-reactive)\s*([a-zA-Z/%μ]+)?(?:\s+(?:Ref(?:erence)?\s*(?:Range|Interval)?[:\-]?\s*([\d.\s\-–]+)))?",
        flags=re.IGNORECASE,
    )

    for line in lines:
        match = test_pattern.search(line)
        if match:
            test_name = match.group(1).strip()
            result_val = match.group(2).strip()
            unit = match.group(3).strip() if match.group(3) else ""
            ref = match.group(4).strip() if match.group(4) else ""

            is_abnormal = False
            if "high" in line.lower() or "abnormal" in line.lower() or "*" in line:
                is_abnormal = True
                abnormal.append(f"{test_name}: {result_val} (Flagged Abnormal)")

            if len(test_name) > 2 and test_name.lower() not in {"patient", "age", "date", "dr", "doctor"}:
                tests.append({
                    "test_name": test_name,
                    "result": result_val,
                    "unit": unit,
                    "reference_range": ref,
                    "is_abnormal": is_abnormal,
                })

    # Radiology impressions
    impression = None
    m_imp = re.search(r"(?:Impression|Findings|Conclusion)\s*[:\-]\s*(.+?)(?=\s+(?:Signature|Radiologist|\n\n|$))", normalize_text(text), flags=re.IGNORECASE | re.DOTALL)
    if m_imp:
        impression = m_imp.group(1).strip()[:300]

    return {
        "test_results": tests,
        "abnormal_findings": abnormal,
        "radiology_impression": impression,
    }


def extract_lab_details(text: str) -> Dict[str, Any]:
    """Preserve backward compatibility for lab report details."""
    return extract_diagnostic_report_details(text)


# --- 9. Payment Receipts ---
def extract_payment_receipt_details(text: str) -> Dict[str, Any]:
    """Extract fields from Payment Receipts & Advance Vouchers."""
    norm = normalize_text(text)

    # Receipt Number
    receipt_no = None
    m_rec = re.search(r"(?:Receipt\s+(?:No|Number|#)|Voucher\s+No\.?)\s*[:\-]\s*([A-Za-z0-9\-]+)", norm, flags=re.IGNORECASE)
    if m_rec:
        receipt_no = m_rec.group(1).strip()

    # Payment Date
    receipt_date = None
    m_date = re.search(r"(?:Date|Payment\s+Date|Receipt\s+Date)\s*[:\-]\s*([A-Za-z0-9.,/\- ]+?)(?=\s+(?:Time|Mode|Amount|\n|$))", norm, flags=re.IGNORECASE)
    if m_date:
        receipt_date = normalize_date(m_date.group(1).strip())

    # Amount Paid
    amount_paid = None
    m_amt = re.search(r"(?:Amount\s+Paid|Received\s+Amount|Sum\s+of\s+Rupees|Amount)\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)", norm, flags=re.IGNORECASE)
    if m_amt:
        try:
            amount_paid = float(m_amt.group(1).replace(",", ""))
        except ValueError:
            pass

    # Payment Mode
    mode = "Cash"
    if re.search(r"\bUPI\b", norm, flags=re.IGNORECASE):
        mode = "UPI"
    elif re.search(r"\b(?:NEFT|RTGS|IMPS|Bank\s+Transfer)\b", norm, flags=re.IGNORECASE):
        mode = "Bank Transfer"
    elif re.search(r"\b(?:Credit\s+Card|Debit\s+Card|Card)\b", norm, flags=re.IGNORECASE):
        mode = "Card"
    elif re.search(r"\bCheque\b", norm, flags=re.IGNORECASE):
        mode = "Cheque"

    # Transaction reference
    ref_no = None
    m_ref = re.search(r"(?:Txn\s+ID|Transaction\s+ID|UPI\s+Ref|Cheque\s+No\.?|UTR\s+No\.?)\s*[:\-]\s*([A-Za-z0-9\-]+)", norm, flags=re.IGNORECASE)
    if m_ref:
        ref_no = m_ref.group(1).strip()

    return {
        "receipt_number": receipt_no,
        "receipt_date": receipt_date,
        "amount_paid": amount_paid,
        "payment_mode": mode,
        "reference_number": ref_no,
    }


# --- 10. Pharmacy Bills ---
def extract_pharmacy_bill_details(text: str) -> Dict[str, Any]:
    """Extract fields from Retail Pharmacy Bills."""
    norm = normalize_text(text)
    lines = get_lines(text)

    # Pharmacy name
    pharmacy = None
    for line in lines[:8]:
        if re.search(r"\b(?:Pharmacy|Chemist|Druggist|Medical\s+Store)\b", line, flags=re.IGNORECASE):
            pharmacy = line.strip()
            break

    # Bill number
    bill_no = None
    m_bill = re.search(r"(?:Bill|Invoice|Memo)\s+(?:No|Number|#)\.?\s*[:\-]\s*([A-Za-z0-9\-]+)", norm, flags=re.IGNORECASE)
    if m_bill:
        bill_no = m_bill.group(1).strip()

    # Date
    bill_date = None
    m_date = re.search(r"(?:Date|Bill\s+Date)\s*[:\-]\s*([A-Za-z0-9.,/\- ]+?)(?=\s+(?:Time|\n|$))", norm, flags=re.IGNORECASE)
    if m_date:
        bill_date = normalize_date(m_date.group(1).strip())

    # Total amount
    total_amt = None
    m_amt = re.search(r"(?:Total\s+Amount|Net\s+Amount|Amount\s+Payable|Grand\s+Total)\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)", norm, flags=re.IGNORECASE)
    if m_amt:
        try:
            total_amt = float(m_amt.group(1).replace(",", ""))
        except ValueError:
            pass

    return {
        "pharmacy_name": pharmacy,
        "bill_number": bill_no,
        "bill_date": bill_date,
        "total_amount": total_amt,
    }


# --- 11. Medico-Legal Certificate (MLC) / FIR ---
def extract_fir_mlc_details(text: str) -> Dict[str, Any]:
    """Extract fields from FIR or MLC reports."""
    norm = normalize_text(text)

    fir_no = None
    m_fir = re.search(r"FIR\s+(?:No|Number|#)\.?\s*[:\-]\s*([A-Za-z0-9/\-]+)", norm, flags=re.IGNORECASE)
    if m_fir:
        fir_no = m_fir.group(1).strip()

    mlc_no = None
    m_mlc = re.search(r"MLC\s+(?:No|Number|#)\.?\s*[:\-]\s*([A-Za-z0-9/\-]+)", norm, flags=re.IGNORECASE)
    if m_mlc:
        mlc_no = m_mlc.group(1).strip()

    police_station = None
    m_ps = re.search(r"Police\s+Station\s*[:\-]\s*([A-Za-z\s]+?)(?=\s+(?:District|Date|\n|$))", norm, flags=re.IGNORECASE)
    if m_ps:
        police_station = m_ps.group(1).strip()

    # Alcohol or substance influence check
    alcohol_detected = False
    if re.search(r"\b(?:smell\s+of\s+alcohol|under\s+the\s+influence\s+of\s+alcohol|breath\s+alcohol\s+positive|intoxicated)\b", norm, flags=re.IGNORECASE):
        alcohol_detected = True

    incident_summary = None
    m_inc = re.search(r"(?:History\s+of\s+Incident|Brief\s+Facts|Occurrence|Accident\s+Details)\s*[:\-]\s*(.+?)(?=\s+(?:Doctor|Signature|\n\n|$))", norm, flags=re.IGNORECASE | re.DOTALL)
    if m_inc:
        incident_summary = m_inc.group(1).strip()[:300]

    return {
        "fir_number": fir_no,
        "mlc_number": mlc_no,
        "police_station": police_station,
        "alcohol_detected": alcohol_detected,
        "incident_summary": incident_summary,
    }


# --- 12. Implant Invoice & Sticker ---
def extract_implant_invoice_details(text: str) -> Dict[str, Any]:
    """Extract fields from Implant Invoice or Sticker Outer Pouch."""
    norm = normalize_text(text)

    manufacturer = None
    m_mfg = re.search(r"(?:Manufacturer|Mfg\s+By|Company)\s*[:\-]\s*([A-Za-z\s.'’]+?)(?=\s+(?:Model|Lot|Batch|\n|$))", norm, flags=re.IGNORECASE)
    if m_mfg:
        manufacturer = m_mfg.group(1).strip()

    brand_name = None
    m_brand = re.search(r"(?:Brand\s+Name|Product\s+Name|Device|Implant\s+Name)\s*[:\-]\s*([A-Za-z0-9\s\-]+?)(?=\s+(?:Size|Lot|Serial|\n|$))", norm, flags=re.IGNORECASE)
    if m_brand:
        brand_name = m_brand.group(1).strip()

    lot_no = None
    m_lot = re.search(r"(?:Lot|Batch)\s+(?:No|Number|#)\.?\s*[:\-]\s*([A-Za-z0-9\-]+)", norm, flags=re.IGNORECASE)
    if m_lot:
        lot_no = m_lot.group(1).strip()

    serial_no = None
    m_ser = re.search(r"(?:Serial|SN)\s+(?:No|Number|#)\.?\s*[:\-]\s*([A-Za-z0-9\-]+)", norm, flags=re.IGNORECASE)
    if m_ser:
        serial_no = m_ser.group(1).strip()

    price = None
    m_price = re.search(r"(?:Price|Cost|Amount|MRP)\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)", norm, flags=re.IGNORECASE)
    if m_price:
        try:
            price = float(m_price.group(1).replace(",", ""))
        except ValueError:
            pass

    return {
        "manufacturer": manufacturer,
        "brand_name": brand_name,
        "lot_number": lot_no,
        "serial_number": serial_no,
        "implant_price": price,
    }


# --- 13. Ambulance Receipt / Certificate ---
def extract_ambulance_receipt_details(text: str) -> Dict[str, Any]:
    """Extract fields from Ambulance Receipt / Certificate."""
    norm = normalize_text(text)

    provider = None
    m_prov = re.search(r"(?:Ambulance\s+Service|Provider|Service\s+Name)\s*[:\-]\s*([A-Za-z\s.'’]+?)(?=\s+(?:Vehicle|Date|\n|$))", norm, flags=re.IGNORECASE)
    if m_prov:
        provider = m_prov.group(1).strip()

    veh_no = None
    m_veh = re.search(r"(?:Vehicle\s+No\.?|Ambulance\s+No\.?|Reg\s+No\.?)\s*[:\-]\s*([A-Za-z0-9\-]+)", norm, flags=re.IGNORECASE)
    if m_veh:
        veh_no = m_veh.group(1).strip()

    from_loc = None
    m_from = re.search(r"From\s*[:\-]\s*([A-Za-z0-9\s,]+?)(?=\s+(?:To|Distance|\n|$))", norm, flags=re.IGNORECASE)
    if m_from:
        from_loc = m_from.group(1).strip()

    to_loc = None
    m_to = re.search(r"To\s*[:\-]\s*([A-Za-z0-9\s,]+?)(?=\s+(?:Distance|Amount|\n|$))", norm, flags=re.IGNORECASE)
    if m_to:
        to_loc = m_to.group(1).strip()

    amount = None
    m_amt = re.search(r"(?:Amount\s+Paid|Total\s+Charges|Total|Fare)\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)", norm, flags=re.IGNORECASE)
    if m_amt:
        try:
            amount = float(m_amt.group(1).replace(",", ""))
        except ValueError:
            pass

    return {
        "provider_name": provider,
        "vehicle_number": veh_no,
        "from_location": from_loc,
        "to_location": to_loc,
        "amount_paid": amount,
    }


# --- 14. Pre-Authorization Approval Letter ---
def extract_preauth_details(text: str) -> Dict[str, Any]:
    """Extract fields from Pre-Authorization Approval Letter."""
    norm = normalize_text(text)

    preauth_no = None
    m_no = re.search(r"(?:Pre-?auth\s+(?:No|Number|ID|Ref)|Authorization\s+No\.?)\s*[:\-]\s*([A-Za-z0-9\-]+)", norm, flags=re.IGNORECASE)
    if m_no:
        preauth_no = m_no.group(1).strip()

    approved_amt = None
    m_amt = re.search(r"(?:Approved\s+Amount|Sanctioned\s+Amount|Authorized\s+Amount)\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)", norm, flags=re.IGNORECASE)
    if m_amt:
        try:
            approved_amt = float(m_amt.group(1).replace(",", ""))
        except ValueError:
            pass

    status = "Approved"
    if re.search(r"\b(?:Denied|Rejected|Repudiated)\b", norm, flags=re.IGNORECASE):
        status = "Denied"
    elif re.search(r"\b(?:Query|Information\s+Awaited|Additional\s+Requirement)\b", norm, flags=re.IGNORECASE):
        status = "Query Raised"

    return {
        "preauth_number": preauth_no,
        "approved_amount": approved_amt,
        "approval_status": status,
    }


# --- 15. Other Supporting Documents ---
def extract_other_doc_details(text: str) -> Dict[str, Any]:
    """Extract fields from Other Supporting Documents."""
    norm = normalize_text(text)

    doc_title = None
    lines = get_lines(norm)
    if lines:
        doc_title = lines[0][:80]

    return {
        "document_title": doc_title,
    }


# =========================================================
# MAIN EXTRACTOR ENTRYPOINT
# =========================================================

def extract_information(
    text: str,
    document_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract structured claim and clinical information from OCR text.
    Adapts extraction based on document_type while preserving full
    backward compatibility with existing pipeline consumers.
    """
    normalized_text = normalize_text(text)
    canonical_type = normalize_category_name(document_type)

    # 1. Core fields present across multiple medical document types
    core_result = {
        "hospital_name": extract_hospital_name(normalized_text),
        "patient_name": extract_patient_name(normalized_text),
        "external_id": extract_external_id(normalized_text),
        "case_number": extract_case_number(normalized_text),
        "customer_number": extract_customer_number(normalized_text),
        "admission_date": extract_admission_date(normalized_text),
        "discharge_date": extract_discharge_date(normalized_text),
        "billing_date": extract_billing_date(normalized_text),
        "total_charges": extract_total_charges(normalized_text),
    }

    # 2. Document-specific structured details
    details: Dict[str, Any] = {}

    if canonical_type == "claim_form":
        details = extract_claim_form_details(normalized_text)
        core_result["document_type"] = "claim_form"
        if details.get("policy_number"):
            core_result["policy_number"] = details["policy_number"]
        if details.get("claimed_amount"):
            core_result["total_charges"] = details["claimed_amount"]

    elif canonical_type == "insurance_card":
        details = extract_card_details(normalized_text)
        core_result["document_type"] = "insurance_card"
        if details.get("policy_number"):
            core_result["policy_number"] = details["policy_number"]
        if details.get("sum_insured"):
            core_result["sum_insured"] = details["sum_insured"]

    elif canonical_type == "identity_proof":
        details = extract_identity_proof_details(normalized_text)
        core_result["document_type"] = "identity_proof"

    elif canonical_type == "bank_proof":
        details = extract_bank_proof_details(normalized_text)
        core_result["document_type"] = "bank_proof"

    elif canonical_type == "discharge_summary":
        details = extract_discharge_details(normalized_text)
        core_result["document_type"] = "discharge_summary"
        if details.get("diagnosis"):
            core_result["diagnosis"] = details["diagnosis"]
        if details.get("procedure"):
            core_result["procedure"] = details["procedure"]
        if details.get("doctor_name"):
            core_result["doctor_name"] = details["doctor_name"]

    elif canonical_type == "consultation_letter":
        details = extract_consultation_details(normalized_text)
        core_result["document_type"] = "consultation_letter"
        if details.get("doctor_name"):
            core_result["doctor_name"] = details["doctor_name"]
        core_result["medications"] = details.get("medications", [])

    elif canonical_type == "diagnostic_report":
        details = extract_diagnostic_report_details(normalized_text)
        core_result["document_type"] = "diagnostic_report"
        core_result["test_results"] = details.get("test_results", [])
        core_result["abnormal_findings"] = details.get("abnormal_findings", [])

    elif canonical_type == "hospital_bill":
        details = extract_bill_details(normalized_text)
        core_result["document_type"] = "hospital_bill"

    elif canonical_type == "payment_receipt":
        details = extract_payment_receipt_details(normalized_text)
        core_result["document_type"] = "payment_receipt"
        if details.get("amount_paid"):
            core_result["total_charges"] = details["amount_paid"]

    elif canonical_type == "pharmacy_bill":
        details = extract_pharmacy_bill_details(normalized_text)
        core_result["document_type"] = "pharmacy_bill"
        if details.get("total_amount"):
            core_result["total_charges"] = details["total_amount"]

    elif canonical_type == "fir_mlc":
        details = extract_fir_mlc_details(normalized_text)
        core_result["document_type"] = "fir_mlc"

    elif canonical_type == "implant_invoice":
        details = extract_implant_invoice_details(normalized_text)
        core_result["document_type"] = "implant_invoice"
        if details.get("implant_price"):
            core_result["total_charges"] = details["implant_price"]

    elif canonical_type == "ambulance_receipt":
        details = extract_ambulance_receipt_details(normalized_text)
        core_result["document_type"] = "ambulance_receipt"
        if details.get("amount_paid"):
            core_result["total_charges"] = details["amount_paid"]

    elif canonical_type == "pre_authorization":
        details = extract_preauth_details(normalized_text)
        core_result["document_type"] = "pre_authorization"
        if details.get("approved_amount"):
            core_result["approved_amount"] = details["approved_amount"]

    elif canonical_type == "other_medical_doc":
        details = extract_other_doc_details(normalized_text)
        core_result["document_type"] = "other_medical_doc"

    else:
        # Default/unspecified
        if core_result["total_charges"]:
            core_result["document_type"] = "hospital_bill"
            details = extract_bill_details(normalized_text)
        else:
            core_result["document_type"] = "discharge_summary"
            details = extract_discharge_details(normalized_text)

    # Attach specialized details dictionary
    core_result["document_data"] = details

    # Flatten specialized fields to core_result if missing
    for k, v in details.items():
        if k not in core_result and v is not None:
            core_result[k] = v

    return core_result