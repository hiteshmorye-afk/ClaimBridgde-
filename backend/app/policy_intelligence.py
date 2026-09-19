import re
from typing import Any, Dict, List


"""
ClaimBridge Policy Intelligence

Architecture:

Information Extraction
        ↓
Structured Data + OCR Text
        ↓
Medical Intelligence
        ↓
Policy Intelligence (RAG)
        ↓
Validation Engine

This module provides claim-specific policy retrieval
and policy analysis using a lightweight RAG approach.
"""


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text: str) -> str:
    """Normalize text for policy analysis."""

    if not text:
        return ""

    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


# =========================================================
# TOKENIZATION
# =========================================================

def tokenize(text: str) -> List[str]:
    """Convert text into normalized searchable terms."""

    normalized_text = normalize_text(text).lower()

    return re.findall(
        r"\b[a-zA-Z0-9]+\b",
        normalized_text,
    )


# =========================================================
# POLICY CHUNKING
# =========================================================

def split_policy_into_chunks(
    policy_text: str,
    chunk_size: int = 500,
) -> List[str]:
    """
    Split policy text into manageable retrieval chunks.

    Section-based policies are preserved as complete sections.
    """

    normalized_text = normalize_text(policy_text)

    if not normalized_text:
        return []

    sections = re.split(
        r"(?=SECTION\s+\d+\s*-)",
        normalized_text,
        flags=re.IGNORECASE,
    )

    sections = [
        section.strip()
        for section in sections
        if section.strip()
    ]

    if len(sections) > 1:
        return sections

    # Fallback for policies without SECTION headings.
    words = normalized_text.split()

    chunks = []

    for i in range(0, len(words), chunk_size):

        chunk = " ".join(
            words[i:i + chunk_size]
        )

        if chunk:
            chunks.append(chunk)

    return chunks


# =========================================================
# POLICY SECTION CLASSIFICATION
# =========================================================

def classify_policy_section(text: str) -> str:
    """
    Identify the broad purpose of a policy section.
    """

    normalized = normalize_text(text).lower()

    if "hospitalization" in normalized:
        return "hospitalization"

    if (
        "surgical" in normalized
        or "surgery" in normalized
        or "procedure" in normalized
    ):
        return "surgical_treatment"

    if (
        "medical treatment" in normalized
        or "medically necessary" in normalized
        or "medical" in normalized
    ):
        return "medical_treatment"

    if (
        "exclusion" in normalized
        or "excluded" in normalized
        or "not covered" in normalized
    ):
        return "exclusion"

    if "waiting period" in normalized:
        return "waiting_period"

    if (
        "claim documentation" in normalized
        or "documentation" in normalized
        or "documents" in normalized
    ):
        return "documentation"

    return "general"


# =========================================================
# POLICY STOPWORDS
# =========================================================

POLICY_STOPWORDS = {
    "the",
    "and",
    "or",
    "of",
    "to",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "with",
    "for",
    "from",
    "on",
    "in",
    "at",
    "by",
    "this",
    "that",

    # Administrative OCR terms
    "patient",
    "name",
    "hospital",
    "date",
    "time",
    "room",
    "number",
    "no",
    "mr",
    "mrs",
    "amount",
    "due",
    "statement",
    "account",
    "charges",

    # Generic low-information terms
    "care",
    "unit",
    "common",
    "all",
    "information",
    "evidence",
}


# =========================================================
# POLICY SYNONYMS
# =========================================================

