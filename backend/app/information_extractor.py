"""
ClaimBridge Information Extraction

Extracts structured claim information from OCR text.

The extractor is designed to handle variations commonly
found in hospital bills and claim documents.
"""

import re
from datetime import datetime
from typing import Any, Dict


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text: str) -> str:
    """Normalize OCR text while preserving line structure."""

    if not text:
        return ""

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Normalize spaces but preserve newlines.
    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    return text.strip()


def get_lines(text: str) -> list[str]:
    """Return cleaned non-empty OCR lines."""

    return [
        line.strip()
        for line in normalize_text(text).split("\n")
        if line.strip()
    ]


# =========================================================
# HOSPITAL NAME
# =========================================================

def extract_hospital_name(text: str) -> str | None:
    """
    Extract hospital name.

    Handles:
    - Hospital name followed by Hospital
    - Common OCR capitalization variations
    """

    lines = get_lines(text)

    for line in lines:

        normalized = line.strip()

        # Common explicit hospital-name pattern.
        match = re.search(
            r"^(.+?\bHospital)\b",
            normalized,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

    # Fallback for known hospital wording.
    for line in lines:

        if "hospital" in line.lower():
            return line.strip()

    return None


# =========================================================
# PATIENT NAME
# =========================================================

def extract_patient_name(text: str) -> str | None:
    """Extract patient name from the Patient Name field."""

    patterns = [
        r"Patient\s+Name\s*:\s*(.+)",
        r"Patient\s+Name\s*-\s*(.+)",
    ]

    normalized_text = normalize_text(text)

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        )

        if match:

            value = match.group(1).strip()

            if value:
                return value

    return None


# =========================================================
# PATIENT / EXTERNAL ID
# =========================================================

def extract_external_id(text: str) -> str | None:
    """
    Extract an external patient identifier.

    Supported examples:
    - External ID: X1234567890A
    - Patient No.: 968945993

    Patient number is used as the external identifier when
    an explicit external ID is not available.
    """

    normalized_text = normalize_text(text)

    # Explicit external ID.
    patterns = [
        r"External\s+ID\s*:\s*([A-Za-z0-9\-]+)",
        r"External\s+ID\s*-\s*([A-Za-z0-9\-]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

    # Hospital patient number.
    patterns = [
        r"Patient\s+No\.?\s*:\s*([A-Za-z0-9\-]+)",
        r"Patient\s+Number\s*:\s*([A-Za-z0-9\-]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

    return None


# =========================================================
# CASE NUMBER
# =========================================================

def extract_case_number(text: str) -> str | None:
    """Extract an explicitly labelled case number."""

    normalized_text = normalize_text(text)

    patterns = [
        r"Case\s+No\.?\s*:\s*([A-Za-z0-9\-]+)",
        r"Case\s+Number\s*:\s*([A-Za-z0-9\-]+)",
        r"Case\s*#\s*:\s*([A-Za-z0-9\-]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

    return None


# =========================================================
# CUSTOMER NUMBER
# =========================================================

def extract_customer_number(text: str) -> str | None:
    """Extract an explicitly labelled customer number."""

    normalized_text = normalize_text(text)

    patterns = [
        r"Customer\s+No\.?\s*:\s*([A-Za-z0-9\-]+)",
        r"Customer\s+Number\s*:\s*([A-Za-z0-9\-]+)",
        r"Customer\s*#\s*:\s*([A-Za-z0-9\-]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

    return None


# =========================================================
# DATE PARSING
# =========================================================

MONTHS = {
    "JAN": 1,
    "JANUARY": 1,
    "FEB": 2,
    "FEBRUARY": 2,
    "MAR": 3,
    "MARCH": 3,
    "APR": 4,
    "APRIL": 4,
    "MAY": 5,
    "JUN": 6,
    "JUNE": 6,
    "JUL": 7,
    "JULY": 7,
    "AUG": 8,
    "AUGUST": 8,
    "SEP": 9,
    "SEPT": 9,
    "SEPTEMBER": 9,
    "OCT": 10,
    "OCTOBER": 10,
    "NOV": 11,
    "NOVEMBER": 11,
    "DEC": 12,
    "DECEMBER": 12,
}


def normalize_date(
    date_text: str,
) -> str | None:
    """
    Convert supported date formats to DD.MM.YYYY.

    Examples:
    MAY 16, 2019 -> 16.05.2019
    16.05.2019   -> 16.05.2019
    """

    if not date_text:
        return None

    value = date_text.strip()

    # Numeric format.
    numeric_match = re.fullmatch(
        r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})",
        value,
    )

    if numeric_match:

        day = int(numeric_match.group(1))
        month = int(numeric_match.group(2))
        year = int(numeric_match.group(3))

        try:

            date_value = datetime(
                year,
                month,
                day,
            )

            return date_value.strftime(
                "%d.%m.%Y"
            )

        except ValueError:

            return None

    # Month-name format.
    month_match = re.fullmatch(
        r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})",
        value,
    )

    if month_match:

        month_name = month_match.group(1).upper()
        day = int(month_match.group(2))
        year = int(month_match.group(3))

        month = MONTHS.get(
            month_name
        )

        if month is None:
            return None

        try:

            date_value = datetime(
                year,
                month,
                day,
            )

            return date_value.strftime(
                "%d.%m.%Y"
            )

        except ValueError:

            return None

    return None


