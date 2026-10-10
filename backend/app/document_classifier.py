"""
ClaimBridge Document Classifier

Automatic classification of medical and insurance claim documents
using extracted text, weighted keyword patterns, and structural cues.

Supported Categories:
- hospital_bill
- discharge_summary
- prescription
- lab_report
- medical_report
- insurance_policy
- unknown
"""

import re
from typing import Any, Dict, List, Optional


# =========================================================
# DOCUMENT TYPE EVIDENCE RULES (WEIGHTED)
# =========================================================

DOCUMENT_EVIDENCE: Dict[str, Dict[str, Any]] = {
    "hospital_bill": {
        "strong": [
            r"\btax\s+invoice\b",
            r"\bhospital\s+bill\b",
            r"\bstatement\s+of\s+account\b",
            r"\binterim\s+bill\b",
            r"\bfinal\s+bill\b",
            r"\bbilling\s+summary\b",
            r"\binvoice\s+no\b",
            r"\bbill\s+no\b",
            r"\bamount\s+due\b",
            r"\bamount\s+payable\b",
            r"\btotal\s+charges\b",
        ],
        "medium": [
            r"\broom\s+(?:rent|charges|accommodation)\b",
            r"\bpharmacy\s+charges\b",
            r"\bconsultation\s+fee\b",
            r"\bnursing\s+charges\b",
            r"\blaboratory\s+charges\b",
            r"\bot\s+charges\b",
            r"\boperating\s+room\b",
            r"\bpatient\s+deposit\b",
            r"\bdiscount\b",
            r"\bgst\b",
            r"\btax\b",
            r"\bsubtotal\b",
            r"\badvance\s+paid\b",
            r"\bbalance\s+due\b",
        ],
        "standard": [
            r"\binvoice\b",
            r"\bbill\b",
            r"\bcharges\b",
            r"\bpayment\b",
            r"\brate\b",
            r"\bqty\b",
            r"\bquantity\b",
        ],
    },
    "discharge_summary": {
        "strong": [
            r"\bdischarge\s+summary\b",
            r"\bdischarge\s+card\b",
            r"\bclinical\s+discharge\s+summary\b",
            r"\bdischarge\s+diagnosis\b",
            r"\bcondition\s+at\s+discharge\b",
            r"\badvice\s+on\s+discharge\b",
            r"\bhospital\s+course\b",
            r"\bcourse\s+in\s+the\s+hospital\b",
        ],
        "medium": [
            r"\bdate\s+of\s+admission\b",
            r"\bdate\s+of\s+discharge\b",
            r"\bhistory\s+of\s+present\s+illness\b",
            r"\bclinical\s+summary\b",
            r"\btreatment\s+given\b",
            r"\boperative\s+findings\b",
            r"\bprocedure\s+performed\b",
            r"\bphysical\s+findings\b",
            r"\bfollow\s*-\s*up\s+instructions\b",
            r"\battending\s+physician\b",
            r"\bconsultant\s+in\s*charge\b",
        ],
        "standard": [
            r"\badmission\b",
            r"\bdischarge\b",
            r"\bpatient\s+condition\b",
            r"\bvitals\b",
            r"\bmedications\s+advised\b",
        ],
    },
    "prescription": {
        "strong": [
            r"\bprescription\b",
            r"\brx\b",
            r"\bprescribed\s+medications\b",
            r"\bmedical\s+prescription\b",
            r"\bdoctor['’]?s\s+prescription\b",
        ],
        "medium": [
            r"\btab(?:let)?\.?\b",
            r"\bcap(?:sule)?\.?\b",
            r"\bsyp(?:rup)?\.?\b",
            r"\binj(?:ection)?\.?\b",
            r"\bdosage\b",
            r"\bdose\b",
            r"\bfrequency\b",
            r"\bduration\b",
            r"\btake\s+(?:once|twice|thrice|\d+\s+times)\b",
            r"\bafter\s+(?:food|meals)\b",
            r"\bbefore\s+(?:food|meals)\b",
            r"\b1-0-1\b",
            r"\b1-1-1\b",
            r"\b0-0-1\b",
            r"\b1-0-0\b",
            r"\bstat\b",
            r"\bsos\b",
        ],
        "standard": [
            r"\bmedicine\b",
            r"\bmg\b",
            r"\bml\b",
            r"\bpharmacy\b",
            r"\brefill\b",
        ],
    },
    "lab_report": {
        "strong": [
            r"\blaboratory\s+report\b",
            r"\blab\s+report\b",
            r"\bpathology\s+report\b",
            r"\bdiagnostic\s+report\b",
            r"\btest\s+results?\b",
            r"\btest\s+report\b",
            r"\bclinical\s+laboratory\b",
        ],
        "medium": [
            r"\breference\s+(?:range|interval|values)\b",
            r"\bobserved\s+value\b",
            r"\bunits\b",
            r"\bhemoglobin\b",
            r"\bcomplete\s+blood\s+count\b",
            r"\bcbc\b",
            r"\bwbc\b",
            r"\brbc\b",
            r"\bplatelets\b",
            r"\bserum\s+creatinine\b",
            r"\bblood\s+glucose\b",
            r"\burine\s+routine\b",
            r"\blipid\s+profile\b",
            r"\blft\b",
            r"\bkft\b",
            r"\bmethod\b",
            r"\bspecimen\b",
        ],
        "standard": [
            r"\bnormal\b",
            r"\babnormal\b",
            r"\bhigh\b",
            r"\blow\b",
            r"\bpositive\b",
            r"\bnegative\b",
        ],
    },
    "medical_report": {
        "strong": [
            r"\bmedical\s+report\b",
            r"\bclinical\s+report\b",
            r"\bmedical\s+certificate\b",
            r"\bconsultation\s+report\b",
            r"\bdoctor['’]?s\s+report\b",
        ],
        "medium": [
            r"\bclinical\s+findings\b",
            r"\bexamination\s+findings\b",
            r"\bimpression\b",
            r"\bprovisional\s+diagnosis\b",
            r"\bfinal\s+diagnosis\b",
            r"\bchief\s+complaints?\b",
            r"\bhistory\s+of\s+presenting\s+illness\b",
            r"\brecommendations?\b",
            r"\bopinion\b",
        ],
        "standard": [
            r"\bdiagnosis\b",
            r"\bexamination\b",
            r"\bfindings\b",
            r"\bclinical\b",
        ],
    },
    "insurance_policy": {
        "strong": [
            r"\binsurance\s+policy\b",
            r"\bpolicy\s+schedule\b",
            r"\bpolicy\s+document\b",
            r"\bcertificate\s+of\s+insurance\b",
            r"\bhealth\s+insurance\s+policy\b",
            r"\bpolicy\s+wording\b",
        ],
        "medium": [
            r"\bpolicy\s+number\b",
            r"\bpolicy\s+period\b",
            r"\bperiod\s+of\s+insurance\b",
            r"\bsum\s+insured\b",
            r"\bcumulative\s+bonus\b",
            r"\bdeductible\b",
            r"\bco-?payment\b",
            r"\bwaiting\s+period\b",
            r"\bpermanent\s+exclusions\b",
            r"\broom\s+rent\s+limit\b",
            r"\binsured\s+person\b",
            r"\bproposer\b",
            r"\bpremium\b",
            r"\btpa\b",
        ],
        "standard": [
            r"\bcoverage\b",
            r"\binsurer\b",
            r"\bclaim\s+procedure\b",
            r"\bterms\s+and\s+conditions\b",
        ],
    },
}