POLICY_SYNONYMS = {

    # Hospitalization
    "admitted": {
        "admission",
        "hospitalization",
        "hospitalized",
        "inpatient",
    },

    "admission": {
        "admitted",
        "hospitalization",
        "hospitalized",
        "inpatient",
    },

    "hospitalized": {
        "hospitalization",
        "admission",
        "admitted",
        "inpatient",
    },

    "inpatient": {
        "hospitalization",
        "admission",
        "hospitalized",
    },

    # Surgical treatment
    "surgery": {
        "surgical",
        "procedure",
        "operation",
    },

    "surgical": {
        "surgery",
        "procedure",
        "operation",
    },

    "operation": {
        "surgery",
        "surgical",
        "procedure",
    },

    "procedure": {
        "surgery",
        "surgical",
        "operation",
    },

    # Medical treatment
    "treatment": {
        "medical",
        "therapy",
        "care",
    },

    "medical": {
        "treatment",
        "therapy",
    },

    # Diagnostics
    "x": {
        "diagnostic",
    },

    "ray": {
        "diagnostic",
        "imaging",
    },

    "laboratory": {
        "medical",
        "treatment",
        "investigation",
        "diagnostic",
    },

    # Medication
    "pharmacy": {
        "medical",
        "treatment",
        "medication",
    },

    "medication": {
        "pharmacy",
        "medical",
        "treatment",
    },

    # Nursing
    "nursing": {
        "medical",
        "treatment",
        "care",
    },

    # Emergency
    "emergency": {
        "hospitalization",
        "medical",
        "treatment",
    },

    # Documentation
    "documentation": {
        "documents",
        "documentation",
        "supporting",
    },

    "documents": {
        "documentation",
        "supporting",
    },
}


# =========================================================
# CLAIM CONCEPT GROUPS
# =========================================================

CLAIM_CONCEPT_GROUPS = {
    "hospitalization": {
        "hospitalization",
        "hospitalized",
        "admission",
        "admitted",
        "inpatient",
        "discharge",
    },

    "medical_treatment": {
        "medical",
        "treatment",
        "therapy",
        "medicine",
        "medication",
        "pharmacy",
        "nursing",
        "oxygen",
        "emergency",
    },

    "diagnostic_services": {
        "x",
        "ray",
        "laboratory",
        "diagnostic",
        "imaging",
        "investigation",
        "scan",
        "mri",
        "ultrasound",
    },

    "surgical_treatment": {
        "surgery",
        "surgical",
        "procedure",
        "operation",
        "operating",
    },

    "claim_documentation": {
        "documentation",
        "documents",
        "hospital",
        "bill",
        "billing",
        "diagnosis",
        "treatment",
        "supporting",
        "assessment",
    },

    "expenses": {
        "expense",
        "expenses",
        "charges",
        "cost",
        "costs",
        "bill",
        "billing",
    },
}


# =========================================================
# QUERY TERM WEIGHTING
# =========================================================

def build_weighted_query_terms(
    query: str,
    claim_terms: List[str] | None = None,
) -> Dict[str, float]:
    """
    Build weighted terms for policy retrieval.

    Medical and claim-specific concepts receive higher
    importance than generic vocabulary.
    """

    terms: Dict[str, float] = {}

    raw_terms = tokenize(query)

    normalized_claim_terms = set(
        term.lower()
        for term in (claim_terms or [])
    )

    high_value_terms = {
        "hospitalization",
        "hospitalized",
        "admission",
        "admitted",
        "inpatient",
        "surgery",
        "surgical",
        "procedure",
        "operation",
        "treatment",
        "medical",
        "diagnosis",
        "emergency",
        "laboratory",
        "pharmacy",
        "medication",
        "oxygen",
        "documentation",
        "documents",
        "bill",
        "billing",
        "expenses",
        "imaging",
        "investigation",
    }

    for term in raw_terms:

        if term in POLICY_STOPWORDS:
            continue

        # Ignore pure numeric OCR tokens.
        if term.isdigit():
            continue

        if len(term) < 3:
            continue

        weight = 1.0

        if term in normalized_claim_terms:
            weight = 1.5

        if term in high_value_terms:
            weight = max(weight, 2.5)

        terms[term] = max(
            terms.get(term, 0.0),
            weight,
        )

    return terms


# =========================================================
# RELEVANCE SCORING
# =========================================================

