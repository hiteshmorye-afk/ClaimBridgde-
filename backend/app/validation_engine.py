from typing import Dict, Any


# Fields that are essential for validating a hospital claim.
# These fields should normally be available in a hospital bill.
REQUIRED_FIELDS = [
    "patient_name",
    "external_id",
    "admission_date",
    "discharge_date",
    "total_charges",
]


# These fields may or may not be present depending on the
# hospital's document format. Their absence should not make
# an otherwise complete claim incomplete.
DOCUMENT_DEPENDENT_FIELDS = [
    "case_number",
    "customer_number",
    "billing_date",
]


EXPECTED_DATE_FORMAT = "%d.%m.%Y"


def _validate_date_format(value: Any, field_name: str, mismatches: list):
    """
    Validate date format when a date value is present.
    Expected format: DD.MM.YYYY
    """
    if value is None or value == "":
        return

    if not isinstance(value, str):
        mismatches.append(
            f"{field_name} must be a string in DD.MM.YYYY format"
        )
        return

    parts = value.split(".")

    if len(parts) != 3:
        mismatches.append(
            f"{field_name} has invalid date format: {value}"
        )
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
        mismatches.append(
            f"{field_name} has invalid date format: {value}"
        )


def _date_to_tuple(value: Any):
    """
    Convert DD.MM.YYYY into a comparable tuple.
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


def validate_extracted_information(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate structured information extracted from a claim document.

    Validation is divided into:

    1. Core required fields
       These are necessary for basic claim validation.

    2. Document-dependent fields
       These may not exist on every hospital document and therefore
       should not automatically make the claim incomplete.

    The function also performs consistency and value checks.
    """

    missing_fields = []
    optional_missing_fields = []
    mismatches = []
    risk_indicators = []

    # ---------------------------------------------------------
    # 1. Check core required fields
    # ---------------------------------------------------------

    for field in REQUIRED_FIELDS:
        value = extracted_data.get(field)

        if value is None or value == "":
            missing_fields.append(field)

    # ---------------------------------------------------------
    # 2. Check document-dependent fields separately
    # ---------------------------------------------------------

    for field in DOCUMENT_DEPENDENT_FIELDS:
        value = extracted_data.get(field)

        if value is None or value == "":
            optional_missing_fields.append(field)

    # ---------------------------------------------------------
    # 3. Validate date formats
    # ---------------------------------------------------------

    date_fields = [
        "admission_date",
        "discharge_date",
        "billing_date",
    ]

    for field in date_fields:
        _validate_date_format(
            extracted_data.get(field),
            field,
            mismatches,
        )

    # ---------------------------------------------------------
    # 4. Validate admission and discharge date consistency
    # ---------------------------------------------------------

    admission_date = _date_to_tuple(
        extracted_data.get("admission_date")
    )

    discharge_date = _date_to_tuple(
        extracted_data.get("discharge_date")
    )

    billing_date = _date_to_tuple(
        extracted_data.get("billing_date")
    )

    if admission_date and discharge_date:
        if admission_date > discharge_date:
            mismatches.append(
                "Admission date cannot be later than discharge date"
            )
            risk_indicators.append(
                "Invalid admission/discharge date sequence"
            )

    # ---------------------------------------------------------
    # 5. Validate billing date when available
    # ---------------------------------------------------------

    if discharge_date and billing_date:
        if discharge_date > billing_date:
            mismatches.append(
                "Billing date cannot be earlier than discharge date"
            )
            risk_indicators.append(
                "Billing date occurs before discharge date"
            )

    # ---------------------------------------------------------
    # 6. Validate total charges
    # ---------------------------------------------------------

    total_charges = extracted_data.get("total_charges")

    if total_charges is not None and total_charges != "":
        try:
            amount = float(total_charges)

            if amount <= 0:
                mismatches.append(
                    "Total charges must be greater than zero"
                )
                risk_indicators.append(
                    "Invalid total charges amount"
                )

        except (TypeError, ValueError):
            mismatches.append(
                "Total charges must be a valid numeric value"
            )
            risk_indicators.append(
                "Invalid total charges format"
            )

    # ---------------------------------------------------------
    # 7. Validate external ID
    # ---------------------------------------------------------

    external_id = extracted_data.get("external_id")

    if external_id is not None and external_id != "":
        if not isinstance(external_id, str):
            mismatches.append(
                "External ID must be stored as a string"
            )

    # ---------------------------------------------------------
    # 8. Validate customer number only when present
    # ---------------------------------------------------------

    customer_number = extracted_data.get("customer_number")

    if customer_number is not None and customer_number != "":
        if not str(customer_number).isdigit():
            mismatches.append(
                "Customer number must contain only digits"
            )

    # ---------------------------------------------------------
    # 9. Determine verification status
    # ---------------------------------------------------------

    if mismatches:
        verification_status = "Needs Review"

    elif missing_fields:
        verification_status = "Incomplete"

    else:
        verification_status = "Validated"

    # ---------------------------------------------------------
    # 10. Calculate validation readiness score
    #
    # Only core required fields affect completeness.
    # Optional/document-dependent fields do not reduce the score.
    # ---------------------------------------------------------

    total_required = len(REQUIRED_FIELDS)
    present_required = total_required - len(missing_fields)

    if total_required > 0:
        completeness_score = (
            present_required / total_required
        ) * 100
    else:
        completeness_score = 100.0

    # Apply mismatch penalty.
    # Preserve the previous concept of a maximum 40-point penalty.
    mismatch_penalty = min(len(mismatches) * 10, 40)

    readiness_score = max(
        0.0,
        completeness_score - mismatch_penalty
    )

    # ---------------------------------------------------------
    # 11. Add informational risk indicator for optional fields
    #
    # These do not reduce the validation score.
    # ---------------------------------------------------------

    if optional_missing_fields:
        risk_indicators.append(
            "Document-dependent fields not present: "
            + ", ".join(optional_missing_fields)
        )

    # ---------------------------------------------------------
    # 12. Verification summary
    # ---------------------------------------------------------

    if verification_status == "Validated":
        if optional_missing_fields:
            verification_summary = (
                "All core claim fields required for validation "
                "are present and consistent. Some document-dependent "
                "fields are not available in the submitted document."
            )
        else:
            verification_summary = (
                "All required claim fields are present and consistent."
            )

    elif verification_status == "Incomplete":
        verification_summary = (
            "One or more core claim fields required for validation "
            "are missing."
        )

    else:
        verification_summary = (
            "Validation inconsistencies were detected and the claim "
            "requires review."
        )

    # ---------------------------------------------------------
    # 13. Final validation result
    # ---------------------------------------------------------

    return {
        "verification_status": verification_status,
        "readiness_score": round(readiness_score, 2),
        "missing_fields": missing_fields,
        "optional_missing_fields": optional_missing_fields,
        "mismatches": mismatches,
        "risk_indicators": risk_indicators,
        "verification_summary": verification_summary,
    }