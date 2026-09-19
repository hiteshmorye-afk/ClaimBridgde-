"""
ClaimBridge Confidence Engine

Architecture position:

Medical Intelligence
        +
Policy Intelligence
        +
Validation Engine
        +
Claim Readiness Engine
        ↓
Confidence Engine
        ↓
Auto Processing / Human Review

The Confidence Engine measures confidence in the available
claim evidence and determines whether the claim can proceed
automatically or requires human review.

It does NOT make the final claim approval/rejection decision.
"""

from typing import Any, Dict


# =========================================================
# CONFIDENCE WEIGHTS
# =========================================================

OCR_WEIGHT = 0.20
MEDICAL_WEIGHT = 0.25
POLICY_WEIGHT = 0.25
VALIDATION_WEIGHT = 0.20
READINESS_WEIGHT = 0.10


# =========================================================
# SCORE NORMALIZATION
# =========================================================

def normalize_score(
    score: float,
) -> float:
    """Keep a score between 0 and 100."""

    return max(
        0.0,
        min(
            float(score),
            100.0,
        ),
    )


# =========================================================
# OCR CONFIDENCE
# =========================================================

def calculate_ocr_confidence(
    ocr_result: Dict[str, Any],
) -> float:
    """
    Convert OCR confidence from 0-1 to 0-100.
    """

    confidence = ocr_result.get(
        "confidence",
        0.0,
    )

    return normalize_score(
        float(confidence) * 100
    )


# =========================================================
# MEDICAL CONFIDENCE
# =========================================================

def calculate_medical_confidence(
    medical_result: Dict[str, Any],
) -> float:
    """
    Convert Medical Intelligence confidence
    from 0-1 to 0-100.
    """

    confidence = medical_result.get(
        "confidence_score",
        0.0,
    )

    return normalize_score(
        float(confidence) * 100
    )


# =========================================================
# POLICY CONFIDENCE
# =========================================================

def calculate_policy_confidence(
    policy_result: Dict[str, Any],
) -> float:
    """
    Convert Policy Intelligence retrieval confidence
    into a 0-100 score.
    """

    confidence = policy_result.get(
        "retrieval_confidence",
        0.0,
    )

    return normalize_score(
        float(confidence) * 100
    )


# =========================================================
# VALIDATION CONFIDENCE
# =========================================================

def calculate_validation_confidence(
    validation_result: Dict[str, Any],
) -> float:
    """
    Convert validation results into a confidence score.

    A fully validated claim receives 100.
    Missing information or mismatches reduce confidence.
    """

    score = normalize_score(
        validation_result.get(
            "readiness_score",
            0.0,
        )
    )

    if validation_result.get(
        "mismatches"
    ):
        score -= 20

    if validation_result.get(
        "missing_fields"
    ):
        score -= 20

    return normalize_score(score)


# =========================================================
# READINESS CONFIDENCE
# =========================================================

def calculate_readiness_confidence(
    readiness_result: Dict[str, Any],
) -> float:
    """
    Use the Claim Readiness Engine score as one
    supporting confidence factor.
    """

    return normalize_score(
        readiness_result.get(
            "readiness_score",
            0.0,
        )
    )


# =========================================================
# OVERALL CONFIDENCE
# =========================================================

def calculate_overall_confidence(
    ocr_confidence: float,
    medical_confidence: float,
    policy_confidence: float,
    validation_confidence: float,
    readiness_confidence: float,
) -> float:
    """
    Calculate the weighted overall evidence confidence.
    """

    score = (
        ocr_confidence * OCR_WEIGHT
        + medical_confidence * MEDICAL_WEIGHT
        + policy_confidence * POLICY_WEIGHT
        + validation_confidence * VALIDATION_WEIGHT
        + readiness_confidence * READINESS_WEIGHT
    )

    return round(
        normalize_score(score),
        2,
    )


# =========================================================
# CONFIDENCE LEVEL
# =========================================================

def determine_confidence_level(
    confidence_score: float,
) -> str:
    """
    Convert the numerical confidence score into
    an explainable confidence level.
    """

    if confidence_score >= 85:
        return "High"

    if confidence_score >= 70:
        return "Medium"

    return "Low"


# =========================================================
# PROCESSING ROUTE
# =========================================================

def determine_processing_route(
    confidence_score: float,
    validation_result: Dict[str, Any],
    medical_result: Dict[str, Any],
    policy_result: Dict[str, Any],
    readiness_result: Dict[str, Any],
) -> str:
    """
    Determine whether the claim can proceed to
    automatic processing or requires human review.

    This is routing logic, NOT final claim approval.
    """

    # -----------------------------------------------------
    # Mandatory human review conditions
    # -----------------------------------------------------

    if validation_result.get(
        "mismatches"
    ):
        return "Human Review"

    if policy_result.get(
        "relevant_exclusions"
    ):
        return "Human Review"

    if policy_result.get(
        "policy_status"
    ) == "Insufficient Policy Evidence":
        return "Human Review"

    if medical_result.get(
        "processing_status"
    ) == "Insufficient Data":
        return "Human Review"

    if readiness_result.get(
        "readiness_status"
    ) == "Needs Human Review":
        return "Human Review"

    # -----------------------------------------------------
    # Confidence-based routing
    # -----------------------------------------------------

    if confidence_score >= 85:
        return "Auto Processing"

    return "Human Review"


