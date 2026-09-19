import re
from typing import Dict, Any, List


# ---------------------------------------------------------
# Medical terminology
# ---------------------------------------------------------

MEDICAL_TERMS = [
    "admission",
    "discharge",
    "diagnosis",
    "treatment",
    "procedure",
    "surgery",
    "operation",
    "medical",
    "medicine",
    "medication",
    "tablet",
    "injection",
    "therapy",
    "consultation",
    "hospitalization",
    "hospital",
    "icu",
    "ward",
    "emergency",
    "anaesthesia",
    "anesthesia",
    "fracture",
    "infection",
    "fever",
    "pain",
    "blood",
    "scan",
    "x-ray",
    "mri",
    "ct scan",
    "ultrasound",
    "laboratory",
    "pathology",
]


# ---------------------------------------------------------
# Medical service / billing indicators
# ---------------------------------------------------------

MEDICAL_SERVICE_TERMS = {
    "x-ray": "Diagnostic Imaging",
    "x ray": "Diagnostic Imaging",
    "mri": "Diagnostic Imaging",
    "ct scan": "Diagnostic Imaging",
    "ultrasound": "Diagnostic Imaging",

    "laboratory": "Laboratory Investigation",
    "pathology": "Laboratory Investigation",

    "pharmacy": "Medication / Pharmacy",
    "medicine": "Medication / Pharmacy",
    "medication": "Medication / Pharmacy",
    "injection": "Medication / Injection",

    "oxygen": "Respiratory Support",

    "nursing care": "Nursing Care",

    "room accommodation": "Hospital Accommodation",

    "emergency room": "Emergency Care",

    "operating room": "Surgical Service",
    "operating room supplies": "Surgical Supplies",

    "recovery room": "Post-operative Care",

    "patient care unit": "Patient Care",

    "supplies": "Medical Supplies",
}