# =========================================================
# ADMISSION DATE
# =========================================================

def extract_admission_date(
    text: str,
) -> str | None:
    """Extract explicitly labelled admission date."""

    normalized_text = normalize_text(text)

    patterns = [
        r"Date\s+admitted\s*:\s*([A-Za-z0-9.,/\- ]+?)(?=\s+TIME\b|\n|$)",
        r"Admission\s+Date\s*:\s*([A-Za-z0-9.,/\- ]+?)(?=\s+TIME\b|\n|$)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        )

        if match:

            return normalize_date(
                match.group(1).strip()
            )

    return None


# =========================================================
# DISCHARGE DATE
# =========================================================

def extract_discharge_date(
    text: str,
) -> str | None:
    """Extract explicitly labelled discharge date."""

    normalized_text = normalize_text(text)

    patterns = [
        r"Date\s+discharge\s*:\s*([A-Za-z0-9.,/\- ]+?)(?=\s+TIME\b|\n|$)",
        r"Date\s+discharged\s*:\s*([A-Za-z0-9.,/\- ]+?)(?=\s+TIME\b|\n|$)",
        r"Discharge\s+Date\s*:\s*([A-Za-z0-9.,/\- ]+?)(?=\s+TIME\b|\n|$)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        )

        if match:

            return normalize_date(
                match.group(1).strip()
            )

    return None


# =========================================================
# BILLING DATE
# =========================================================

def extract_billing_date(
    text: str,
) -> str | None:
    """Extract an explicitly labelled billing date."""

    normalized_text = normalize_text(text)

    patterns = [
        r"Billing\s+Date\s*:\s*([A-Za-z0-9.,/\- ]+?)(?=\s+TIME\b|\n|$)",
        r"Bill\s+Date\s*:\s*([A-Za-z0-9.,/\- ]+?)(?=\s+TIME\b|\n|$)",
        r"Date\s+of\s+Billing\s*:\s*([A-Za-z0-9.,/\- ]+?)(?=\s+TIME\b|\n|$)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        )

        if match:

            return normalize_date(
                match.group(1).strip()
            )

    return None


# =========================================================
# TOTAL CHARGES
# =========================================================

def extract_total_charges(
    text: str,
) -> float | None:
    """
    Extract the final hospital bill amount.

    Supports:
    AMOUNT DUE - HOSPITAL BILL
    TOTAL CHARGES
    TOTAL AMOUNT
    """

    normalized_text = normalize_text(text)

    patterns = [
        r"AMOUNT\s+DUE\s*-\s*HOSPITAL\s+BILL\s*\n?\s*([\d,]+\.\d{2})",
        r"AMOUNT\s+DUE\s*[:\-]?\s*([\d,]+\.\d{2})",
        r"TOTAL\s+CHARGES\s*[:\-]?\s*([\d,]+\.\d{2})",
        r"TOTAL\s+AMOUNT\s*[:\-]?\s*([\d,]+\.\d{2})",
        r"TOTAL\s*[:\-]\s*([\d,]+\.\d{2})",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        )

        if match:

            value = match.group(1)

            value = value.replace(
                ",",
                "",
            )

            try:

                return float(value)

            except ValueError:

                return None

    return None


# =========================================================
# MAIN EXTRACTION FUNCTION
# =========================================================

def extract_information(
    text: str,
) -> Dict[str, Any]:
    """
    Extract structured information from OCR text.
    """

    normalized_text = normalize_text(
        text
    )

    return {
        "hospital_name": extract_hospital_name(
            normalized_text
        ),

        "patient_name": extract_patient_name(
            normalized_text
        ),

        "external_id": extract_external_id(
            normalized_text
        ),

        "case_number": extract_case_number(
            normalized_text
        ),

        "customer_number": extract_customer_number(
            normalized_text
        ),

        "admission_date": extract_admission_date(
            normalized_text
        ),

        "discharge_date": extract_discharge_date(
            normalized_text
        ),

        "billing_date": extract_billing_date(
            normalized_text
        ),

        "total_charges": extract_total_charges(
            normalized_text
        ),
    }


# =========================================================
# MODULE TEST
# =========================================================

if __name__ == "__main__":

    sample_text = """
    Chong Hua Hospital
    STATEMENT OF ACCOUNT
    Patient No. : 968945993
    Patient Name: Mrs. Tuhod
    Date admitted: MAY 16, 2019
    TIME: 7:00AM
    Date discharge: MAY 19, 2019
    TIME: 2:00PM
    AMOUNT DUE - HOSPITAL BILL
    184,000.00
    """

    result = extract_information(
        sample_text
    )

    print("\n" + "=" * 60)
    print("CLAIMBRIDGE INFORMATION EXTRACTION")
    print("=" * 60)

    for key, value in result.items():

        print(
            f"{key}: {value}"
        )