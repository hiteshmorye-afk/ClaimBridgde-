"""
ClaimBridge Final Claim Decision Engine

Architecture position:

Validation Engine
        +
Medical Intelligence
        +
Policy Intelligence
        +
Claim Readiness Engine
        +
Confidence Engine
        ↓
Auto Processing / Human Review
        ↓
Final Claim Decision
        ↓
Claim History

This module produces an explainable processing decision.
It does NOT represent an insurer's legally binding decision.
"""

from typing import Any, Dict, List


# =========================================================
# DECISION THRESHOLDS
# =========================================================

AUTO_PROCESSING_THRESHOLD = 85.0
READINESS_THRESHOLD = 80.0


# =========================================================
# DECISION REASONS
# =========================================================

def generate_decision_reasons(
    decision: str,
    readiness_result: Dict[str, Any],
    confidence_result: Dict[str, Any],
    policy_result: Dict[str, Any],
    validation_result: Dict[str, Any],
) -> List[str]:
    """
    Generate explainable reasons for the final processing decision.
    """

    reasons = []

    readiness_score = readiness_result.get(
        "readiness_score",
        0.0,
    )

    confidence_score = confidence_result.get(
        "confidence_score",
        0.0,
    )

    policy_status = policy_result.get(
        "policy_status",
        "",
    )

    relevant_exclusions = policy_result.get(
        "relevant_exclusions",
        [],
    )

    mismatches = validation_result.get(
        "mismatches",
        [],
    )

    missing_fields = validation_result.get(
        "missing_fields",
        [],
    )

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    if mismatches:

        reasons.append(
            "Validation mismatches require additional review."
        )

    elif missing_fields:

        reasons.append(
            "Required claim information is incomplete."
        )

    else:

        reasons.append(
            "Claim information passed structural validation."
        )

    # -----------------------------------------------------
    # Policy
    # -----------------------------------------------------

    if relevant_exclusions:

        reasons.append(
            "One or more policy exclusions may apply to the claim."
        )

    elif policy_status == "Potentially Covered":

        reasons.append(
            "Relevant policy coverage evidence was identified."
        )

    else:

        reasons.append(
            "Policy evidence is insufficient for automated processing."
        )

    # -----------------------------------------------------
    # Readiness
    # -----------------------------------------------------

    reasons.append(
        f"Claim readiness score: {readiness_score:.2f}%."
    )

    # -----------------------------------------------------
    # Confidence
    # -----------------------------------------------------

    reasons.append(
        f"Evidence confidence score: {confidence_score:.2f}%."
    )

    # -----------------------------------------------------
    # Final route
    # -----------------------------------------------------

    if decision == "Proceed with Automated Processing":

        reasons.append(
            "Claim evidence meets the configured automated-processing thresholds."
        )

    elif decision == "Human Review Required":

        reasons.append(
            "Claim evidence does not meet the configured conditions for automated processing."
        )

    else:

        reasons.append(
            "Claim requires additional information before a processing decision can be made."
        )

    return reasons


# =========================================================
# FINAL DECISION
# =========================================================

def determine_final_claim_decision(
    readiness_result: Dict[str, Any],
    confidence_result: Dict[str, Any],
    policy_result: Dict[str, Any],
    validation_result: Dict[str, Any],
) -> str:
    """
    Determine the next claim-processing route.

    Important:
    This function does NOT approve or reject an insurance claim.

    It determines whether the claim can proceed through
    automated processing or requires human review.
    """

    readiness_score = float(
        readiness_result.get(
            "readiness_score",
            0.0,
        )
    )

    confidence_score = float(
        confidence_result.get(
            "confidence_score",
            0.0,
        )
    )

    processing_route = confidence_result.get(
        "processing_route",
        "",
    )

    policy_status = policy_result.get(
        "policy_status",
        "",
    )

    relevant_exclusions = policy_result.get(
        "relevant_exclusions",
        [],
    )

    mismatches = validation_result.get(
        "mismatches",
        [],
    )

    missing_fields = validation_result.get(
        "missing_fields",
        [],
    )

    # -----------------------------------------------------
    # Mandatory review conditions
    # -----------------------------------------------------

    if mismatches:

        return "Human Review Required"

    if missing_fields:

        return "Human Review Required"

    if relevant_exclusions:

        return "Human Review Required"

    if policy_status == "Insufficient Policy Evidence":

        return "Human Review Required"

    if processing_route == "Human Review":

        return "Human Review Required"

    # -----------------------------------------------------
    # Automated processing conditions
    # -----------------------------------------------------

    if (
        readiness_score >= READINESS_THRESHOLD
        and confidence_score >= AUTO_PROCESSING_THRESHOLD
        and processing_route == "Auto Processing"
    ):

        return "Proceed with Automated Processing"

    # -----------------------------------------------------
    # Otherwise
    # -----------------------------------------------------

    return "Additional Review Required"


# =========================================================
# MAIN DECISION FUNCTION
# =========================================================

def evaluate_final_claim_decision(
    readiness_result: Dict[str, Any],
    confidence_result: Dict[str, Any],
    policy_result: Dict[str, Any],
    validation_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Main Final Claim Decision entry point.

    Produces an explainable processing decision based on
    the outputs of the preceding ClaimBridge engines.
    """

    decision = determine_final_claim_decision(
        readiness_result=readiness_result,
        confidence_result=confidence_result,
        policy_result=policy_result,
        validation_result=validation_result,
    )

    reasons = generate_decision_reasons(
        decision=decision,
        readiness_result=readiness_result,
        confidence_result=confidence_result,
        policy_result=policy_result,
        validation_result=validation_result,
    )

    return {
        "decision": decision,

        "readiness_score": readiness_result.get(
            "readiness_score",
            0.0,
        ),

        "confidence_score": confidence_result.get(
            "confidence_score",
            0.0,
        ),

        "processing_route": confidence_result.get(
            "processing_route",
            "Unknown",
        ),

        "policy_status": policy_result.get(
            "policy_status",
            "Unknown",
        ),

        "decision_reasons": reasons,

        "processing_status": "Analyzed",
    }


# =========================================================
# MODULE TEST
# =========================================================

if __name__ == "__main__":

    sample_readiness_result = {
        "readiness_score": 96.30,
        "readiness_status": "Ready for Next Stage",
    }

    sample_confidence_result = {
        "confidence_score": 93.03,
        "confidence_level": "High",
        "processing_route": "Auto Processing",
    }

    sample_policy_result = {
        "policy_status": "Potentially Covered",
        "relevant_exclusions": [],
    }

    sample_validation_result = {
        "verification_status": "Validated",
        "readiness_score": 100.0,
        "missing_fields": [],
        "mismatches": [],
    }

    result = evaluate_final_claim_decision(
        readiness_result=sample_readiness_result,
        confidence_result=sample_confidence_result,
        policy_result=sample_policy_result,
        validation_result=sample_validation_result,
    )

    print("\n" + "=" * 60)
    print("CLAIMBRIDGE FINAL CLAIM DECISION")
    print("=" * 60)

    for key, value in result.items():

        print(f"\n{key}:")
        print(value)