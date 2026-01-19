"""
Similarity module exports.
"""

from app.similarity.orchestrator import (
    SimilarityOrchestrator,
    ExactMatcher,
    FuzzyMatcher,
    SemanticMatcher,
)

__all__ = [
    "SimilarityOrchestrator",
    "ExactMatcher",
    "FuzzyMatcher",
    "SemanticMatcher",
]