def calculate_relevance_score(
    query: str,
    document: str,
    claim_terms: List[str] | None = None,
) -> float:
    """
    Calculate claim-aware relevance between a query
    and a policy section.

    Scoring considers:

    1. Direct keyword matches
    2. Synonym matches
    3. Claim-specific terminology
    4. Policy coverage concepts
    5. Independent concept matches

    The score is intentionally normalized against the
    meaningful query vocabulary rather than every token
    appearing in the OCR-derived claim representation.
    """

    query_terms = build_weighted_query_terms(
        query,
        claim_terms,
    )

    document_normalized = normalize_text(
        document
    ).lower()

    document_terms = set(
        tokenize(document)
    )

    if not query_terms or not document_terms:
        return 0.0

    matched_weight = 0.0
    total_weight = sum(
        query_terms.values()
    )

    matched_terms = set()

    # -----------------------------------------------------
    # Direct and synonym matches
    # -----------------------------------------------------

    for term, weight in query_terms.items():

        if term in document_terms:

            matched_weight += weight
            matched_terms.add(term)

            continue

        synonyms = POLICY_SYNONYMS.get(
            term,
            set(),
        )

        if synonyms.intersection(
            document_terms
        ):

            matched_weight += weight * 0.75
            matched_terms.add(term)

    # -----------------------------------------------------
    # Phrase-level policy concepts
    # -----------------------------------------------------

    phrase_bonus = 0.0

    strong_policy_phrases = {
        "medically necessary": 0.12,
        "hospitalization expenses": 0.12,
        "inpatient treatment": 0.12,
        "medical treatment": 0.10,
        "medical documentation": 0.10,
        "hospital bills": 0.10,
        "claim assessment": 0.08,
        "surgical procedures": 0.10,
    }

    for phrase, bonus in strong_policy_phrases.items():

        if phrase in document_normalized:

            # Only award the bonus when the query
            # contains at least one relevant word.
            phrase_tokens = set(
                tokenize(phrase)
            )

            if phrase_tokens.intersection(
                query_terms.keys()
            ):
                phrase_bonus += bonus

    # -----------------------------------------------------
    # Concept coverage bonus
    # -----------------------------------------------------

    concept_matches = 0

    query_term_set = set(
        query_terms.keys()
    )

    for concept_terms in CLAIM_CONCEPT_GROUPS.values():

        if (
            query_term_set.intersection(
                concept_terms
            )
            and document_terms.intersection(
                concept_terms
            )
        ):
            concept_matches += 1

    concept_bonus = min(
        concept_matches * 0.04,
        0.16,
    )

    # -----------------------------------------------------
    # Base score
    # -----------------------------------------------------

    if total_weight == 0:
        return 0.0

    base_score = (
        matched_weight / total_weight
    )

    score = (
        base_score
        + phrase_bonus
        + concept_bonus
    )

    return round(
        min(score, 1.0),
        4,
    )


# =========================================================
# POLICY RETRIEVAL
# =========================================================

