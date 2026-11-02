"""
ClaimBridge Document Reliability & Readiness Engine

Calculates an explainable 0-100 score for individual uploaded documents
based on 5 transparent dimensions:
1. Document Readability (20 pts)
2. Correct Document Category (20 pts)
3. Required Information Completeness (25 pts)
4. Consistency with Patient/Claim Details (20 pts)
5. Authenticity Evidence (15 pts)

Statutory & Safety Rule:
Ordinary scanned hospital documents without cryptographic signature or
authorized issuer verification receive 0/15 authenticity points and are
explicitly labeled "Authenticity Not Independently Verified".
"""

from typing import Any, Dict, List, Optional


EXPECTED_FIELDS_BY_CATEGORY: Dict[str, List[str]] = {
    "hospital_bill": [
        "hospital_name",
        "patient_name",
        "bill_number",
        "total_amount",
        "admission_date",
    ],
    "discharge_summary": [
        "hospital_name",
        "patient_name",
        "admission_date",
        "discharge_date",
        "diagnosis",
    ],
    "claim_form": [
        "patient_name",
        "policy_number",
        "hospital_name",
        "claimed_amount",
    ],
    "insurance_card": [
        "policyholder_name",
        "policy_number",
        "member_id",
        "insurance_company",
    ],
    "identity_proof": [
        "patient_name",
        "id_number",
        "date_of_birth",
    ],
    "diagnostic_report": [
        "patient_name",
        "test_name",
        "report_date",
        "investigation_result",
    ],
    "consultation_letter": [
        "patient_name",
        "doctor_name",
        "diagnosis",
        "prescription",
    ],
    "payment_receipt": [
        "patient_name",
        "receipt_number",
        "amount_paid",
        "payment_date",
    ],
    "pharmacy_bill": [
        "patient_name",
        "bill_number",
        "total_amount",
    ],
    "pre_authorization": [
        "patient_name",
        "hospital_name",
        "policy_number",
        "estimated_cost",
    ],
}


