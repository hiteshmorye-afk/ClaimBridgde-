"""
Unit tests for ClaimBridge Biomedical NLP & NER Engine.
Covers:
1. Synthetic medical text clinical entity extraction (Diseases, Symptoms, Procedures, Medications, Tests)
2. Exact text span integrity (start, end, source_span matching)
3. Validated ICD-10 cross-referencing (validated dictionary only, never fabricated)
4. Non-hallucination guarantee: unlisted conditions get icd_code = None
5. Graceful handling of empty text, long clinical narratives, and missing neural dependencies
"""

import pytest
from app.biomedical_nlp import (
    BiomedicalNLPService,
    NeuralBioBERTAdapter,
    ValidatedClinicalNERAdapter,
    BiomedicalExtractionResult,
    BIOMEDICAL_DISCLAIMER,
)


SYNTHETIC_CLINICAL_DISCHARGE_SUMMARY = """
ADMISSION DIAGNOSIS: Acute Cholecystitis with Cholelithiasis.
CHIEF COMPLAINT: 46-year-old male presented with severe acute abdominal pain and high grade fever for 2 days.
Associated with nausea and recurrent vomiting.
DIAGNOSTIC INVESTIGATIONS:
- Ultrasound Abdomen showed distended gallbladder with multiple gallstones and thickened gallbladder wall (4.5 mm).
- Complete Blood Count revealed leukocytosis (WBC 14,800/mcL).
- Liver Function Test showed mild elevation of serum alkaline phosphatase.
PROCEDURE PERFORMED:
Successful Laparoscopic Cholecystectomy under general anaesthesia on 11-Aug-2026.
MEDICATIONS ADMINISTERED:
- Inj Ceftriaxone 1g IV BD
- Inj Pantoprazole 40mg IV OD
- Tab Paracetamol 650mg TDS PRN
DISCHARGE ADVICE: Patient stable, afebrile, discharged with oral medications.
"""


@pytest.fixture
def clinical_service():
    adapter = ValidatedClinicalNERAdapter()
    return BiomedicalNLPService(adapter=adapter)


def test_clinical_entity_extraction_categories(clinical_service):
    result = clinical_service.process_clinical_text(SYNTHETIC_CLINICAL_DISCHARGE_SUMMARY)

    assert isinstance(result, BiomedicalExtractionResult)
    assert result.status == "Success"

    # Diseases
    assert "Acute Cholecystitis" in result.diseases
    assert "Cholelithiasis" in result.diseases

    # Symptoms
    assert "Abdominal Pain" in result.symptoms
    assert "Fever" in result.symptoms
    assert "Nausea" in result.symptoms
    assert "Vomiting" in result.symptoms

    # Procedures
    assert "Laparoscopic Cholecystectomy" in result.procedures

    # Medications
    assert "Ceftriaxone" in result.medications
    assert "Pantoprazole" in result.medications
    assert "Paracetamol" in result.medications

    # Diagnostic Tests
    assert "Ultrasound Abdomen" in result.tests
    assert "Complete Blood Count" in result.tests
    assert "Liver Function Test" in result.tests


def test_span_integrity(clinical_service):
    result = clinical_service.process_clinical_text(SYNTHETIC_CLINICAL_DISCHARGE_SUMMARY)
    assert len(result.entities) > 5

    for entity in result.entities:
        # Verify span boundaries exactly correspond to text
        extracted_from_span = SYNTHETIC_CLINICAL_DISCHARGE_SUMMARY[entity.start:entity.end]
        assert extracted_from_span.lower() == entity.source_span.lower()
        assert entity.confidence > 0.0


def test_validated_icd10_cross_referencing(clinical_service):
    result = clinical_service.process_clinical_text("Patient diagnosed with Acute Cholecystitis.")
    acute_chole = next(e for e in result.entities if e.normalized_term == "Acute Cholecystitis")
    assert acute_chole.icd_code == "K81.0"
    assert acute_chole.icd_system == "ICD-10"


def test_non_hallucination_of_unlisted_icd_codes(clinical_service):
    """
    CRITICAL SAFETY CHECK:
    Entities without an authoritative dictionary mapping MUST have icd_code = None.
    ICD codes must never be fabricated.
    """
    result = clinical_service.process_clinical_text("Patient reported severe abdominal pain and nausea.")
    symptom_entities = [e for e in result.entities if e.label == "SYMPTOM"]
    for s in symptom_entities:
        # Abdominal pain and nausea are symptoms, not billable ICD-10 primary diagnoses in catalogue
        assert s.icd_code is None


def test_empty_and_whitespace_input(clinical_service):
    result = clinical_service.process_clinical_text("    ")
    assert result.status == "Empty Input"
    assert len(result.entities) == 0


def test_long_document_processing(clinical_service):
    # Repeat the clinical narrative 10 times to test long text stability
    long_narrative = SYNTHETIC_CLINICAL_DISCHARGE_SUMMARY * 10
    result = clinical_service.process_clinical_text(long_narrative)
    assert result.status == "Success"
    assert len(result.entities) > 20


def test_neural_biobert_adapter_graceful_fallback():
    # Since torch/transformers are not installed in .venv, NeuralBioBERTAdapter must fall back cleanly
    adapter = NeuralBioBERTAdapter(checkpoint="d4data/biomedical-ner-all")
    result = adapter.extract_entities("Patient admitted for Acute Appendicitis.")
    assert "Fallback" in result.status or result.status == "Success"
    assert "Acute Appendicitis" in result.diseases
