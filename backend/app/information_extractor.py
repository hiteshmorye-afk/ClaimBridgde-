import re
from datetime import datetime


def extract_information(text: str):
    """
    Extract structured information from OCR text.

    Handles:
    - Same-line OCR fields
    - Next-line OCR fields
    - OCR reading-order issues
    - Date consistency
    - Hospital bill information
    """

    if not text or not text.strip():
        return {}

    # -------------------------------------------------
    # 1. NORMALIZE OCR TEXT
    # -------------------------------------------------

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)

    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip()
    ]

    # -------------------------------------------------
    # 2. RESULT STRUCTURE
    # -------------------------------------------------

    result = {
        "hospital_name": None,
        "patient_name": None,
        "external_id": None,
        "case_number": None,
        "customer_number": None,
        "admission_date": None,
        "discharge_date": None,
        "billing_date": None,
        "total_charges": None,
    }

    # -------------------------------------------------
    # 3. HOSPITAL NAME
    # -------------------------------------------------

    hospital_patterns = [
        "KK Women's and Children's Hospital",
        "KK Women's & Children's Hospital",
        "Children's Hospital",
    ]

    for hospital in hospital_patterns:
        if hospital.lower() in text.lower():
            result["hospital_name"] = hospital
            break

    # -------------------------------------------------
    # 4. PATIENT NAME
    # -------------------------------------------------

    patient_match = re.search(
        r"Patient\s*:?\s*([A-Za-z][A-Za-z .'-]+)",
        text,
        re.IGNORECASE
    )

    if patient_match:
        result["patient_name"] = patient_match.group(1).strip()

    # -------------------------------------------------
    # 5. EXTERNAL ID / NRIC
    #
    # Example:
    # X0724956604F
    # -------------------------------------------------

    external_match = re.search(
        r"\bX\d{10}[A-Z]\b",
        text,
        re.IGNORECASE
    )

    if external_match:
        result["external_id"] = external_match.group(0).upper()

    # -------------------------------------------------
    # 6. CUSTOMER NUMBER
    #
    # Example:
    # 76100506511
    # -------------------------------------------------

    customer_match = re.search(
        r"\b\d{11}\b",
        text
    )

    if customer_match:
        result["customer_number"] = customer_match.group(0)

    # -------------------------------------------------
    # 7. CASE NUMBER
    #
    # Example:
    # 3024956604
    # -------------------------------------------------

    case_numbers = re.findall(
        r"\b\d{10}\b",
        text
    )

    if case_numbers:
        result["case_number"] = case_numbers[0]

    # -------------------------------------------------
    # 8. FIND ALL DATES
    # -------------------------------------------------

    date_matches = re.findall(
        r"\b\d{2}\.\d{2}\.\d{4}\b",
        text
    )

    # Remove duplicates while preserving order
    unique_dates = []

    for date in date_matches:
        if date not in unique_dates:
            unique_dates.append(date)

    # -------------------------------------------------
    # 9. ADMISSION DATE
    # -------------------------------------------------

    admission_match = re.search(
        r"Admission date\s*:?\s*(\d{2}\.\d{2}\.\d{4})",
        text,
        re.IGNORECASE
    )

    if admission_match:
        result["admission_date"] = admission_match.group(1)

    # -------------------------------------------------
    # 10. DISCHARGE DATE
    # -------------------------------------------------

    discharge_match = re.search(
        r"Discharge date\s*:?\s*(\d{2}\.\d{2}\.\d{4})",
        text,
        re.IGNORECASE
    )

    if discharge_match:
        result["discharge_date"] = discharge_match.group(1)

    # -------------------------------------------------
    # 11. BILLING DATE
    # -------------------------------------------------

    billing_match = re.search(
        r"Billing date\s*:?\s*(\d{2}\.\d{2}\.\d{4})",
        text,
        re.IGNORECASE
    )

    if billing_match:
        result["billing_date"] = billing_match.group(1)

    # -------------------------------------------------
    # 12. DATE FALLBACK / OCR LAYOUT RECOVERY
    # -------------------------------------------------

    parsed_dates = []

    for date in unique_dates:
        try:
            parsed_date = datetime.strptime(
                date,
                "%d.%m.%Y"
            )

            parsed_dates.append(
                (parsed_date, date)
            )

        except ValueError:
            pass

    parsed_dates.sort()

    # If admission date is missing,
    # use the earliest detected date.
    if not result["admission_date"] and parsed_dates:
        result["admission_date"] = parsed_dates[0][1]

    # If discharge date is missing,
    # use the latest date available.
    if not result["discharge_date"] and parsed_dates:
        result["discharge_date"] = parsed_dates[-1][1]

    # -------------------------------------------------
    # 13. TOTAL CHARGES
    # -------------------------------------------------

    total_match = re.search(
        r"Total charges\s*:?\s*([\d,]+\.\d{2})",
        text,
        re.IGNORECASE
    )

    if total_match:

        result["total_charges"] = float(
            total_match.group(1).replace(",", "")
        )

    else:

        # OCR may put amount on next line
        for index, line in enumerate(lines):

            if "total charges" in line.lower():

                if index + 1 < len(lines):

                    amount_match = re.search(
                        r"([\d,]+\.\d{2})",
                        lines[index + 1]
                    )

                    if amount_match:

                        result["total_charges"] = float(
                            amount_match.group(1).replace(",", "")
                        )

                break

    # -------------------------------------------------
    # 14. FINAL DATE CONSISTENCY CHECK
    # -------------------------------------------------

    def parse_date(value):

        if not value:
            return None

        try:
            return datetime.strptime(
                value,
                "%d.%m.%Y"
            )

        except ValueError:
            return None

    admission_dt = parse_date(
        result["admission_date"]
    )

    discharge_dt = parse_date(
        result["discharge_date"]
    )

    billing_dt = parse_date(
        result["billing_date"]
    )

    # If OCR assigned admission date to discharge
    # but billing date is later, correct discharge.
    if (
        admission_dt
        and discharge_dt
        and billing_dt
        and discharge_dt == admission_dt
        and billing_dt > admission_dt
    ):
        result["discharge_date"] = result["billing_date"]

    # -------------------------------------------------
    # 15. FINAL RESULT
    # -------------------------------------------------

    return result


# =====================================================
# LOCAL TEST
# =====================================================

if __name__ == "__main__":

    sample_text = """
    KK Women's and Children's Hospital
    TAX INVOICE

    Patient : VERCELLA VERONICA

    External ID/NRIC
    Case number
    : X0724956604F

    Customer number
    : 76100506511

    Admission date
    : 3024956604

    Discharge date
    : 17.08.2010

    Billing date
    : 24.08.2010

    Total charges
    11,636.41
    """

    result = extract_information(sample_text)

    print("\nInformation Extraction Result")
    print("--------------------------------")

    for key, value in result.items():
        print(f"{key}: {value}")