"""
ClaimBridge Biomedical NLP & NER Engine
=======================================
Provides clinical entity extraction (Diseases, Symptoms, Medications, Procedures, Diagnostic Tests)
with text-span tracking, validated ICD-10 cross-referencing, and graceful model degradation.

Key Design Principles:
1. Architecture Separation: Base BioBERT (dmis-lab/biobert-v1.1) is an encoder; task-specific NER
   requires a token classification checkpoint (e.g. d4data/biomedical-ner-all or alvaroalon2/biobert_diseases_ner).
2. Service Interface: Underlying neural vs. rule-based clinical backends are isolated behind
   `BaseBiomedicalNERAdapter`.
3. Validated Terminology Mapping: ICD-10 codes are ONLY assigned when confirmed by an authoritative,
   pre-validated catalogue. Never fabricated or guessed.
4. Span Integrity: Extracted entities retain start, end, exact span text, and normalized form.
5. Graceful Degradation: Handles long documents, uninstalled torch/transformers dependencies,
   missing model weights, and empty inputs cleanly.
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


BIOMEDICAL_DISCLAIMER = (
    "Biomedical entity extraction for claim documentation review. "
    "Not a clinical diagnostic device. Requires authorized adjudicator verification."
)

# Standard verified clinical catalogue (strictly validated ICD-10 codes)
VALIDATED_ICD10_CATALOGUE: Dict[str, Dict[str, str]] = {
    "acute cholecystitis": {"code": "K81.0", "system": "ICD-10", "display": "Acute cholecystitis"},
    "chronic cholecystitis": {"code": "K81.1", "system": "ICD-10", "display": "Chronic cholecystitis"},
    "cholelithiasis": {"code": "K80.2", "system": "ICD-10", "display": "Calculus of gallbladder without cholecystitis"},
    "acute appendicitis": {"code": "K35.8", "system": "ICD-10", "display": "Other and unspecified acute appendicitis"},
    "acute myocardial infarction": {"code": "I21.9", "system": "ICD-10", "display": "Acute myocardial infarction, unspecified"},
    "type 2 diabetes mellitus": {"code": "E11.9", "system": "ICD-10", "display": "Type 2 diabetes mellitus without complications"},
    "essential hypertension": {"code": "I10", "system": "ICD-10", "display": "Essential (primary) hypertension"},
    "pneumonia": {"code": "J18.9", "system": "ICD-10", "display": "Pneumonia, unspecified organism"},
    "inguinal hernia": {"code": "K40.9", "system": "ICD-10", "display": "Unilateral inguinal hernia"},
    "bilateral inguinal hernia": {"code": "K40.2", "system": "ICD-10", "display": "Bilateral inguinal hernia"},
    "dengue fever": {"code": "A90", "system": "ICD-10", "display": "Dengue fever [classical dengue]"},
    "malaria": {"code": "B54", "system": "ICD-10", "display": "Unspecified malaria"},
    "urinary tract infection": {"code": "N39.0", "system": "ICD-10", "display": "Urinary tract infection, site not specified"},
    "acute gastroenteritis": {"code": "A09", "system": "ICD-10", "display": "Infectious gastroenteritis and colitis, unspecified"},
}


class BiomedicalEntity(BaseModel):
    text: str
    label: str  # "DISEASE", "SYMPTOM", "MEDICATION", "PROCEDURE", "TEST"
    start: int
    end: int
    confidence: float
    source_span: str
    normalized_term: str
    icd_code: Optional[str] = None
    icd_system: Optional[str] = None


class BiomedicalExtractionResult(BaseModel):
    entities: List[BiomedicalEntity] = Field(default_factory=list)
    diseases: List[str] = Field(default_factory=list)
    symptoms: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    procedures: List[str] = Field(default_factory=list)
    tests: List[str] = Field(default_factory=list)
    backend_mode: str  # "neural_biobert_checkpoint", "validated_clinical_rule_engine", "mock_adapter"
    status: str
    disclaimer: str = BIOMEDICAL_DISCLAIMER

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class BaseBiomedicalNERAdapter(ABC):
    """Abstract interface for biomedical entity extraction."""

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        pass

    @abstractmethod
    def extract_entities(self, text: str) -> BiomedicalExtractionResult:
        pass


class ValidatedClinicalNERAdapter(BaseBiomedicalNERAdapter):
    """
    High-precision clinical entity recognizer with exact text spans and validated ICD mapping.
    Used for deterministic baseline extraction and when deep learning libraries are not installed.
    """

    PATTERNS: List[Tuple[str, str, re.Pattern]] = [
        # Diseases
        ("DISEASE", "Acute Cholecystitis", re.compile(r"\bacute\s+cholecystitis\b", re.IGNORECASE)),
        ("DISEASE", "Chronic Cholecystitis", re.compile(r"\bchronic\s+cholecystitis\b", re.IGNORECASE)),
        ("DISEASE", "Cholelithiasis", re.compile(r"\b(?:cholelithiasis|gallstones?)\b", re.IGNORECASE)),
        ("DISEASE", "Acute Appendicitis", re.compile(r"\bacute\s+appendicitis\b", re.IGNORECASE)),
        ("DISEASE", "Acute Myocardial Infarction", re.compile(r"\b(?:acute\s+myocardial\s+infarction|ami|heart\s+attack)\b", re.IGNORECASE)),
        ("DISEASE", "Type 2 Diabetes Mellitus", re.compile(r"\b(?:type\s+2\s+diabetes(?:\s+mellitus)?|t2dm)\b", re.IGNORECASE)),
        ("DISEASE", "Essential Hypertension", re.compile(r"\b(?:essential\s+hypertension|hypertension|htn)\b", re.IGNORECASE)),
        ("DISEASE", "Pneumonia", re.compile(r"\bpneumonia\b", re.IGNORECASE)),
        ("DISEASE", "Inguinal Hernia", re.compile(r"\b(?:bilateral\s+)?inguinal\s+hernia\b", re.IGNORECASE)),
        ("DISEASE", "Dengue Fever", re.compile(r"\bdengue(?:\s+fever)?\b", re.IGNORECASE)),
        ("DISEASE", "Malaria", re.compile(r"\bmalaria\b", re.IGNORECASE)),
        ("DISEASE", "Urinary Tract Infection", re.compile(r"\b(?:urinary\s+tract\s+infection|uti)\b", re.IGNORECASE)),
        ("DISEASE", "Acute Gastroenteritis", re.compile(r"\b(?:acute\s+gastroenteritis|age)\b", re.IGNORECASE)),

        # Symptoms
        ("SYMPTOM", "Abdominal Pain", re.compile(r"\b(?:acute\s+)?abdominal\s+pain\b", re.IGNORECASE)),
        ("SYMPTOM", "Fever", re.compile(r"\b(?:high\s+grade\s+)?fever\b", re.IGNORECASE)),
        ("SYMPTOM", "Nausea", re.compile(r"\bnausea\b", re.IGNORECASE)),
        ("SYMPTOM", "Vomiting", re.compile(r"\bvomiting\b", re.IGNORECASE)),
        ("SYMPTOM", "Chest Pain", re.compile(r"\bchest\s+pain\b", re.IGNORECASE)),
        ("SYMPTOM", "Shortness of Breath", re.compile(r"\b(?:shortness\s+of\s+breath|dyspnea)\b", re.IGNORECASE)),
        ("SYMPTOM", "Headache", re.compile(r"\bheadache\b", re.IGNORECASE)),

        # Procedures
        ("PROCEDURE", "Laparoscopic Cholecystectomy", re.compile(r"\blaparoscopic\s+cholecystectomy\b", re.IGNORECASE)),
        ("PROCEDURE", "Open Cholecystectomy", re.compile(r"\bopen\s+cholecystectomy\b", re.IGNORECASE)),
        ("PROCEDURE", "Appendectomy", re.compile(r"\b(?:laparoscopic\s+)?appendectomy\b", re.IGNORECASE)),
        ("PROCEDURE", "Hernioplasty", re.compile(r"\b(?:hernioplasty|herniorrhaphy|hernia\s+repair)\b", re.IGNORECASE)),
        ("PROCEDURE", "Coronary Angiography", re.compile(r"\b(?:coronary\s+angiography|ptca\s+angioplasty|stent\s+placement)\b", re.IGNORECASE)),
        ("PROCEDURE", "Intravenous Cannulation", re.compile(r"\b(?:iv\s+cannulation|central\s+line)\b", re.IGNORECASE)),

        # Medications
        ("MEDICATION", "Ceftriaxone", re.compile(r"\b(?:ceftriaxone|inj\s+ceftriaxone)\b", re.IGNORECASE)),
        ("MEDICATION", "Pantoprazole", re.compile(r"\b(?:pantoprazole|tab\s+pantoprazole|inj\s+pantocid)\b", re.IGNORECASE)),
        ("MEDICATION", "Metronidazole", re.compile(r"\b(?:metronidazole|iv\s+flagyl)\b", re.IGNORECASE)),
        ("MEDICATION", "Paracetamol", re.compile(r"\b(?:paracetamol|pcm|acetaminophen)\b", re.IGNORECASE)),
        ("MEDICATION", "Tramadol", re.compile(r"\b(?:tramadol|inj\s+tramadol)\b", re.IGNORECASE)),
        ("MEDICATION", "Ondansetron", re.compile(r"\b(?:ondansetron|inj\s+emset)\b", re.IGNORECASE)),
        ("MEDICATION", "Atorvastatin", re.compile(r"\batorvastatin\b", re.IGNORECASE)),
        ("MEDICATION", "Metformin", re.compile(r"\bmetformin\b", re.IGNORECASE)),

        # Tests
        ("TEST", "Ultrasound Abdomen", re.compile(r"\b(?:ultrasound(?:\s+of)?\s+abdomen|usg\s+abdomen|sonography)\b", re.IGNORECASE)),
        ("TEST", "Complete Blood Count", re.compile(r"\b(?:complete\s+blood\s+count|cbc)\b", re.IGNORECASE)),
        ("TEST", "Chest X-Ray", re.compile(r"\b(?:chest\s+x-?ray|cxr)\b", re.IGNORECASE)),
        ("TEST", "Liver Function Test", re.compile(r"\b(?:liver\s+function\s+test|lft)\b", re.IGNORECASE)),
        ("TEST", "Renal Function Test", re.compile(r"\b(?:renal\s+function\s+test|kft|rft|serum\s+creatinine)\b", re.IGNORECASE)),
        ("TEST", "Electrocardiogram", re.compile(r"\b(?:electrocardiogram|ecg|ekg)\b", re.IGNORECASE)),
        ("TEST", "CT Scan Abdomen", re.compile(r"\b(?:ct\s+scan\s+abdomen|cect\s+abdomen)\b", re.IGNORECASE)),
    ]

    @property
    def adapter_name(self) -> str:
        return "validated_clinical_rule_engine"

    def extract_entities(self, text: str) -> BiomedicalExtractionResult:
        if not text or not text.strip():
            return BiomedicalExtractionResult(
                backend_mode=self.adapter_name,
                status="Empty Input",
            )

        entities: List[BiomedicalEntity] = []
        seen_spans: Set[Tuple[int, int]] = set()

        for label, norm_term, pattern in self.PATTERNS:
            for match in pattern.finditer(text):
                span = (match.start(), match.end())
                if span in seen_spans:
                    continue
                seen_spans.add(span)

                matched_text = match.group(0)

                # Look up validated ICD-10 code (strictly if documented in catalogue)
                icd_entry = VALIDATED_ICD10_CATALOGUE.get(norm_term.lower())
                icd_code = icd_entry["code"] if icd_entry else None
                icd_sys = icd_entry["system"] if icd_entry else None

                entities.append(
                    BiomedicalEntity(
                        text=matched_text,
                        label=label,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.95,
                        source_span=matched_text,
                        normalized_term=norm_term,
                        icd_code=icd_code,
                        icd_system=icd_sys,
                    )
                )

        # Sort entities by appearance in text
        entities.sort(key=lambda e: e.start)

        diseases = sorted(list({e.normalized_term for e in entities if e.label == "DISEASE"}))
        symptoms = sorted(list({e.normalized_term for e in entities if e.label == "SYMPTOM"}))
        medications = sorted(list({e.normalized_term for e in entities if e.label == "MEDICATION"}))
        procedures = sorted(list({e.normalized_term for e in entities if e.label == "PROCEDURE"}))
        tests = sorted(list({e.normalized_term for e in entities if e.label == "TEST"}))

        return BiomedicalExtractionResult(
            entities=entities,
            diseases=diseases,
            symptoms=symptoms,
            medications=medications,
            procedures=procedures,
            tests=tests,
            backend_mode=self.adapter_name,
            status="Success",
        )


class NeuralBioBERTAdapter(BaseBiomedicalNERAdapter):
    """
    Adapter for fine-tuned BioBERT token classification pipelines.
    Gracefully falls back to ValidatedClinicalNERAdapter if dependencies
    (transformers, torch) or weights are unavailable.
    """

    DEFAULT_CHECKPOINT = "d4data/biomedical-ner-all"

    def __init__(self, checkpoint: Optional[str] = None):
        self.checkpoint = checkpoint or os.environ.get(
            "CLAIMBRIDGE_BIOBERT_CHECKPOINT", self.DEFAULT_CHECKPOINT
        )
        self._pipeline = None
        self._fallback_adapter = ValidatedClinicalNERAdapter()
        self._init_error: Optional[str] = None
        self._try_load_pipeline()

    @property
    def adapter_name(self) -> str:
        if self._pipeline:
            return f"neural_biobert ({self.checkpoint})"
        return f"fallback_to_{self._fallback_adapter.adapter_name}"

    def _try_load_pipeline(self):
        try:
            import torch
            from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification

            self._pipeline = pipeline(
                "ner",
                model=self.checkpoint,
                aggregation_strategy="simple",
            )
        except Exception as exc:
            self._pipeline = None
            self._init_error = f"{type(exc).__name__}: {str(exc)}"

    def extract_entities(self, text: str) -> BiomedicalExtractionResult:
        if not self._pipeline:
            # Fall back safely without crashing
            result = self._fallback_adapter.extract_entities(text)
            result.status = f"Fallback Mode ({self._init_error or 'Neural model uninitialized'})"
            return result

        try:
            # Chunk long documents into 400-word segments to prevent token overflow
            words = text.split()
            chunk_size = 400
            chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

            raw_entities = []
            char_offset = 0
            for chunk in chunks:
                preds = self._pipeline(chunk)
                for p in preds:
                    p["start"] += char_offset
                    p["end"] += char_offset
                    raw_entities.append(p)
                char_offset += len(chunk) + 1

            entities: List[BiomedicalEntity] = []
            for r in raw_entities:
                entity_group = r.get("entity_group", "").upper()
                word = r.get("word", "").strip()
                score = float(r.get("score", 0.0))

                label = "DISEASE"
                if "MED" in entity_group or "CHEM" in entity_group:
                    label = "MEDICATION"
                elif "PROC" in entity_group:
                    label = "PROCEDURE"
                elif "SYMP" in entity_group or "SIGN" in entity_group:
                    label = "SYMPTOM"
                elif "DIAG" in entity_group or "TEST" in entity_group:
                    label = "TEST"

                # Check validated catalogue
                icd_entry = VALIDATED_ICD10_CATALOGUE.get(word.lower())

                entities.append(
                    BiomedicalEntity(
                        text=word,
                        label=label,
                        start=r["start"],
                        end=r["end"],
                        confidence=round(score, 4),
                        source_span=word,
                        normalized_term=word.title(),
                        icd_code=icd_entry["code"] if icd_entry else None,
                        icd_system=icd_entry["system"] if icd_entry else None,
                    )
                )

            diseases = sorted(list({e.normalized_term for e in entities if e.label == "DISEASE"}))
            symptoms = sorted(list({e.normalized_term for e in entities if e.label == "SYMPTOM"}))
            medications = sorted(list({e.normalized_term for e in entities if e.label == "MEDICATION"}))
            procedures = sorted(list({e.normalized_term for e in entities if e.label == "PROCEDURE"}))
            tests = sorted(list({e.normalized_term for e in entities if e.label == "TEST"}))

            return BiomedicalExtractionResult(
                entities=entities,
                diseases=diseases,
                symptoms=symptoms,
                medications=medications,
                procedures=procedures,
                tests=tests,
                backend_mode="neural_biobert_checkpoint",
                status="Success",
            )
        except Exception as exc:
            result = self._fallback_adapter.extract_entities(text)
            result.status = f"Inference Failed ({type(exc).__name__}), fell back to clinical rules"
            return result


class BiomedicalNLPService:
    """
    Top-level application service. Integrates with ClaimBridge Medical Intelligence.
    """

    def __init__(self, adapter: Optional[BaseBiomedicalNERAdapter] = None):
        self.adapter = adapter or ValidatedClinicalNERAdapter()

    def process_clinical_text(self, text: str) -> BiomedicalExtractionResult:
        return self.adapter.extract_entities(text)


# Global singleton
_global_biomedical_service: Optional[BiomedicalNLPService] = None


def get_biomedical_nlp_service() -> BiomedicalNLPService:
    global _global_biomedical_service
    if _global_biomedical_service is None:
        # Check if neural biobert is requested via environment
        use_neural = os.environ.get("CLAIMBRIDGE_USE_NEURAL_BIOBERT", "false").lower() == "true"
        if use_neural:
            _global_biomedical_service = BiomedicalNLPService(NeuralBioBERTAdapter())
        else:
            _global_biomedical_service = BiomedicalNLPService(ValidatedClinicalNERAdapter())
    return _global_biomedical_service
