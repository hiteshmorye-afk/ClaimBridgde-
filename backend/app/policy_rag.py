"""
ClaimBridge Policy RAG (Retrieval-Augmented Generation) Engine
==============================================================
Provides claim-isolated, citation-verifiable retrieval over synthetic health insurance policies.

Key Design Requirements:
1. Strict Policy Context Isolation: A claim's query against policy_id 'POL-A' never retrieves
   clauses or evidence from 'POL-B'.
2. Citation Integrity: Every retrieved passage retains its exact source document name,
   section number, section title, and unique chunk identifier.
3. Fictional Corpus Governance: Every chunk and retrieval output is explicitly tagged as
   fictional policy text and carries a non-binding synthetic disclaimer.
4. Local Development Storage: Pure in-memory vector/BM25 index with zero schema migrations,
   no external vector database service required.
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


FICTIONAL_POLICY_DISCLAIMER = (
    "Synthetic policy text for demonstration and testing purposes only. "
    "Not a real insurance contract."
)

DEFAULT_POLICIES_DIR = Path(__file__).resolve().parent.parent / "policies"


def normalize_text(text: str) -> str:
    """Normalize whitespace and formatting for consistent retrieval."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def tokenize(text: str) -> List[str]:
    """Extract alphanumeric lowercased tokens."""
    return re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())


STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with",
    "by", "at", "is", "are", "was", "were", "be", "been", "being", "this",
    "that", "it", "as", "from", "any", "all", "shall", "under", "which",
}


@dataclass
class PolicyChunk:
    chunk_id: str
    policy_id: str
    document_name: str
    section_number: Optional[int]
    section_title: str
    section_type: str
    content: str
    tokens: List[str] = field(default_factory=list)
    term_frequencies: Dict[str, float] = field(default_factory=dict)
    is_fictional: bool = True
    disclaimer: str = FICTIONAL_POLICY_DISCLAIMER

    def __post_init__(self):
        if not self.tokens:
            self.tokens = [t for t in tokenize(self.content) if t not in STOPWORDS]
        if not self.term_frequencies and self.tokens:
            total = len(self.tokens)
            for t in self.tokens:
                self.term_frequencies[t] = self.term_frequencies.get(t, 0.0) + 1.0 / total


@dataclass
class PolicyRetrievalResult:
    chunk_id: str
    policy_id: str
    document_name: str
    section_number: Optional[int]
    section_title: str
    section_type: str
    content: str
    relevance_score: float
    citation: str
    matched_terms: List[str]
    is_fictional: bool = True
    disclaimer: str = FICTIONAL_POLICY_DISCLAIMER

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "policy_id": self.policy_id,
            "document_name": self.document_name,
            "section_number": self.section_number,
            "section_title": self.section_title,
            "section_type": self.section_type,
            "content": self.content,
            "relevance_score": round(self.relevance_score, 4),
            "citation": self.citation,
            "matched_terms": self.matched_terms,
            "is_fictional": self.is_fictional,
            "disclaimer": self.disclaimer,
        }


def classify_section_type(title_and_text: str) -> str:
    """Classify the functional purpose of a policy section."""
    lowered = title_and_text.lower()
    if "exclusion" in lowered or "not covered" in lowered or "excluded" in lowered:
        return "exclusion"
    if "hospitalization" in lowered or "inpatient" in lowered or "admission" in lowered:
        return "hospitalization"
    if "surgical" in lowered or "surgery" in lowered or "procedure" in lowered:
        return "surgical_treatment"
    if "waiting period" in lowered:
        return "waiting_period"
    if "documentation" in lowered or "documents" in lowered or "claim assessment" in lowered:
        return "claim_documentation"
    if "medical treatment" in lowered or "medically necessary" in lowered:
        return "medical_treatment"
    return "general_terms"


