"""
ClaimBridge Multi-Document Claim Processor

Coordinates processing across all documents associated with an insurance claim,
aggregates document-level AI extractions, and performs cross-document
consistency reconciliation and contradiction detection.
"""

import os
from typing import Any, Dict, List, Optional
from .pipeline import process_document
from .validation_engine import validate_cross_document_consistency


def process_claim(
    document_paths: List[str],
    claim_id: str = "CLM-TEST-001",
    policy_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process multiple documents belonging to one insurance claim.
    Each document is processed through the 11-stage AI pipeline,
    followed by cross-document reconciliation.
    """
    if policy_path is None:
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        policy_path = os.path.join(backend_dir, "policies", "sample_policy.txt")

    print("\n" + "=" * 70)
    print(f"CLAIMBRIDGE MULTI-DOCUMENT PROCESSING — CLAIM: {claim_id}")
    print("=" * 70)

    document_results = []
    extracted_records = []

    for index, doc_path in enumerate(document_paths, start=1):
        print("\n" + "-" * 70)
        print(f"PROCESSING DOCUMENT {index}/{len(document_paths)}: {doc_path}")
        print("-" * 70)

        try:
            doc_result = process_document(
                image_path=doc_path,
                policy_path=policy_path,
                claim_id=claim_id,
            )
            document_results.append({
                "file": doc_path,
                "status": "success",
                "result": doc_result,
            })

            extracted_info = doc_result.get("extracted_information", {})
            if extracted_info:
                extracted_records.append(extracted_info)

        except Exception as exc:
            print(f"ERROR processing {doc_path}: {exc}")
            document_results.append({
                "file": doc_path,
                "status": "failed",
                "error": str(exc),
            })

    # =========================================================
    # CROSS-DOCUMENT RECONCILIATION
    # =========================================================
    print("\n" + "=" * 70)
    print("RUNNING CROSS-DOCUMENT RECONCILIATION")
    print("=" * 70)

    cross_reconciliation = validate_cross_document_consistency(extracted_records)

    print(f"Reconciliation Status: {cross_reconciliation['cross_document_status']}")
    print(f"Cross Mismatches     : {cross_reconciliation['mismatches']}")
    print(f"Missing Documents    : {cross_reconciliation['missing_documents']}")

    # Determine overall status
    has_failed = any(r.get("status") == "failed" for r in document_results)
    if cross_reconciliation["mismatches"]:
        overall_status = "Discrepancy Detected"
    elif has_failed:
        overall_status = "Partial Failure"
    else:
        overall_status = "Completed"

    summary = {
        "claim_id": claim_id,
        "total_documents": len(document_paths),
        "successful_documents": sum(1 for r in document_results if r.get("status") == "success"),
        "failed_documents": sum(1 for r in document_results if r.get("status") == "failed"),
        "overall_status": overall_status,
        "document_results": document_results,
        "cross_document_validation": cross_reconciliation,
    }

    print("\n" + "=" * 70)
    print("CLAIM MULTI-DOCUMENT PROCESSING COMPLETED")
    print("=" * 70)

    return summary


if __name__ == "__main__":
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_docs = [
        os.path.join(backend_dir, "test_images", "sample_bill.png"),
    ]
    if os.path.exists(test_docs[0]):
        process_claim(test_docs)
    else:
        print("Sample test document not found; skipping self-test.")