# =========================================================
# CATEGORY NORMALIZATION
# =========================================================

CATEGORY_NORMALIZATION_MAP = {
    "hospital bill": "hospital_bill",
    "hospital_bill": "hospital_bill",
    "bill": "hospital_bill",
    "invoice": "hospital_bill",
    "discharge summary": "discharge_summary",
    "discharge_summary": "discharge_summary",
    "discharge card": "discharge_summary",
    "prescription": "prescription",
    "rx": "prescription",
    "lab report": "lab_report",
    "lab_report": "lab_report",
    "laboratory report": "lab_report",
    "investigation report": "lab_report",
    "medical report": "medical_report",
    "medical_report": "medical_report",
    "insurance policy": "insurance_policy",
    "insurance_policy": "insurance_policy",
    "insurance card": "insurance_policy",
    "policy": "insurance_policy",
    "unknown": "unknown",
}


def normalize_category_name(category: Optional[str]) -> str:
    """Normalize user or UI category name into standard backend type."""
    if not category:
        return "unknown"
    cleaned = category.strip().lower()
    return CATEGORY_NORMALIZATION_MAP.get(cleaned, cleaned.replace(" ", "_"))


# =========================================================
# DOCUMENT CLASSIFICATION
# =========================================================

def classify_text_segment(text: str) -> Dict[str, Any]:
    """
    Score and classify a specific segment of text (e.g. a page or document).
    """
    if not text or not text.strip():
        return {
            "document_type": "unknown",
            "confidence": 0.0,
            "matched_keywords": [],
            "scores": {},
        }

    text_lower = text.lower()
    scores: Dict[str, float] = {}
    matched_by_type: Dict[str, List[str]] = {}

    for doc_type, rules in DOCUMENT_EVIDENCE.items():
        matched: List[str] = []
        score = 0.0

        # Strong matches: 3.0 points each
        for pattern in rules.get("strong", []):
            if re.search(pattern, text_lower):
                clean_term = pattern.replace(r"\b", "").replace(r"\s+", " ").replace("\\", "")
                matched.append(clean_term)
                score += 3.0

        # Medium matches: 1.5 points each
        for pattern in rules.get("medium", []):
            if re.search(pattern, text_lower):
                clean_term = pattern.replace(r"\b", "").replace(r"\s+", " ").replace("\\", "")
                matched.append(clean_term)
                score += 1.5

        # Standard matches: 0.5 points each
        for pattern in rules.get("standard", []):
            if re.search(pattern, text_lower):
                clean_term = pattern.replace(r"\b", "").replace(r"\s+", " ").replace("\\", "")
                matched.append(clean_term)
                score += 0.5

        scores[doc_type] = round(score, 2)
        matched_by_type[doc_type] = matched

    # Find the highest-scoring document type
    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]
    best_matched = matched_by_type[best_type]

    # If best score is below minimum threshold (e.g., 2.0), consider unknown
    if best_score < 2.0:
        return {
            "document_type": "unknown",
            "confidence": 0.0,
            "matched_keywords": [],
            "scores": scores,
        }

    # Calibrate confidence based on score and evidence count
    # 2.0 pts -> ~0.65, 5.0 pts -> ~0.85, 8.0+ pts -> 0.98
    confidence = min(0.60 + (best_score / 15.0) * 0.38, 0.98)

    return {
        "document_type": best_type,
        "confidence": round(confidence, 2),
        "matched_keywords": best_matched,
        "scores": scores,
    }


