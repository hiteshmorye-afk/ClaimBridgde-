"""
ClaimBridge Information Extraction

Extracts structured claim and clinical information from OCR text.
Adapts extraction according to the detected document type:
- Hospital Bills
- Discharge Summaries
- Prescriptions
- Lab Reports
- Medical Reports
- Insurance Policies

Preserves 100% backward compatibility with existing downstream consumers.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional


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
# COMMON ENTITY EXTRACTORS
# =========================================================

def extract_hospital_name(text: str) -> Optional[str]:
    """Extract hospital or clinic name."""
    lines = get_lines(text)
    for line in lines:
        normalized = line.strip()
        match = re.search(r"^(.+?\b(?:Hospital|Clinic|Medical\s+Center|Healthcare|Nursing\s+Home))\b", normalized, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

    for line in lines:
        if "hospital" in line.lower() or "clinic" in line.lower():
            return line.strip()

    return None


def extract_patient_name(text: str) -> Optional[str]:
    """Extract patient name from labelled fields."""
    normalized_text = normalize_text(text)
    patterns = [
        r"Patient\s+Name\s*[:\-]\s*([^\n]+)",
        r"Name\s+of\s+Patient\s*[:\-]\s*([^\n]+)",
        r"Patient\s*[:\-]\s*([^\n]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized_text, flags=re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            # Split off inline trailing fields if present on the same line
            val = re.split(r"\s+(?:Age|Gender|Sex|DOB|Bed|Room|IPD|OPD|MRN|UHID)\s*[:\-]", val, flags=re.IGNORECASE)[0].strip()
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
        r"(?:AMOUNT\s+DUE|AMOUNT\s+PAYABLE|TOTAL\s+CHARGES|TOTAL\s+AMOUNT|FINAL\s+AMOUNT|NET\s+AMOUNT)\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)",
        r"TOTAL\s*[:\-]\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)",
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

def extract_bill_details(text: str) -> Dict[str, Any]:
    """Extract specialized fields for Hospital Bills."""
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

    return {
        "invoice_number": invoice_no,
        "subtotal": subtotal,
        "tax": tax,
        "discount": discount,
        "itemized_charges": itemized,
    }


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


def extract_prescription_details(text: str) -> Dict[str, Any]:
    """Extract specialized fields for Prescriptions."""
    normalized_text = normalize_text(text)
    lines = get_lines(text)

    # Doctor
    doctor = None
    doc_match = re.search(r"(?:Dr\.?|Doctor)\s*[:\-]?\s*([^\n]+)", normalized_text, flags=re.IGNORECASE)
    if doc_match:
        doctor = re.split(r"\s+(?:MBBS|MD|Reg|Date|Rx)\s*[:\-]", doc_match.group(1).strip(), flags=re.IGNORECASE)[0].strip()

    # Prescription date
    presc_date = None
    date_match = re.search(r"(?:Date|Prescription\s+Date)\s*[:\-]\s*([^\n]+)", normalized_text, flags=re.IGNORECASE)
    if date_match:
        presc_date = normalize_date(date_match.group(1).strip())

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
        "prescription_date": presc_date,
        "medications": medications,
    }


def extract_lab_details(text: str) -> Dict[str, Any]:
    """Extract specialized fields for Laboratory Reports."""
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

    return {
        "test_results": tests,
        "abnormal_findings": abnormal,
    }


def extract_policy_details(text: str) -> Dict[str, Any]:
    """Extract specialized fields for Insurance Policy documents."""
    normalized_text = normalize_text(text)

    # Policy number
    policy_no = None
    p_match = re.search(r"Policy\s+(?:Number|No|#)\.?\s*[:\-]\s*([A-Za-z0-9\-#\[\]]+)", normalized_text, flags=re.IGNORECASE)
    if p_match:
        policy_no = p_match.group(1).strip()

    # Insurer name
    insurer = None
    ins_match = re.search(r"(?:Insurance\s+Company|Insurer|Provider|Insurance\s+Provider)\s*[:\-]\s*([A-Za-z\s.'’]+?)(?=\s+(?:Policy|Date|\n|$))", normalized_text, flags=re.IGNORECASE)
    if ins_match:
        insurer = ins_match.group(1).strip()

    # Sum insured
    sum_insured = None
    sum_match = re.search(r"(?:Sum\s+Insured|Coverage\s+Amount|Policy\s+Limit)\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)", normalized_text, flags=re.IGNORECASE)
    if sum_match:
        try:
            sum_insured = float(sum_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Deductible
    deductible = None
    ded_match = re.search(r"Deductible\s*[:\-]?\s*(?:Rs\.?|\$|INR)?\s*([\d,]+\.?\d*)", normalized_text, flags=re.IGNORECASE)
    if ded_match:
        try:
            deductible = float(ded_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Exclusions
    exclusions = []
    excl_pattern = re.compile(r"(?:Exclusion\s+\d+|Exclusion|Excluded)\s*[:\-]\s*([^\n]+)", flags=re.IGNORECASE)
    for m in excl_pattern.finditer(normalized_text):
        exclusions.append(m.group(1).strip())

    return {
        "policy_number": policy_no,
        "insurer_name": insurer,
        "sum_insured": sum_insured,
        "deductible": deductible,
        "exclusions": exclusions,
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
    doc_type = (document_type or "unknown").lower()
    details: Dict[str, Any] = {}

    if doc_type in {"hospital_bill", "bill", "invoice"}:
        details = extract_bill_details(normalized_text)
        core_result["document_type"] = "hospital_bill"

    elif doc_type in {"discharge_summary", "discharge"}:
        details = extract_discharge_details(normalized_text)
        core_result["document_type"] = "discharge_summary"
        # Propagate diagnosis if detected
        if details.get("diagnosis"):
            core_result["diagnosis"] = details["diagnosis"]
        if details.get("procedure"):
            core_result["procedure"] = details["procedure"]
        if details.get("doctor_name"):
            core_result["doctor_name"] = details["doctor_name"]

    elif doc_type in {"prescription", "rx"}:
        details = extract_prescription_details(normalized_text)
        core_result["document_type"] = "prescription"
        if details.get("doctor_name"):
            core_result["doctor_name"] = details["doctor_name"]
        core_result["medications"] = details.get("medications", [])

    elif doc_type in {"lab_report", "laboratory_report"}:
        details = extract_lab_details(normalized_text)
        core_result["document_type"] = "lab_report"
        core_result["test_results"] = details.get("test_results", [])
        core_result["abnormal_findings"] = details.get("abnormal_findings", [])

    elif doc_type in {"medical_report", "clinical_report"}:
        details = extract_discharge_details(normalized_text)
        core_result["document_type"] = "medical_report"
        if details.get("diagnosis"):
            core_result["diagnosis"] = details["diagnosis"]

    elif doc_type in {"insurance_policy", "policy"}:
        details = extract_policy_details(normalized_text)
        core_result["document_type"] = "insurance_policy"
        if details.get("policy_number"):
            core_result["policy_number"] = details["policy_number"]
        if details.get("sum_insured"):
            core_result["sum_insured"] = details["sum_insured"]

    else:
        # Default/unspecified: attempt to extract bill details if charges exist,
        # otherwise discharge details if diagnosis exists
        core_result["document_type"] = "hospital_bill" if core_result["total_charges"] else "medical_document"
        if core_result["total_charges"]:
            details = extract_bill_details(normalized_text)
        else:
            details = extract_discharge_details(normalized_text)

    # Attach specialized details dictionary
    core_result["document_data"] = details

    # Flatten common specialized fields if not already on core_result
    for k, v in details.items():
        if k not in core_result and v is not None:
            core_result[k] = v

    return core_result


if __name__ == "__main__":
    sample_bill = """
    Chong Hua Hospital
    TAX INVOICE
    Patient No. : 968945993
    Patient Name: Mrs. Tuhod
    Date admitted: MAY 16, 2019
    Date discharge: MAY 19, 2019
    Room Charges: 45,000.00
    Pharmacy Charges: 32,000.00
    TOTAL CHARGES: 184,000.00
    """

    res = extract_information(sample_bill, document_type="hospital_bill")
    print("\nHospital Bill Extraction:")
    for k, v in res.items():
        print(f"  {k}: {v}")