def retrieve_relevant_policy_sections(
    query: str,
    policy_text: str,
    top_k: int = 3,
    claim_terms: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve the most relevant policy sections.
    """

    chunks = split_policy_into_chunks(
        policy_text
    )

    results = []

    for index, chunk in enumerate(chunks):

        score = calculate_relevance_score(
            query,
            chunk,
            claim_terms,
        )

        section_type = classify_policy_section(
            chunk
        )

        results.append(
            {
                "section_id": index + 1,
                "section_type": section_type,
                "text": chunk,
                "relevance_score": score,
            }
        )

    results.sort(
        key=lambda item: item["relevance_score"],
        reverse=True,
    )

    return results[:top_k]


# =========================================================
# POLICY TERMS
# =========================================================

COVERAGE_TERMS = [
    "covered",
    "coverage",
    "eligible",
    "hospitalization",
    "hospitalisation",
    "treatment",
    "surgery",
    "procedure",
    "medical expenses",
    "medically necessary",
]


EXCLUSION_TERMS = [
    "excluded",
    "exclusion",
    "not covered",
    "non-covered",
    "ineligible",
    "waiting period",
    "cosmetic",
    "experimental",
    "self-inflicted",
]


# =========================================================
# CLAIM-SPECIFIC TERMS
# =========================================================

def extract_claim_terms(
    ocr_text: str,
    extracted_information: Dict[str, Any] | None = None,
    medical_information: Dict[str, Any] | None = None,
) -> List[str]:
    """
    Extract meaningful claim terms.

    Administrative identifiers, dates, amounts and
    unrelated OCR vocabulary are excluded.
    """

    extracted_information = (
        extracted_information or {}
    )

    medical_information = (
        medical_information or {}
    )

    claim_text_parts: List[str] = []

    # -----------------------------------------------------
    # Medical services
    # -----------------------------------------------------

    medical_services = medical_information.get(
        "medical_services",
        [],
    )

    for service in medical_services:

        if isinstance(service, dict):

            term = service.get("term")
            category = service.get("category")

            if term:
                claim_text_parts.append(
                    str(term)
                )

            if category:
                claim_text_parts.append(
                    str(category)
                )

        elif service:

            claim_text_parts.append(
                str(service)
            )

    # -----------------------------------------------------
    # Medical indicators
    # -----------------------------------------------------

    medical_indicators = medical_information.get(
        "medical_indicators",
        [],
    )

    if medical_indicators:

        claim_text_parts.extend(
            str(item)
            for item in medical_indicators
        )

    # -----------------------------------------------------
    # Explicit diagnosis
    # -----------------------------------------------------

    diagnosis = medical_information.get(
        "diagnosis"
    )

    if diagnosis:
        claim_text_parts.append(
            str(diagnosis)
        )

    # -----------------------------------------------------
    # Explicit procedure
    # -----------------------------------------------------

    procedure = medical_information.get(
        "procedure"
    )

    if procedure:
        claim_text_parts.append(
            str(procedure)
        )

    # -----------------------------------------------------
    # Structured information
    # -----------------------------------------------------

    if extracted_information.get(
        "admission_date"
    ):
        claim_text_parts.append(
            "admission"
        )

    if extracted_information.get(
        "discharge_date"
    ):
        claim_text_parts.append(
            "discharge"
        )

    if extracted_information.get(
        "total_charges"
    ):
        claim_text_parts.extend(
            [
                "hospital",
                "expenses",
                "billing",
            ]
        )

    # -----------------------------------------------------
    # OCR medical terms
    # -----------------------------------------------------

    if ocr_text:

        ocr_tokens = tokenize(
            ocr_text
        )

        relevant_ocr_terms = {
            "oxygen",
            "x",
            "ray",
            "laboratory",
            "pharmacy",
            "supplies",
            "nursing",
            "emergency",
            "operating",
            "recovery",
            "medical",
            "hospital",
            "admission",
            "discharge",
            "surgery",
            "surgical",
            "treatment",
            "procedure",
            "diagnosis",
            "medicine",
            "medication",
            "billing",
            "expenses",
        }

        for token in ocr_tokens:

            if token in POLICY_STOPWORDS:
                continue

            if token in relevant_ocr_terms:
                claim_text_parts.append(
                    token
                )

    # -----------------------------------------------------
    # Normalize final terms
    # -----------------------------------------------------

    combined_text = " ".join(
        claim_text_parts
    )

    final_terms = []

    for token in tokenize(
        combined_text
    ):

        if token in POLICY_STOPWORDS:
            continue

        if token.isdigit():
            continue

        if len(token) < 3:
            continue

        final_terms.append(
            token
        )

    return sorted(
        set(final_terms)
    )


# =========================================================
# EXCLUSION RELEVANCE
# =========================================================

def exclusion_applies_to_claim(
    exclusion_term: str,
    claim_terms: List[str],
    policy_section: str,
) -> bool:
    """
    Determine whether a policy exclusion has a direct
    relationship with the current claim.

    This remains intentionally conservative.
    """

    claim_term_set = set(
        token.lower()
        for token in claim_terms
    )

    # -----------------------------------------------------
    # Cosmetic exclusion
    # -----------------------------------------------------

    if exclusion_term == "cosmetic":

        cosmetic_related_terms = {
            "cosmetic",
            "plastic",
            "beauty",
            "aesthetic",
        }

        return bool(
            cosmetic_related_terms.intersection(
                claim_term_set
            )
        )

    # -----------------------------------------------------
    # Experimental exclusion
    # -----------------------------------------------------

    if exclusion_term == "experimental":

        experimental_related_terms = {
            "experimental",
            "trial",
            "investigational",
        }

        return bool(
            experimental_related_terms.intersection(
                claim_term_set
            )
        )

    # -----------------------------------------------------
    # Self-inflicted exclusion
    # -----------------------------------------------------

    if exclusion_term == "self-inflicted":

        self_inflicted_terms = {
            "self-inflicted",
            "intentional",
            "injury",
            "suicide",
            "self",
            "harm",
        }

        return bool(
            self_inflicted_terms.intersection(
                claim_term_set
            )
        )

    # -----------------------------------------------------
    # Waiting period
    # -----------------------------------------------------

    if exclusion_term == "waiting period":

        waiting_related_terms = {
            "waiting",
            "pre-existing",
            "preexisting",
        }

        return bool(
            waiting_related_terms.intersection(
                claim_term_set
            )
        )

    # -----------------------------------------------------
    # Generic exclusion
    # -----------------------------------------------------

    exclusion_words = set(
        tokenize(exclusion_term)
    )

    section_terms = set(
        tokenize(policy_section)
    )

    return bool(
        exclusion_words.intersection(
            claim_term_set
        ).intersection(
            section_terms
        )
    )


# =========================================================
# POLICY INDICATORS
# =========================================================

def detect_policy_indicators(
    policy_sections: List[Dict[str, Any]],
    claim_terms: List[str],
) -> Dict[str, List[str]]:
    """
    Detect coverage and exclusion indicators.
    """

    coverage_indicators = []
    exclusion_indicators = []
    relevant_exclusions = []

    for section in policy_sections:

        text = section["text"]
        text_lower = text.lower()

        # -------------------------------------------------
        # Coverage indicators
        # -------------------------------------------------

        for term in COVERAGE_TERMS:

            if term in text_lower:

                if term not in coverage_indicators:
                    coverage_indicators.append(
                        term
                    )

        # -------------------------------------------------
        # Exclusion indicators
        # -------------------------------------------------

        for term in EXCLUSION_TERMS:

            if term in text_lower:

                if term not in exclusion_indicators:
                    exclusion_indicators.append(
                        term
                    )

                if exclusion_applies_to_claim(
                    term,
                    claim_terms,
                    text_lower,
                ):

                    if term not in relevant_exclusions:
                        relevant_exclusions.append(
                            term
                        )

    return {
        "coverage_indicators": coverage_indicators,
        "exclusion_indicators": exclusion_indicators,
        "relevant_exclusions": relevant_exclusions,
    }


# =========================================================
# CLAIM POLICY QUERY
# =========================================================

def build_claim_policy_query(
    ocr_text: str,
    extracted_information: Dict[str, Any] | None = None,
    medical_information: Dict[str, Any] | None = None,
) -> str:
    """
    Build a focused policy retrieval query.

    The query represents the claim semantically instead
    of sending the complete OCR document.
    """

    extracted_information = (
        extracted_information or {}
    )

    medical_information = (
        medical_information or {}
    )

    query_parts = []

    # -----------------------------------------------------
    # Core claim concepts
    # -----------------------------------------------------

    query_parts.extend(
        [
            "hospitalization",
            "medical treatment",
            "hospital bill",
            "claim documentation",
        ]
    )

    # -----------------------------------------------------
    # Medical services
    # -----------------------------------------------------

    medical_services = medical_information.get(
        "medical_services",
        [],
    )

    for service in medical_services:

        if isinstance(service, dict):

            term = service.get("term")
            category = service.get("category")

            if term:
                query_parts.append(
                    str(term)
                )

            if category:
                query_parts.append(
                    str(category)
                )

    # -----------------------------------------------------
    # Medical indicators
    # -----------------------------------------------------

    medical_indicators = medical_information.get(
        "medical_indicators",
        [],
    )

    query_parts.extend(
        str(item)
        for item in medical_indicators
    )

    # -----------------------------------------------------
    # Explicit diagnosis
    # -----------------------------------------------------

    diagnosis = medical_information.get(
        "diagnosis"
    )

    if diagnosis:
        query_parts.append(
            f"diagnosis {diagnosis}"
        )

    # -----------------------------------------------------
    # Explicit procedure
    # -----------------------------------------------------

    procedure = medical_information.get(
        "procedure"
    )

    if procedure:
        query_parts.append(
            f"procedure {procedure}"
        )

    # -----------------------------------------------------
    # Structured claim information
    # -----------------------------------------------------

    if extracted_information.get(
        "admission_date"
    ):
        query_parts.append(
            "admission"
        )

    if extracted_information.get(
        "discharge_date"
    ):
        query_parts.append(
            "discharge"
        )

    if extracted_information.get(
        "total_charges"
    ):
        query_parts.append(
            "hospital expenses"
        )

    return normalize_text(
        " ".join(query_parts)
    )


# =========================================================
# POLICY COVERAGE ANALYSIS
# =========================================================

def analyze_policy_coverage(
    policy_sections: List[Dict[str, Any]],
    claim_terms: List[str],
) -> Dict[str, Any]:
    """
    Analyse policy sections against the specific claim.
    """

    indicators = detect_policy_indicators(
        policy_sections,
        claim_terms,
    )

    coverage_indicators = indicators[
        "coverage_indicators"
    ]

    exclusion_indicators = indicators[
        "exclusion_indicators"
    ]

    relevant_exclusions = indicators[
        "relevant_exclusions"
    ]

    # -----------------------------------------------------
    # Decision logic
    # -----------------------------------------------------

    if relevant_exclusions:

        policy_status = (
            "Relevant Exclusion Detected"
        )

    elif coverage_indicators:

        policy_status = (
            "Potentially Covered"
        )

    else:

        policy_status = (
            "Insufficient Policy Evidence"
        )

    return {
        "policy_status": policy_status,
        "coverage_indicators": coverage_indicators,
        "exclusion_indicators": exclusion_indicators,
        "relevant_exclusions": relevant_exclusions,
    }


# =========================================================
# MAIN POLICY INTELLIGENCE
# =========================================================

def analyze_policy_information(
    policy_text: str,
    ocr_text: str,
    extracted_information: Dict[str, Any] | None = None,
    medical_information: Dict[str, Any] | None = None,
    top_k: int = 3,
) -> Dict[str, Any]:
    """
    Main Policy Intelligence entry point.
    """

    extracted_information = (
        extracted_information or {}
    )

    medical_information = (
        medical_information or {}
    )

    # -----------------------------------------------------
    # Build focused claim query
    # -----------------------------------------------------

    query = build_claim_policy_query(
        ocr_text,
        extracted_information,
        medical_information,
    )

    # -----------------------------------------------------
    # Extract claim-specific terms
    # -----------------------------------------------------

    claim_terms = extract_claim_terms(
        ocr_text,
        extracted_information,
        medical_information,
    )

    # -----------------------------------------------------
    # Missing policy
    # -----------------------------------------------------

    if not policy_text:

        return {
            "policy_status": (
                "Insufficient Policy Evidence"
            ),
            "query": query,
            "claim_terms": claim_terms,
            "retrieved_sections": [],
            "coverage_indicators": [],
            "exclusion_indicators": [],
            "relevant_exclusions": [],
            "retrieval_confidence": 0.0,
            "processing_status": "Needs Review",
        }

    # -----------------------------------------------------
    # Retrieve relevant policy sections
    # -----------------------------------------------------

    retrieved_sections = (
        retrieve_relevant_policy_sections(
            query=query,
            policy_text=policy_text,
            top_k=top_k,
            claim_terms=claim_terms,
        )
    )

    # -----------------------------------------------------
    # Analyse policy against claim
    # -----------------------------------------------------

    policy_analysis = analyze_policy_coverage(
        retrieved_sections,
        claim_terms,
    )

    # -----------------------------------------------------
    # Retrieval confidence
    #
    # Strongest section = primary evidence.
    # Average of positive sections = supporting evidence.
    # -----------------------------------------------------

    if retrieved_sections:

        top_score = max(
            section["relevance_score"]
            for section in retrieved_sections
        )

        positive_scores = [
            section["relevance_score"]
            for section in retrieved_sections
            if section["relevance_score"] > 0
        ]

        if positive_scores:

            average_positive_score = (
                sum(positive_scores)
                / len(positive_scores)
            )

            retrieval_confidence = (
                top_score * 0.7
                + average_positive_score * 0.3
            )

        else:

            retrieval_confidence = 0.0

    else:

        retrieval_confidence = 0.0

    retrieval_confidence = round(
        min(retrieval_confidence, 1.0),
        4,
    )

    # -----------------------------------------------------
    # Processing status
    # -----------------------------------------------------

    if retrieval_confidence == 0:

        processing_status = "Needs Review"

    else:

        processing_status = "Analyzed"

    return {
        "policy_status": policy_analysis[
            "policy_status"
        ],

        "query": query,

        "claim_terms": claim_terms,

        "retrieved_sections": retrieved_sections,

        "coverage_indicators": policy_analysis[
            "coverage_indicators"
        ],

        "exclusion_indicators": policy_analysis[
            "exclusion_indicators"
        ],

        "relevant_exclusions": policy_analysis[
            "relevant_exclusions"
        ],

        "retrieval_confidence": (
            retrieval_confidence
        ),

        "processing_status": processing_status,
    }


# =========================================================
# MODULE TEST
# =========================================================

if __name__ == "__main__":

    sample_policy = """
    SECTION 1 - HOSPITALIZATION COVERAGE

    Hospitalization expenses are covered when the insured person
    requires medically necessary inpatient treatment.

    SECTION 2 - SURGICAL TREATMENT

    Medically necessary surgical procedures are covered subject
    to the terms and conditions of the policy.

    SECTION 3 - MEDICAL TREATMENT

    Reasonable and medically necessary medical treatment is covered
    when supported by appropriate medical documentation.

    SECTION 4 - EXCLUSIONS

    Cosmetic surgery is excluded from coverage.

    Experimental treatment is not covered under this policy.

    Self-inflicted injuries are excluded from coverage.

    SECTION 5 - WAITING PERIOD

    Certain medical conditions may be subject to an applicable
    waiting period before coverage becomes effective.

    SECTION 6 - CLAIM DOCUMENTATION

    The claimant must provide appropriate medical documents,
    hospital bills, diagnosis information, treatment information,
    and other supporting documentation required for claim assessment.
    """

    sample_ocr = """
    Patient admitted for hospitalization.
    Hospital bill.
    X-RAY
    LABORATORY
    PHARMACY
    OPERATING ROOM
    NURSING CARE
    """

    sample_extracted_information = {
        "patient_name": "John Doe",
        "hospital_name": "ABC Hospital",
        "admission_date": "16.05.2019",
        "discharge_date": "19.05.2019",
        "total_charges": 75000,
    }

    sample_medical_information = {
        "diagnosis": None,
        "procedure": None,
        "medical_services": [
            {
                "term": "x-ray",
                "category": "Diagnostic Imaging",
            },
            {
                "term": "laboratory",
                "category": "Laboratory Investigation",
            },
            {
                "term": "pharmacy",
                "category": "Medication / Pharmacy",
            },
            {
                "term": "operating room",
                "category": "Surgical Service",
            },
        ],
        "medical_indicators": [
            "Hospital Admission Evidence",
            "Medical Billing Evidence",
            "Diagnostic Imaging Evidence",
        ],
    }

    result = analyze_policy_information(
        policy_text=sample_policy,
        ocr_text=sample_ocr,
        extracted_information=sample_extracted_information,
        medical_information=sample_medical_information,
    )

    print("\n" + "=" * 60)
    print("CLAIMBRIDGE POLICY INTELLIGENCE")
    print("=" * 60)

    for key, value in result.items():

        print(f"\n{key}:")
        print(value)