# =========================================================
# CONFIDENCE REASONS
# =========================================================

def generate_confidence_reasons(
    confidence_score: float,
    confidence_level: str,
    processing_route: str,
    component_scores: Dict[str, float],
) -> list[str]:
    """
    Generate explainable reasons for the confidence result.
    """

    reasons = []

    if component_scores["ocr_confidence"] >= 85:
        reasons.append(
            "OCR confidence is high."
        )
    else:
        reasons.append(
            "OCR confidence requires additional verification."
        )

    if component_scores["medical_confidence"] >= 85:
        reasons.append(
            "Medical Intelligence produced high-confidence information."
        )
    else:
        reasons.append(
            "Medical information has limited confidence."
        )

    if component_scores["policy_confidence"] >= 85:
        reasons.append(
            "Policy retrieval produced strong evidence."
        )
    else:
        reasons.append(
            "Policy retrieval confidence is below the high-confidence threshold."
        )

    if component_scores["validation_confidence"] >= 85:
        reasons.append(
            "Claim information passed validation with high confidence."
        )
    else:
        reasons.append(
            "Validation identified information that requires attention."
        )

    reasons.append(
        f"Overall evidence confidence: {confidence_score:.2f}%."
    )

    reasons.append(
        f"Processing route: {processing_route}."
    )

    return reasons


# =========================================================
# MAIN CONFIDENCE ENGINE
# =========================================================

def evaluate_claim_confidence(
    ocr_result: Dict[str, Any],
    medical_result: Dict[str, Any],
    policy_result: Dict[str, Any],
    validation_result: Dict[str, Any],
    readiness_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Main Confidence Engine entry point.

    Combines confidence from:

    - OCR
    - Medical Intelligence
    - Policy Intelligence
    - Validation Engine
    - Claim Readiness Engine
    """

    # -----------------------------------------------------
    # Component confidence
    # -----------------------------------------------------

    ocr_confidence = calculate_ocr_confidence(
        ocr_result
    )

    medical_confidence = calculate_medical_confidence(
        medical_result
    )

    policy_confidence = calculate_policy_confidence(
        policy_result
    )

    validation_confidence = calculate_validation_confidence(
        validation_result
    )

    readiness_confidence = calculate_readiness_confidence(
        readiness_result
    )

    # -----------------------------------------------------
    # Overall confidence
    # -----------------------------------------------------

    overall_confidence = calculate_overall_confidence(
        ocr_confidence=ocr_confidence,
        medical_confidence=medical_confidence,
        policy_confidence=policy_confidence,
        validation_confidence=validation_confidence,
        readiness_confidence=readiness_confidence,
    )

    # -----------------------------------------------------
    # Confidence level
    # -----------------------------------------------------

    confidence_level = determine_confidence_level(
        overall_confidence
    )

    # -----------------------------------------------------
    # Processing route
    # -----------------------------------------------------

    processing_route = determine_processing_route(
        confidence_score=overall_confidence,
        validation_result=validation_result,
        medical_result=medical_result,
        policy_result=policy_result,
        readiness_result=readiness_result,
    )

    # -----------------------------------------------------
    # Explainability
    # -----------------------------------------------------

    component_scores = {
        "ocr_confidence": round(
            ocr_confidence,
            2,
        ),
        "medical_confidence": round(
            medical_confidence,
            2,
        ),
        "policy_confidence": round(
            policy_confidence,
            2,
        ),
        "validation_confidence": round(
            validation_confidence,
            2,
        ),
        "readiness_confidence": round(
            readiness_confidence,
            2,
        ),
    }

    reasons = generate_confidence_reasons(
        confidence_score=overall_confidence,
        confidence_level=confidence_level,
        processing_route=processing_route,
        component_scores=component_scores,
    )

    return {
        "confidence_score": overall_confidence,

        "confidence_level": confidence_level,

        "processing_route": processing_route,

        "component_scores": component_scores,

        "confidence_reasons": reasons,

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

    sample_medical_result = {
        "diagnosis": "Acute infection",
        "procedure": "Surgical treatment",
        "medical_terms": [
            "diagnosis",
            "infection",
            "procedure",
            "treatment",
        ],
        "confidence_score": 0.90,
        "processing_status": "Analyzed",
    }

    sample_policy_result = {
        "policy_status": "Potentially Covered",
        "retrieval_confidence": 0.90,
        "relevant_exclusions": [],
    }

    sample_validation_result = {
        "verification_status": "Validated",
        "readiness_score": 100.0,
        "missing_fields": [],
        "mismatches": [],
    }

    sample_readiness_result = {
        "readiness_score": 96.30,
        "readiness_status": "Ready for Next Stage",
    }

    result = evaluate_claim_confidence(
        ocr_result=sample_ocr_result,
        medical_result=sample_medical_result,
        policy_result=sample_policy_result,
        validation_result=sample_validation_result,
        readiness_result=sample_readiness_result,
    )

    print("\n" + "=" * 60)
    print("CLAIMBRIDGE CONFIDENCE ENGINE")
    print("=" * 60)

    for key, value in result.items():
        print(f"\n{key}:")
        print(value)