def calculate_document_reliability(
    ocr_confidence: float,
    has_text: bool,
    category_match: Optional[bool],
    category_status: str,
    extracted_data: Optional[Dict[str, Any]],
    validation_mismatches: Optional[List[Any]],
    document_category: str,
    has_crypto_signature: bool = False,
    issuer_verified: bool = False,
) -> Dict[str, Any]:
    """
    Calculate the transparent 0-100 Document Reliability & Readiness Score.
    """
    extracted_data = extracted_data or {}
    validation_mismatches = validation_mismatches or []

    # 1. READABILITY (Max 20 pts)
    if not has_text:
        readability_score = 0.0
        readability_label = "Unreadable File"
        readability_desc = "ClaimBridge could not read text from this file."
    else:
        conf = float(ocr_confidence or 0.0)
        if conf > 1.0:
            conf = conf / 100.0  # normalize to 0.0 - 1.0
        readability_score = round(min(20.0, max(5.0, conf * 20.0)), 1)
        if conf >= 0.80:
            readability_label = "High Readability"
            readability_desc = "Text reading quality is high. Most text was clearly recognized."
        elif conf >= 0.50:
            readability_label = "Moderate Readability"
            readability_desc = "Text is partially legible; some characters or figures may require review."
        else:
            readability_label = "Low Readability"
            readability_desc = "Scan quality is poor or faded; manual review recommended."

    # 2. CATEGORY MATCH (Max 20 pts)
    if category_match is True:
        category_score = 20.0
        category_label = "Correct Document Type"
        category_desc = "Uploaded file matches the selected document category."
    elif category_match is False or category_status == "Incorrect Document Type":
        category_score = 0.0
        category_label = "Incorrect Document Type"
        category_desc = "Uploaded file does not match the chosen category."
    else:
        category_score = 10.0
        category_label = "Category Unconfirmed"
        category_desc = "Document category could not be confirmed with high confidence."

    # 3. REQUIRED INFORMATION COMPLETENESS (Max 25 pts)
    expected_fields = EXPECTED_FIELDS_BY_CATEGORY.get(
        document_category.lower(),
        ["patient_name", "date", "hospital_name", "amount"],
    )

    found_fields = []
    missing_fields = []
    for field in expected_fields:
        matched = False
        for k, v in extracted_data.items():
            if v and str(v).strip() and (field in k.lower() or k.lower() in field):
                found_fields.append(field)
                matched = True
                break
        if not matched:
            missing_fields.append(field)

    found_count = len(found_fields)
    ratio = min(1.0, found_count / max(1, len(expected_fields)))
    completeness_score = round(max(5.0 if has_text else 0.0, ratio * 25.0), 1)
    if ratio >= 0.80:
        completeness_desc = "Most critical fields expected for this document were successfully identified."
    elif ratio >= 0.40:
        completeness_desc = "Some expected details were identified, but a few key fields are missing."
    else:
        completeness_desc = "Key details required for this document category were not found."

    # 4. CONSISTENCY WITH PATIENT & CLAIM (Max 20 pts)
    mismatch_count = len(validation_mismatches)
    penalty = min(20.0, mismatch_count * 5.0)
    consistency_score = round(max(0.0, 20.0 - penalty), 1)
    if mismatch_count == 0:
        consistency_desc = "Extracted information is consistent with your claim details."
    elif mismatch_count == 1:
        consistency_desc = "One detail in this document differs from the claim information."
    else:
        consistency_desc = f"{mismatch_count} discrepancies were found between this document and your claim details."

    # 5. AUTHENTICITY EVIDENCE (Max 15 pts)
    if has_crypto_signature or issuer_verified:
        authenticity_score = 15.0
        authenticity_status = "Cryptographically Verified"
        authenticity_desc = "Valid digital signature or authorized issuer credential verified."
    else:
        authenticity_score = 0.0
        authenticity_status = "Authenticity Not Independently Verified"
        authenticity_desc = "Ordinary scanned hospital document. Issuing authority has not been independently verified."

    # Recommended corrections
    recommended_corrections: List[str] = []
    if category_match is False or category_status == "Incorrect Document Type":
        recommended_corrections.append("Re-upload the document under the correct category or replace with the matching file.")
    if readability_score < 12.0:
        recommended_corrections.append("Re-upload a clearer, higher-contrast scan to improve legibility.")
    if missing_fields:
        readable_missing = [f.replace("_", " ").title() for f in missing_fields[:3]]
        recommended_corrections.append(f"Ensure expected fields ({', '.join(readable_missing)}) are visible on the page.")
    if mismatch_count > 0:
        recommended_corrections.append("Check and reconcile conflicting details between document and claim registration.")
    if not recommended_corrections:
        recommended_corrections.append("Document satisfies current reliability checks. Ready for pre-auth evaluation.")

    # Extraction confidence normalized 0-100
    norm_conf = float(ocr_confidence or 0.0)
    if norm_conf <= 1.0:
        norm_conf = norm_conf * 100.0
    extraction_confidence = round(min(100.0, max(0.0, norm_conf)), 1)

    # TOTAL SCORE (0-100)
    total_score = round(
        min(
            100.0,
            max(
                0.0,
                readability_score
                + category_score
                + completeness_score
                + consistency_score
                + authenticity_score,
            ),
        ),
        1,
    )

    # READINESS TIER
    if total_score >= 90.0:
        tier = "High Readiness"
        tier_summary = "Document appears complete and consistent based on available checks."
    elif total_score >= 75.0:
        tier = "Good Readiness"
        tier_summary = "Minor information gaps or warnings; generally acceptable for review."
    elif total_score >= 50.0:
        tier = "Needs Attention"
        tier_summary = "Some information is missing or inconsistent. Manual review recommended."
    else:
        tier = "Low Readiness"
        tier_summary = "Major issues or category mismatch detected. Correction required."

    # DYNAMIC NON-TECHNICAL EXPLANATION
    explanation_parts = [
        f"Your document is {int(total_score)}/100 ready.",
        f"The uploaded file is {readability_label.lower()},",
        f"its document type is {category_label.lower()},",
        f"and {completeness_desc.lower()}",
    ]
    if mismatch_count > 0:
        explanation_parts.append(f"Note: {consistency_desc}")
    explanation_parts.append(
        "The document's issuing authority has not been independently verified."
        if authenticity_score == 0
        else "Digital authenticity has been verified."
    )

    dynamic_explanation = " ".join(explanation_parts)

    return {
        "score": total_score,
        "tier": tier,
        "tierSummary": tier_summary,
        "authenticityStatus": authenticity_status,
        "explanation": dynamic_explanation,
        "missingFields": [f.replace("_", " ").title() for f in missing_fields],
        "foundFields": [f.replace("_", " ").title() for f in found_fields],
        "extractionConfidence": extraction_confidence,
        "recommendedCorrections": recommended_corrections,
        "breakdown": {
            "readability": {
                "score": readability_score,
                "max": 20,
                "label": "Document Readability",
                "status": readability_label,
                "description": readability_desc,
            },
            "categoryMatch": {
                "score": category_score,
                "max": 20,
                "label": "Correct Document Category",
                "status": category_label,
                "description": category_desc,
            },
            "completeness": {
                "score": completeness_score,
                "max": 25,
                "label": "Information Completeness",
                "status": f"{int(ratio * 100)}% Found",
                "description": completeness_desc,
            },
            "consistency": {
                "score": consistency_score,
                "max": 20,
                "label": "Consistency with Claim",
                "status": f"{mismatch_count} Mismatches" if mismatch_count else "Consistent",
                "description": consistency_desc,
            },
            "authenticity": {
                "score": authenticity_score,
                "max": 15,
                "label": "Authenticity Evidence",
                "status": authenticity_status,
                "description": authenticity_desc,
            },
        },
    }