class BM25Retriever:
    """
    BM25 text retrieval implementation with length normalization and IDF weighting.
    """

    def __init__(self, chunks: List[PolicyChunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.doc_count = len(chunks)
        self.doc_lengths = [len(c.tokens) for c in chunks]
        self.avg_doc_len = (
            sum(self.doc_lengths) / max(self.doc_count, 1) if self.doc_count > 0 else 1.0
        )
        self.idf: Dict[str, float] = {}
        self._compute_idf()

    def _compute_idf(self):
        doc_freqs: Dict[str, int] = {}
        for chunk in self.chunks:
            seen = set(chunk.tokens)
            for token in seen:
                doc_freqs[token] = doc_freqs.get(token, 0) + 1

        for token, df in doc_freqs.items():
            # Standard Lucene/Okapi BM25 IDF
            self.idf[token] = math.log(1.0 + (self.doc_count - df + 0.5) / (df + 0.5))

    def score(self, query_tokens: List[str]) -> List[Tuple[float, List[str]]]:
        scores = []
        for idx, chunk in enumerate(self.chunks):
            doc_len = self.doc_lengths[idx]
            token_counts: Dict[str, int] = {}
            for t in chunk.tokens:
                token_counts[t] = token_counts.get(t, 0) + 1

            chunk_score = 0.0
            matched: List[str] = []
            for qt in query_tokens:
                if qt in token_counts:
                    tf = token_counts[qt]
                    idf = self.idf.get(qt, 0.5)
                    denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                    chunk_score += idf * (tf * (self.k1 + 1.0)) / denom
                    matched.append(qt)

            scores.append((chunk_score, matched))
        return scores


class PolicyRAGEngine:
    """
    In-memory RAG Index for ClaimBridge Policies.
    Ensures strict per-policy partitioning.
    """

    def __init__(self, policies_dir: Optional[Path] = None):
        self.policies_dir = policies_dir or DEFAULT_POLICIES_DIR
        # Map: policy_id -> List[PolicyChunk]
        self._policy_indexes: Dict[str, List[PolicyChunk]] = {}
        self._retrievers: Dict[str, BM25Retriever] = {}
        self._corpus_metadata: Dict[str, Dict[str, Any]] = {}
        self.load_corpus()

    def load_corpus(self) -> int:
        """
        Scan and ingest policy documents from the policies directory.
        Returns the number of ingested chunks.
        """
        if not self.policies_dir.exists():
            return 0

        total_chunks = 0
        for entry in self.policies_dir.iterdir():
            if entry.is_file() and entry.suffix.lower() in {".txt", ".md"}:
                policy_id = entry.stem  # e.g. "sample_policy"
                chunks = self.ingest_policy_file(entry, policy_id=policy_id)
                total_chunks += len(chunks)

        return total_chunks

    def ingest_policy_text(
        self,
        text: str,
        policy_id: str,
        document_name: str = "custom_policy.txt",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[PolicyChunk]:
        """
        Parse raw policy text into structured section chunks and index them under policy_id.
        """
        normalized = normalize_text(text)
        if not normalized:
            return []

        chunks: List[PolicyChunk] = []

        # Split on SECTION or ARTICLE headings
        section_pattern = re.compile(
            r"(?=(?:SECTION|ARTICLE)\s+(\d+)\s*[-:]?\s*([^\n\r]+))",
            re.IGNORECASE,
        )

        matches = list(section_pattern.finditer(normalized))
        if matches:
            for i, match in enumerate(matches):
                sec_num = int(match.group(1))
                sec_title_raw = match.group(2).strip()
                start_pos = match.start()
                end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(normalized)
                sec_body = normalized[start_pos:end_pos].strip()

                sec_type = classify_section_type(sec_title_raw + " " + sec_body)
                chunk_id = f"{policy_id}#sec_{sec_num:02d}"

                chunk = PolicyChunk(
                    chunk_id=chunk_id,
                    policy_id=policy_id,
                    document_name=document_name,
                    section_number=sec_num,
                    section_title=f"SECTION {sec_num} - {sec_title_raw}",
                    section_type=sec_type,
                    content=sec_body,
                )
                chunks.append(chunk)
        else:
            # Fallback: paragraph-based or fixed-size chunking
            paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
            if not paragraphs:
                paragraphs = [normalized]

            for i, para in enumerate(paragraphs, start=1):
                sec_type = classify_section_type(para)
                chunk_id = f"{policy_id}#para_{i:02d}"
                first_line = para.split("\n")[0][:60]
                chunk = PolicyChunk(
                    chunk_id=chunk_id,
                    policy_id=policy_id,
                    document_name=document_name,
                    section_number=i,
                    section_title=first_line,
                    section_type=sec_type,
                    content=para,
                )
                chunks.append(chunk)

        # Register in policy index
        self._policy_indexes[policy_id] = chunks
        self._retrievers[policy_id] = BM25Retriever(chunks)
        self._corpus_metadata[policy_id] = {
            "document_name": document_name,
            "chunk_count": len(chunks),
            "is_fictional": True,
            "custom_metadata": metadata or {},
        }
        return chunks

    def ingest_policy_file(self, file_path: Path, policy_id: Optional[str] = None) -> List[PolicyChunk]:
        """Read and index a single policy text file."""
        pid = policy_id or file_path.stem
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return self.ingest_policy_text(
                content,
                policy_id=pid,
                document_name=file_path.name,
            )
        except Exception:
            return []

    def get_registered_policies(self) -> List[str]:
        """Return all currently indexed policy identifiers."""
        return sorted(list(self._policy_indexes.keys()))

    def retrieve(
        self,
        query: str,
        policy_id: str,
        top_k: int = 3,
        min_score: float = 0.05,
    ) -> List[PolicyRetrievalResult]:
        """
        Execute isolated retrieval strictly against the specified policy_id.
        Guarantees that no chunks from other policies are returned.
        """
        if not query or not policy_id:
            return []

        chunks = self._policy_indexes.get(policy_id)
        retriever = self._retrievers.get(policy_id)
        if not chunks or not retriever:
            # Strictly return empty when policy_id is unknown or has no indexed clauses
            return []

        query_tokens = [t for t in tokenize(query) if t not in STOPWORDS]
        if not query_tokens:
            return []

        scores_with_matches = retriever.score(query_tokens)

        # Normalize scores to 0.0 - 1.0 range
        max_raw = max([s for s, _ in scores_with_matches], default=1.0)
        max_raw = max_raw if max_raw > 0 else 1.0

        results: List[PolicyRetrievalResult] = []
        for idx, (raw_score, matched) in enumerate(scores_with_matches):
            if raw_score <= 0:
                continue

            normalized_score = min(raw_score / max_raw, 1.0)
            if normalized_score < min_score:
                continue

            chunk = chunks[idx]

            # Enforce policy isolation at result generation time
            if chunk.policy_id != policy_id:
                continue

            citation = (
                f"[{chunk.document_name} | {chunk.section_title}]"
                if chunk.section_title
                else f"[{chunk.document_name}]"
            )

            results.append(
                PolicyRetrievalResult(
                    chunk_id=chunk.chunk_id,
                    policy_id=chunk.policy_id,
                    document_name=chunk.document_name,
                    section_number=chunk.section_number,
                    section_title=chunk.section_title,
                    section_type=chunk.section_type,
                    content=chunk.content,
                    relevance_score=normalized_score,
                    citation=citation,
                    matched_terms=matched,
                    is_fictional=chunk.is_fictional,
                    disclaimer=chunk.disclaimer,
                )
            )

        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:top_k]


# Global singleton instance for local application runtime
_global_rag_engine: Optional[PolicyRAGEngine] = None


def get_policy_rag_engine() -> PolicyRAGEngine:
    """Return or initialize the global PolicyRAGEngine singleton."""
    global _global_rag_engine
    if _global_rag_engine is None:
        _global_rag_engine = PolicyRAGEngine()
    return _global_rag_engine
