from datetime import datetime


def parse_date(value):
    """Convert DD.MM.YYYY string into datetime."""

    if not value:
        return None

    try:
        return datetime.strptime(value, "%d.%m.%Y")

    except (ValueError, TypeError):
        return None


def validate_extracted_information(data: dict):
    """
    Validate structured information extracted from a claim document.

    This engine does NOT modify extracted data.
    It only identifies missing fields, inconsistencies,
    and risk indicators.
    """

    missing_fields = []
    mismatches = []
    risk_indicators = []

    # -------------------------------------------------
    # 1. REQUIRED FIELDS
    # -------------------------------------------------

    required_fields = [
        "patient_name",
        "external_id",
        "case_number",
        "customer_number",
        "admission_date",
        "discharge_date",
        "billing_date",
        "total_charges",
    ]

    for field in required_fields:

        value = data.get(field)

        if value is None or str(value).strip() == "":
            missing_fields.append(field)

    # -------------------------------------------------
    # 2. DATE VALIDATION
    # -------------------------------------------------

    admission_date = parse_date(
        data.get("admission_date")
    )

    discharge_date = parse_date(
        data.get("discharge_date")
    )

    billing_date = parse_date(
        data.get("billing_date")
    )

    # Invalid date format
    for field, value in [
        ("admission_date", admission_date),
        ("discharge_date", discharge_date),
        ("billing_date", billing_date),
    ]:

        original_value = data.get(field)

        if original_value and value is None:

            mismatches.append({
                "field": field,
                "issue": "Invalid date format",
                "value": original_value,
            })

    # -------------------------------------------------
    # 3. DATE CONSISTENCY
    # -------------------------------------------------

    if admission_date and discharge_date:

        if admission_date > discharge_date:

            mismatches.append({
                "field": "admission_date / discharge_date",
                "issue": "Admission date occurs after discharge date",
                "admission_date": data.get("admission_date"),
                "discharge_date": data.get("discharge_date"),
            })

            risk_indicators.append(
                "Invalid hospitalization date sequence"
            )

    if discharge_date and billing_date:

        if discharge_date > billing_date:

            mismatches.append({
                "field": "discharge_date / billing_date",
                "issue": "Billing date occurs before discharge date",
                "discharge_date": data.get("discharge_date"),
                "billing_date": data.get("billing_date"),
            })

            risk_indicators.append(
                "Billing date inconsistency"
            )

    # -------------------------------------------------
    # 4. AMOUNT VALIDATION
    # -------------------------------------------------

    total_charges = data.get("total_charges")

    if total_charges is not None:

        try:
            amount = float(total_charges)

            if amount < 0:

                mismatches.append({
                    "field": "total_charges",
                    "issue": "Negative claim amount",
                    "value": total_charges,
                })

                risk_indicators.append(
                    "Invalid financial amount"
                )

            elif amount == 0:

                risk_indicators.append(
                    "Zero claim amount"
                )

        except (ValueError, TypeError):

            mismatches.append({
                "field": "total_charges",
                "issue": "Invalid numeric amount",
                "value": total_charges,
            })

    # -------------------------------------------------
    # 5. ID FORMAT VALIDATION
    # -------------------------------------------------

    external_id = data.get("external_id")

    if external_id:

        if not isinstance(external_id, str):

            mismatches.append({
                "field": "external_id",
                "issue": "Invalid external ID format",
                "value": external_id,
            })

    customer_number = data.get("customer_number")

    if customer_number:

        if not str(customer_number).isdigit():

            mismatches.append({
                "field": "customer_number",
                "issue": "Customer number contains invalid characters",
                "value": customer_number,
            })

    # -------------------------------------------------
    # 6. OVERALL STATUS
    # -------------------------------------------------

    if mismatches:
        verification_status = "Needs Review"

    elif missing_fields:
        verification_status = "Incomplete"

    else:
        verification_status = "Validated"

    # -------------------------------------------------
    # 7. READINESS SCORE
    # -------------------------------------------------

    total_required = len(required_fields)
    missing_count = len(missing_fields)

    completeness_score = (
        (total_required - missing_count)
        / total_required
    ) * 100

    # Penalize consistency problems
    mismatch_penalty = min(
        len(mismatches) * 10,
        40
    )

    readiness_score = max(
        0,
        completeness_score - mismatch_penalty
    )

    # -------------------------------------------------
    # 8. SUMMARY
    # -------------------------------------------------

    if verification_status == "Validated":

        summary = (
            "All required extracted fields are present "
            "and passed basic consistency validation."
        )

    elif verification_status == "Incomplete":

        summary = (
            "Required information is missing from the "
            "extracted document and requires review."
        )

    else:

        summary = (
            "The extracted document contains consistency "
            "issues that require review."
        )

    # -------------------------------------------------
    # 9. FINAL VALIDATION RESULT
    # -------------------------------------------------

    return {
        "verification_status": verification_status,
        "readiness_score": round(readiness_score, 2),
        "missing_fields": missing_fields,
        "mismatches": mismatches,
        "risk_indicators": risk_indicators,
        "verification_summary": summary,
    }


# =====================================================
# LOCAL TEST
# =====================================================

if __name__ == "__main__":

    sample_data = {
        "hospital_name": "KK Women's and Children's Hospital",
        "patient_name": "VERCELLA VERONICA",
        "external_id": "X0724956604F",
        "case_number": "3024956604",
        "customer_number": "76100506511",
        "admission_date": "17.08.2010",
        "discharge_date": "24.08.2010",
        "billing_date": "24.08.2010",
        "total_charges": 11636.41,
    }

    result = validate_extracted_information(
        sample_data
    )

    print("\nValidation Result")
    print("=" * 50)

    print(
        f"Status: "
        f"{result['verification_status']}"
    )

    print(
        f"Readiness Score: "
        f"{result['readiness_score']}"
    )

    print(
        f"Missing Fields: "
        f"{result['missing_fields']}"
    )

    print(
        f"Mismatches: "
        f"{result['mismatches']}"
    )

    print(
        f"Risk Indicators: "
        f"{result['risk_indicators']}"
    )

    print(
        f"Summary: "
        f"{result['verification_summary']}"
    )