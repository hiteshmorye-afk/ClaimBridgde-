"""
ClaimBridge Claim Readiness Engine

Architecture position:

Medical Intelligence
        +
Policy Intelligence
        +
Validation Engine
        ↓
Claim Readiness Engine
        ↓
Confidence Engine
        ↓
Auto Processing / Human Review

The Claim Readiness Engine does NOT make the final claim
approval or rejection decision.

Its responsibility is to determine whether the claim has
sufficient evidence, consistency, medical analysis, and
policy analysis to proceed to the next stage.
"""

from typing import Any, Dict


# =========================================================
# SCORE WEIGHTS
# =========================================================

VALIDATION_WEIGHT = 0.35
MEDICAL_WEIGHT = 0.25
POLICY_WEIGHT = 0.25
OCR_WEIGHT = 0.15


# =========================================================
# VALIDATION SCORE
# =========================================================

def calculate_validation_score(
    validation_result: Dict[str, Any],
) -> float:
    """
    Convert Validation Engine output into a normalized score.
    """

    readiness_score = validation_result.get(
        "readiness_score",
        0.0,
    )

    return max(
        0.0,
        min(
            float(readiness_score),
            100.0,
        ),
    )


# =========================================================
# MEDICAL SCORE
# =========================================================

def calculate_medical_score(
    medical_result: Dict[str, Any],
) -> float:
    """
    Calculate the medical evidence score.

    Medical confidence is converted from 0-1 to 0-100.
    """

    confidence = medical_result.get(
        "confidence_score",
        0.0,
    )

    score = float(confidence) * 100

    # If no medical information was detected,
    # the claim should not receive a high medical score.
    if not medical_result.get("medical_terms"):
        score = min(score, 30.0)

    return max(
        0.0,
        min(score, 100.0),
    )


# =========================================================
# POLICY SCORE
# =========================================================

def calculate_policy_score(
    policy_result: Dict[str, Any],
) -> float:
    """
    Calculate the policy evidence score.

    This score reflects the quality of available policy
    evidence, not whether the claim should ultimately
    be approved or rejected.
    """

    retrieval_confidence = policy_result.get(
        "retrieval_confidence",
        0.0,
    )

    score = float(
        retrieval_confidence
    ) * 100

    policy_status = policy_result.get(
        "policy_status",
        "",
    )

    if policy_status == "Potentially Covered":
        score += 20.0

    elif policy_status == "Relevant Exclusion Detected":
        # Evidence exists, but the claim requires
        # additional review.
        score += 10.0

    elif policy_status == "Insufficient Policy Evidence":
        score = min(score, 30.0)

    return max(
        0.0,
        min(score, 100.0),
    )


# =========================================================
# OCR SCORE
# =========================================================

def calculate_ocr_score(
    ocr_result: Dict[str, Any],
) -> float:
    """
    Convert OCR confidence into a 0-100 score.
    """

    confidence = ocr_result.get(
        "confidence",
        0.0,
    )

    return max(
        0.0,
        min(
            float(confidence) * 100,
            100.0,
        ),
    )


# =========================================================
# OVERALL READINESS
# =========================================================

def calculate_overall_readiness(
    validation_score: float,
    medical_score: float,
    policy_score: float,
    ocr_score: float,
) -> float:
    """
    Calculate the weighted Claim Readiness Score.
    """

    score = (
        validation_score * VALIDATION_WEIGHT
        + medical_score * MEDICAL_WEIGHT
        + policy_score * POLICY_WEIGHT
        + ocr_score * OCR_WEIGHT
    )

    return round(
        max(
            0.0,
            min(score, 100.0),
        ),
        2,
    )


# =========================================================
# READINESS STATUS
# =========================================================

def determine_readiness_status(
    overall_score: float,
    validation_result: Dict[str, Any],
    medical_result: Dict[str, Any],
    policy_result: Dict[str, Any],
) -> str:
    """
    Determine whether the claim is ready for the
    next processing stage.

    This does NOT represent final claim approval.
    """

    verification_status = validation_result.get(
        "verification_status",
        "",
    )

    policy_status = policy_result.get(
        "policy_status",
        "",
    )

    medical_status = medical_result.get(
        "processing_status",
        "",
    )

    # -----------------------------------------------------
    # Immediate review conditions
    # -----------------------------------------------------

    if verification_status == "Needs Review":
        return "Needs Human Review"

    if policy_status == "Relevant Exclusion Detected":
        return "Needs Human Review"

    if policy_status == "Insufficient Policy Evidence":
        return "Needs Human Review"

    if medical_status == "Insufficient Data":
        return "Needs Human Review"

    # -----------------------------------------------------
    # Score-based readiness
    # -----------------------------------------------------

    if overall_score >= 80:
        return "Ready for Next Stage"

    if overall_score >= 60:
        return "Conditionally Ready"

    return "Needs Human Review"


# =========================================================
# READINESS REASONS
# =========================================================

