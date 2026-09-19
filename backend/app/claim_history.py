"""
ClaimBridge Claim History

Architecture position:

Final Claim Decision
        ↓
Claim History

The Claim History module creates an auditable record of the
claim-processing journey.

For the current development stage, records are kept in memory.
Database persistence will be connected later using the existing
ClaimHistory SQLAlchemy model.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List


# =========================================================
# HISTORY RECORD
# =========================================================

def create_claim_history_record(
    claim_id: str,
    decision_result: Dict[str, Any],
    readiness_result: Dict[str, Any],
    confidence_result: Dict[str, Any],
    policy_result: Dict[str, Any],
    validation_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create an auditable claim-processing history record.
    """

    return {
        "claim_id": claim_id,

        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),

        "processing_stage": "Final Claim Decision",

        "decision": decision_result.get(
            "decision",
            "Unknown",
        ),

        "processing_route": decision_result.get(
            "processing_route",
            "Unknown",
        ),

        "readiness_score": readiness_result.get(
            "readiness_score",
            0.0,
        ),

        "confidence_score": confidence_result.get(
            "confidence_score",
            0.0,
        ),

        "confidence_level": confidence_result.get(
            "confidence_level",
            "Unknown",
        ),

        "policy_status": policy_result.get(
            "policy_status",
            "Unknown",
        ),

        "validation_status": validation_result.get(
            "verification_status",
            "Unknown",
        ),

        "decision_reasons": decision_result.get(
            "decision_reasons",
            [],
        ),

        "processing_status": "Recorded",
    }


# =========================================================
# HISTORY SUMMARY
# =========================================================

def generate_history_summary(
    history_record: Dict[str, Any],
) -> str:
    """
    Generate a human-readable summary of the claim history event.
    """

    claim_id = history_record.get(
        "claim_id",
        "Unknown",
    )

    decision = history_record.get(
        "decision",
        "Unknown",
    )

    confidence = history_record.get(
        "confidence_score",
        0.0,
    )

    readiness = history_record.get(
        "readiness_score",
        0.0,
    )

    return (
        f"Claim {claim_id} completed the final processing stage "
        f"with decision '{decision}', "
        f"readiness score {readiness:.2f}%, "
        f"and confidence score {confidence:.2f}%."
    )


# =========================================================
# HISTORY VALIDATION
# =========================================================

def validate_history_record(
    history_record: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate that the minimum audit information exists.
    """

    required_fields = [
        "claim_id",
        "timestamp",
        "processing_stage",
        "decision",
        "processing_route",
        "readiness_score",
        "confidence_score",
        "policy_status",
        "validation_status",
    ]

    missing_fields: List[str] = []

    for field in required_fields:

        value = history_record.get(field)

        if value is None or value == "":

            missing_fields.append(field)

    if missing_fields:

        status = "Incomplete"

    else:

        status = "Valid"

    return {
        "status": status,
        "missing_fields": missing_fields,
    }


# =========================================================
# MAIN CLAIM HISTORY FUNCTION
# =========================================================

def record_claim_history(
    claim_id: str,
    decision_result: Dict[str, Any],
    readiness_result: Dict[str, Any],
    confidence_result: Dict[str, Any],
    policy_result: Dict[str, Any],
    validation_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Main Claim History entry point.

    Creates and validates an auditable history record.
    """

    history_record = create_claim_history_record(
        claim_id=claim_id,
        decision_result=decision_result,
        readiness_result=readiness_result,
        confidence_result=confidence_result,
        policy_result=policy_result,
        validation_result=validation_result,
    )

    validation = validate_history_record(
        history_record
    )

    summary = generate_history_summary(
        history_record
    )

    return {
        "history_record": history_record,

        "history_validation": validation,

        "history_summary": summary,

        "processing_status": "Recorded",
    }


# =========================================================
# MODULE TEST
# =========================================================

if __name__ == "__main__":

    sample_decision_result = {
        "decision": "Proceed with Automated Processing",
        "processing_route": "Auto Processing",
        "decision_reasons": [
            "Claim information passed structural validation.",
            "Relevant policy coverage evidence was identified.",
            "Claim readiness score: 96.30%.",
            "Evidence confidence score: 93.03%.",
        ],
    }

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
        "missing_fields": [],
        "mismatches": [],
    }

    result = record_claim_history(
        claim_id="CLM-TEST-001",
        decision_result=sample_decision_result,
        readiness_result=sample_readiness_result,
        confidence_result=sample_confidence_result,
        policy_result=sample_policy_result,
        validation_result=sample_validation_result,
    )

    print("\n" + "=" * 60)
    print("CLAIMBRIDGE CLAIM HISTORY")
    print("=" * 60)

    print("\nHistory Record:")

    for key, value in result[
        "history_record"
    ].items():

        print(f"{key}: {value}")

    print("\nHistory Validation:")
    print(
        result["history_validation"]
    )

    print("\nHistory Summary:")
    print(
        result["history_summary"]
    )

    print("\nProcessing Status:")
    print(
        result["processing_status"]
    )