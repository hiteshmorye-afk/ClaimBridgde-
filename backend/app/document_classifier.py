import re


DOCUMENT_TYPES = {
    "hospital_bill": [
        "tax invoice",
        "total charges",
        "amount payable",
        "billing date",
        "charges before",
        "hospital bill",
        "invoice",
    ],
    "discharge_summary": [
        "discharge summary",
        "discharge diagnosis",
        "discharge date",
        "hospital course",
        "condition at discharge",
    ],
    "prescription": [
        "prescription",
        "dosage",
        "tablet",
        "capsule",
        "medicine",
        "take once",
        "take twice",
    ],
    "lab_report": [
        "laboratory",
        "lab report",
        "test result",
        "reference range",
        "hemoglobin",
        "blood test",
        "pathology",
    ],
    "medical_report": [
        "medical report",
        "diagnosis",
        "clinical findings",
        "examination",
        "impression",
    ],
    "insurance_policy": [
        "policy number",
        "policy period",
        "sum insured",
        "coverage",
        "insurance policy",
        "premium",
    ],
}


def classify_document(text: str):
    """
    Classifies a medical/insurance document
    using OCR text and keyword evidence.
    """

    if not text or not text.strip():
        return {
            "document_type": "unknown",
            "confidence": 0.0,
            "matched_keywords": [],
        }

    text_lower = text.lower()

    scores = {}

    for document_type, keywords in DOCUMENT_TYPES.items():
        matched_keywords = []

        for keyword in keywords:
            if keyword.lower() in text_lower:
                matched_keywords.append(keyword)

        scores[document_type] = matched_keywords

    best_type = max(
        scores,
        key=lambda document_type: len(scores[document_type])
    )

    matched = scores[best_type]

    if not matched:
        return {
            "document_type": "unknown",
            "confidence": 0.0,
            "matched_keywords": [],
        }

    confidence = min(
        0.60 + (len(matched) - 1) * 0.10,
        0.98
    )

    return {
        "document_type": best_type,
        "confidence": round(confidence, 2),
        "matched_keywords": matched,
    }


if __name__ == "__main__":

    sample_text = """
    KK Women's and Children's Hospital
    TAX INVOICE
    Billing date
    Total charges
    Amount payable
    """

    result = classify_document(sample_text)

    print("\nDocument Classification Result")
    print("--------------------------------")
    print(f"Document Type : {result['document_type']}")
    print(f"Confidence    : {result['confidence'] * 100:.2f}%")
    print(f"Evidence      : {result['matched_keywords']}")