# ---------------------------------------------------------
# Text normalization
# ---------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Normalize OCR text for medical analysis.
    """

    if not text:
        return ""

    text = text.lower()

    text = text.replace("–", "-")
    text = text.replace("—", "-")

    return text


# ---------------------------------------------------------
# Medical terminology extraction
# ---------------------------------------------------------

def extract_medical_terms(text: str) -> List[str]:
    """
    Identify recognized medical terminology from OCR text.
    """

    normalized = normalize_text(text)

    detected_terms = []

    for term in MEDICAL_TERMS:
        if term in normalized:
            detected_terms.append(term)

    return sorted(set(detected_terms))


# ---------------------------------------------------------
# Diagnosis extraction
# ---------------------------------------------------------

def extract_diagnosis(text: str):
    """
    Extract diagnosis only when it is explicitly labelled.

    The system must not infer a diagnosis from symptoms,
    services, medicines, or billing items.
    """

    lines = text.splitlines()

    diagnosis_patterns = [
        r"diagnosis\s*[:\-]\s*(.+)",
        r"final diagnosis\s*[:\-]\s*(.+)",
        r"principal diagnosis\s*[:\-]\s*(.+)",
        r"medical diagnosis\s*[:\-]\s*(.+)",
    ]

    for line in lines:
        clean_line = line.strip()

        for pattern in diagnosis_patterns:
            match = re.search(
                pattern,
                clean_line,
                re.IGNORECASE
            )

            if match:
                value = match.group(1).strip()

                if value:
                    return value

    return None


# ---------------------------------------------------------
# Procedure extraction
# ---------------------------------------------------------

def extract_procedure(text: str):
    """
    Extract a formal procedure only when explicitly labelled.

    Terms such as 'operating room' are treated as service
    evidence, not automatically as a specific procedure.
    """

    lines = text.splitlines()

    procedure_patterns = [
        r"procedure\s*[:\-]\s*(.+)",
        r"medical procedure\s*[:\-]\s*(.+)",
        r"surgical procedure\s*[:\-]\s*(.+)",
        r"operation performed\s*[:\-]\s*(.+)",
    ]

    for line in lines:
        clean_line = line.strip()

        for pattern in procedure_patterns:
            match = re.search(
                pattern,
                clean_line,
                re.IGNORECASE
            )

            if match:
                value = match.group(1).strip()

                if value:
                    return value

    return None


# ---------------------------------------------------------
# Medical service extraction
# ---------------------------------------------------------

def extract_medical_services(
    text: str
) -> List[Dict[str, str]]:
    """
    Identify medical services explicitly present in the document.

    These are evidence of medical/hospital services and are
    intentionally kept separate from diagnosis and formal procedure.
    """

    normalized = normalize_text(text)

    services = []

    for term, category in MEDICAL_SERVICE_TERMS.items():

        if term in normalized:

            service = {
                "term": term,
                "category": category,
            }

            if service not in services:
                services.append(service)

    return services


# ---------------------------------------------------------
# Medical indicators
# ---------------------------------------------------------

def identify_medical_indicators(
    text: str,
    medical_services: List[Dict[str, str]]
) -> List[str]:
    """
    Identify broader medical indicators from the document.
    """

    normalized = normalize_text(text)

    indicators = []

    if "admission" in normalized:
        indicators.append(
            "Hospital Admission Evidence"
        )

    if "discharge" in normalized:
        indicators.append(
            "Hospital Discharge Evidence"
        )

    if "hospital" in normalized:
        indicators.append(
            "Hospitalization Evidence"
        )

    if "operating room" in normalized:
        indicators.append(
            "Surgical Service Evidence"
        )

    if "emergency room" in normalized:
        indicators.append(
            "Emergency Care Evidence"
        )

    if (
        "laboratory" in normalized
        or "pathology" in normalized
    ):
        indicators.append(
            "Diagnostic Investigation Evidence"
        )

    if (
        "x-ray" in normalized
        or "x ray" in normalized
        or "mri" in normalized
        or "ct scan" in normalized
        or "ultrasound" in normalized
    ):
        indicators.append(
            "Diagnostic Imaging Evidence"
        )

    if (
        "pharmacy" in normalized
        or "medicine" in normalized
        or "medication" in normalized
    ):
        indicators.append(
            "Medication Evidence"
        )

    if "nursing care" in normalized:
        indicators.append(
            "Nursing Care Evidence"
        )

    if medical_services:
        indicators.append(
            "Medical Billing Evidence"
        )

    return sorted(set(indicators))


# ---------------------------------------------------------
# Medical risk assessment
# ---------------------------------------------------------

def assess_medical_risk(
    text: str,
    medical_services: List[Dict[str, str]],
    diagnosis: str = None,
    procedure: str = None,
) -> int:
    """
    Provide a simple document-level medical risk score.

    This is NOT a clinical diagnosis or clinical severity score.

    It measures the amount of medical complexity/evidence
    identified in the document.
    """

    normalized = normalize_text(text)

    risk_score = 0

    # Hospitalization evidence
    if "admission" in normalized:
        risk_score += 5

    if "discharge" in normalized:
        risk_score += 5

    # Emergency care
    if "emergency room" in normalized:
        risk_score += 10

    # Surgical evidence
    if "operating room" in normalized:
        risk_score += 15

    # Diagnostic investigations
    if (
        "x-ray" in normalized
        or "x ray" in normalized
        or "mri" in normalized
        or "ct scan" in normalized
        or "ultrasound" in normalized
    ):
        risk_score += 10

    # Laboratory investigation
    if (
        "laboratory" in normalized
        or "pathology" in normalized
    ):
        risk_score += 5

    # Medication / pharmacy evidence
    if (
        "pharmacy" in normalized
        or "medication" in normalized
    ):
        risk_score += 5

    # Explicit diagnosis or procedure increases
    # information completeness, not clinical severity.
    if diagnosis:
        risk_score += 5

    if procedure:
        risk_score += 5

    return min(risk_score, 100)


# ---------------------------------------------------------
# Medical confidence
# ---------------------------------------------------------

def calculate_medical_confidence(
    text: str,
    medical_terms: List[str],
    medical_services: List[Dict[str, str]],
    diagnosis: str = None,
    procedure: str = None,
) -> float:
    """
    Calculate confidence based on the amount of explicit
    medical evidence detected in the document.
    """

    score = 0.0

    # OCR text exists
    if text.strip():
        score += 20.0

    # Recognized medical terminology exists
    if medical_terms:
        score += 20.0

    # Explicit medical services exist
    if medical_services:
        score += 30.0

    # Explicit diagnosis
    if diagnosis:
        score += 15.0

    # Explicit formal procedure
    if procedure:
        score += 15.0

    return round(
        min(score, 100.0),
        2
    )


# ---------------------------------------------------------
# Main Medical Intelligence function
# ---------------------------------------------------------

def analyze_medical_information(
    text: str,
    structured_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Analyze medical information from OCR text
    and structured extracted data.
    """

    structured_data = structured_data or {}

    # Normalize OCR text
    normalized_text = normalize_text(text)

    # Extract medical terminology
    medical_terms = extract_medical_terms(
        normalized_text
    )

    # Extract explicit diagnosis
    diagnosis = extract_diagnosis(
        text
    )

    # Extract explicit formal procedure
    procedure = extract_procedure(
        text
    )

    # Extract hospital/medical services
    medical_services = extract_medical_services(
        text
    )

    # Identify broader medical indicators
    medical_indicators = identify_medical_indicators(
        text,
        medical_services
    )

    # Calculate medical risk
    risk_score = assess_medical_risk(
        text,
        medical_services,
        diagnosis,
        procedure
    )

    # Calculate medical confidence
    confidence = calculate_medical_confidence(
        text,
        medical_terms,
        medical_services,
        diagnosis,
        procedure
    )

    # Determine analysis status
    if not text.strip():

        status = "Insufficient Data"

    elif (
        medical_services
        or diagnosis
        or procedure
    ):

        status = "Analyzed"

    else:

        status = "Limited Medical Evidence"

    # -----------------------------------------------------
    # Return result
    #
    # Both naming conventions are retained:
    #
    # 1. Existing pipeline-compatible keys
    # 2. Enhanced descriptive keys
    #
    # This prevents breaking existing ClaimBridge modules.
    # -----------------------------------------------------

    return {
        # Explicit medical information
        "diagnosis": diagnosis,
        "procedure": procedure,

        # Detailed medical evidence
        "medical_services": medical_services,
        "medical_terms": medical_terms,
        "medical_indicators": medical_indicators,

        # Existing pipeline-compatible keys
        "risk_score": risk_score,
        "confidence": confidence,
        "status": status,

        # Pipeline expects confidence_score as 0-1
        "confidence_score": confidence / 100.0,

        # Pipeline compatibility
        "processing_status": status,

        # Enhanced descriptive keys
        "medical_risk_score": risk_score,
        "medical_confidence": confidence,
        "medical_status": status,
    }