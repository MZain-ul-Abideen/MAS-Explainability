"""
Phase 4: Evidence Retrieval Module
Retrieves relevant facts based on queries.
"""

from .evidence_retriever import EvidenceRetriever, retrieve_evidence, EvidencePacket

__all__ = [
    'EvidenceRetriever',
    'retrieve_evidence',
    'EvidencePacket',
]