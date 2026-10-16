"""
Unit tests for ClaimBridge Policy RAG Engine.
Covers:
1. Relevant retrieval of coverage and exclusions
2. Missing evidence handling (irrelevant query returns empty or low-scoring results)
3. Incorrect-policy isolation (Querying POL-A NEVER returns results from POL-B)
4. Citation integrity (exact section number, title, and citation format)
5. Synthetic policy governance (is_fictional flag and disclaimer presence)
"""

import pytest
from app.policy_rag import PolicyRAGEngine, PolicyChunk, FICTIONAL_POLICY_DISCLAIMER


POLICY_ALPHA_TEXT = """
CLAIMBRIDGE SAMPLE POLICY ALPHA - COMPREHENSIVE HEALTH

SECTION 1 - INPATIENT HOSPITALIZATION
Inpatient hospitalization expenses are covered when the insured person
is admitted for medically necessary surgical or acute medical care.
Room accommodation is capped at semi-private room rates.

SECTION 2 - SURGICAL PROCEDURES
All medically necessary surgical procedures performed in an accredited hospital
are eligible for coverage, subject to policy deductible.

SECTION 3 - COSMETIC AND EXPERIMENTAL EXCLUSIONS
Cosmetic surgery, aesthetic treatments, and experimental procedures are strictly excluded.
Any complications arising from self-inflicted injuries are not covered.

SECTION 4 - DOCUMENTATION REQUIREMENTS
Claimant must submit itemized hospital bills, official discharge summary,
and diagnostic test reports within 30 days of discharge.
"""

POLICY_BETA_TEXT = """
CLAIMBRIDGE SAMPLE POLICY BETA - DENTAL AND VISION ADD-ON

SECTION 1 - PREVENTATIVE DENTAL
Routine dental cleaning and examination are covered twice per calendar year.

SECTION 2 - ORTHODONTIC EXCLUSIONS
Cosmetic teeth whitening and elective adult orthodontics are excluded from coverage.
"""


@pytest.fixture
def rag_engine():
    engine = PolicyRAGEngine(policies_dir=None)
    engine.ingest_policy_text(POLICY_ALPHA_TEXT, policy_id="POL-ALPHA", document_name="policy_alpha.txt")
    engine.ingest_policy_text(POLICY_BETA_TEXT, policy_id="POL-BETA", document_name="policy_beta.txt")
    return engine


def test_relevant_retrieval_finds_hospitalization(rag_engine):
    results = rag_engine.retrieve("patient admitted for inpatient hospitalization and room stay", policy_id="POL-ALPHA")
    assert len(results) >= 1
    top = results[0]
    assert top.policy_id == "POL-ALPHA"
    assert "SECTION 1" in top.section_title
    assert "HOSPITALIZATION" in top.section_title
    assert top.relevance_score > 0.3
    assert "hospitalization" in [t.lower() for t in top.matched_terms] or "inpatient" in [t.lower() for t in top.matched_terms]


def test_relevant_retrieval_finds_exclusions(rag_engine):
    results = rag_engine.retrieve("cosmetic surgery rhinoplasty aesthetic treatment", policy_id="POL-ALPHA")
    assert len(results) >= 1
    top = results[0]
    assert top.section_type == "exclusion"
    assert "SECTION 3" in top.section_title
    assert top.relevance_score > 0.3


def test_missing_evidence_returns_empty_or_zero(rag_engine):
    results = rag_engine.retrieve("quantum mechanics satellite orbital velocity astrophysics", policy_id="POL-ALPHA")
    assert len(results) == 0


def test_unknown_policy_id_returns_empty(rag_engine):
    results = rag_engine.retrieve("hospitalization admission", policy_id="POL-NONEXISTENT")
    assert results == []


def test_incorrect_policy_isolation_strictly_enforced(rag_engine):
    """
    CRITICAL SECURITY CHECK:
    Querying dental coverage against POL-ALPHA MUST NOT retrieve POL-BETA's dental clauses.
    Querying surgical coverage against POL-BETA MUST NOT retrieve POL-ALPHA's surgical clauses.
    """
    # Dental query on Alpha: Alpha has no dental coverage
    alpha_results = rag_engine.retrieve("routine dental cleaning and examination", policy_id="POL-ALPHA")
    for r in alpha_results:
        assert r.policy_id == "POL-ALPHA"
        assert "DENTAL" not in r.section_title.upper()

    # Surgery query on Beta: Beta has no surgery coverage
    beta_results = rag_engine.retrieve("medically necessary surgical procedures", policy_id="POL-BETA")
    for r in beta_results:
        assert r.policy_id == "POL-BETA"
        assert "SURGICAL PROCEDURES" not in r.section_title.upper()


def test_citation_integrity(rag_engine):
    results = rag_engine.retrieve("discharge summary itemized hospital bills", policy_id="POL-ALPHA")
    assert len(results) >= 1
    top = results[0]
    assert top.document_name == "policy_alpha.txt"
    assert top.section_number == 4
    assert top.citation == "[policy_alpha.txt | SECTION 4 - DOCUMENTATION REQUIREMENTS]"
    assert top.chunk_id == "POL-ALPHA#sec_04"


def test_synthetic_governance_disclaimer(rag_engine):
    results = rag_engine.retrieve("hospitalization", policy_id="POL-ALPHA")
    assert len(results) >= 1
    top = results[0]
    assert top.is_fictional is True
    assert top.disclaimer == FICTIONAL_POLICY_DISCLAIMER