def generate_readiness_reasons(
    validation_result: Dict[str, Any],
    medical_result: Dict[str, Any],
    policy_result: Dict[str, Any],
    overall_score: float,
) -> list[str]:
    """
    Generate explainable reasons for the readiness status.
    """

    reasons = []

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    if validation_result.get(
        "missing_fields"
    ):

        reasons.append(
            "Required claim information is incomplete."
        )

    if validation_result.get(
        "mismatches"
    ):

        reasons.append(
            "Consistency mismatches were detected."
        )

    if not validation_result.get(
        "missing_fields"
    ) and not validation_result.get(
        "mismatches"
    ):

        reasons.append(
            "Required claim information passed structural validation."
        )

    # -----------------------------------------------------
    # Medical Intelligence
    # -----------------------------------------------------

    if medical_result.get(
        "diagnosis"
    ):

        reasons.append(
            "Diagnosis information was identified."
        )

    else:

        reasons.append(
            "Diagnosis information was not confidently identified."
        )

    if medical_result.get(
        "procedure"
    ):

        reasons.append(
            "Procedure information was identified."
        )

    # -----------------------------------------------------
    # Policy Intelligence
    # -----------------------------------------------------

    if policy_result.get(
        "policy_status"
    ) == "Potentially Covered":

        reasons.append(
            "Relevant policy coverage evidence was identified."
        )

    if policy_result.get(
        "relevant_exclusions"
    ):

        reasons.append(
            "A policy exclusion may be relevant to the claim."
        )

    if policy_result.get(
        "policy_status"
    ) == "Insufficient Policy Evidence":

        reasons.append(
            "Sufficient policy evidence was not retrieved."
        )

    # -----------------------------------------------------
    # Overall score
    # -----------------------------------------------------

    reasons.append(
        f"Overall claim readiness score: {overall_score:.2f}%."
    )

    return reasons


# =========================================================
# MAIN CLAIM READINESS FUNCTION
# =========================================================

def evaluate_claim_readiness(
    ocr_result: Dict[str, Any],
    validation_result: Dict[str, Any],
    medical_result: Dict[str, Any],
    policy_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Main Claim Readiness Engine entry point.

    Combines:

    OCR confidence
    Validation result
    Medical Intelligence
    Policy Intelligence

    and produces an explainable readiness assessment.
    """

    # -----------------------------------------------------
    # Calculate component scores
    # -----------------------------------------------------

    validation_score = calculate_validation_score(
        validation_result
    )

    medical_score = calculate_medical_score(
        medical_result
    )

    policy_score = calculate_policy_score(
        policy_result
    )

    ocr_score = calculate_ocr_score(
        ocr_result
    )

    # -----------------------------------------------------
    # Overall readiness
    # -----------------------------------------------------

    overall_score = calculate_overall_readiness(
        validation_score=validation_score,
        medical_score=medical_score,
        policy_score=policy_score,
        ocr_score=ocr_score,
    )

    # -----------------------------------------------------
    # Readiness status
    # -----------------------------------------------------

    readiness_status = determine_readiness_status(
        overall_score=overall_score,
        validation_result=validation_result,
        medical_result=medical_result,
        policy_result=policy_result,
    )

    # -----------------------------------------------------
    # Explainability
    # -----------------------------------------------------

    reasons = generate_readiness_reasons(
        validation_result=validation_result,
        medical_result=medical_result,
        policy_result=policy_result,
        overall_score=overall_score,
    )

    return {
        "readiness_score": overall_score,

        "readiness_status": readiness_status,

        "component_scores": {
            "validation_score": round(
                validation_score,
                2,
            ),
            "medical_score": round(
                medical_score,
                2,
            ),
            "policy_score": round(
                policy_score,
                2,
            ),
            "ocr_score": round(
                ocr_score,
                2,
            ),
        },

        "readiness_reasons": reasons,

        "processing_status": "Analyzed",
    }


# =========================================================
# MODULE TEST
# =========================================================

if __name__ == "__main__":

    sample_ocr_result = {
        "confidence": 0.92,
        "line_count": 15,
    }

    sample_validation_result = {
        "verification_status": "Validated",
        "readiness_score": 100.0,
        "missing_fields": [],
        "mismatches": [],
    }

    sample_medical_result = {
        "diagnosis": "Acute infection",
        "procedure": "Surgical treatment",
        "medical_terms": [
            "diagnosis",
            "infection",
            "procedure",
            "treatment",
        ],
        "confidence_score": 0.9,
        "processing_status": "Analyzed",
    }

    sample_policy_result = {
        "policy_status": "Potentially Covered",
        "retrieval_confidence": 0.80,
        "relevant_exclusions": [],
    }

    result = evaluate_claim_readiness(
        ocr_result=sample_ocr_result,
        validation_result=sample_validation_result,
        medical_result=sample_medical_result,
        policy_result=sample_policy_result,
    )

    print("\n" + "=" * 60)
    print("CLAIMBRIDGE CLAIM READINESS ENGINE")
    print("=" * 60)

    for key, value in result.items():
        print(f"\n{key}:")
        print(value)