def classify_document(
    text: str,
    pages_text: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Classifies a medical/insurance document using OCR text and evidence cues.

    Supports document-level classification and optional page-level classification
    when multi-page texts are provided.
    """
    overall = classify_text_segment(text)

    page_results = []
    if pages_text and len(pages_text) > 1:
        for idx, page_t in enumerate(pages_text, start=1):
            p_class = classify_text_segment(page_t)
            page_results.append({
                "page": idx,
                "document_type": p_class["document_type"],
                "confidence": p_class["confidence"],
                "matched_keywords": p_class["matched_keywords"],
            })

    result = {
        "document_type": overall["document_type"],
        "confidence": overall["confidence"],
        "matched_keywords": overall["matched_keywords"],
        "category_scores": overall["scores"],
    }

    if page_results:
        result["page_classifications"] = page_results

    return result


if __name__ == "__main__":
    sample_text = """
    Chong Hua Hospital
    TAX INVOICE
    Invoice No: INV-2026-9921
    Billing date: 19.05.2019
    Room Charges: 45,000.00
    Pharmacy Charges: 32,000.00
    Total charges: 184,000.00
    Amount payable: 184,000.00
    """

    res = classify_document(sample_text)
    print("\nDocument Classification Result:")
    print("--------------------------------")
    print(f"Document Type : {res['document_type']}")
    print(f"Confidence    : {res['confidence'] * 100:.2f}%")
    print(f"Evidence      : {res['matched_keywords']}")