"""
Similarity Matching Module

Handles fingerprint similarity calculation using multiple algorithms:
- Exact matching (binary)
- Fuzzy matching (string similarity)
- Semantic matching (embedding-based)
"""

import logging
from typing import List, Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class SimilarityMatcher(ABC):
    """Base class for similarity matching algorithms."""
    
    @abstractmethod
    def match(self, query: str, reference_samples: List[str], threshold: float = 0.8) -> tuple:
        """
        Match query against reference samples.
        
        Returns:
            (confidence: float, matches: List[str])
        """
        pass


class ExactMatcher(SimilarityMatcher):
    """Exact string matching - binary result."""
    
    def match(self, query: str, reference_samples: List[str], threshold: float = 0.8) -> tuple:
        """
        Check for exact match in reference samples.
        
        Args:
            query: Query string to match
            reference_samples: List of reference samples
            threshold: Ignored for exact matching
        
        Returns:
            (confidence, matches) where confidence is 1.0 for match or 0.0 for no match
        """
        for sample in reference_samples:
            if query == sample:
                return 1.0, [sample]
        return 0.0, []


class FuzzyMatcher(SimilarityMatcher):
    """Fuzzy string matching using simple similarity heuristics."""
    
    @staticmethod
    def _calculate_similarity(s1: str, s2: str) -> float:
        """
        Calculate string similarity using simple character overlap.
        
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not s1 or not s2:
            return 0.0 if s1 != s2 else 1.0
        
        # Normalize to lowercase for comparison
        s1, s2 = s1.lower(), s2.lower()
        
        # If identical after normalization
        if s1 == s2:
            return 1.0
        
        # Calculate character overlap
        len_s1, len_s2 = len(s1), len(s2)
        max_len = max(len_s1, len_s2)
        
        if max_len == 0:
            return 1.0
        
        # Count matching characters
        matches = sum(1 for c1, c2 in zip(s1, s2) if c1 == c2)
        similarity = matches / max_len
        
        return similarity
    
    def match(self, query: str, reference_samples: List[str], threshold: float = 0.8) -> tuple:
        """
        Match query against reference samples using fuzzy matching.
        
        Args:
            query: Query string to match
            reference_samples: List of reference samples
            threshold: Minimum similarity score to consider a match
        
        Returns:
            (confidence, matches) where confidence is the best similarity score found
        """
        best_confidence = 0.0
        matches = []
        
        for sample in reference_samples:
            confidence = self._calculate_similarity(query, sample)
            
            if confidence >= threshold:
                if confidence > best_confidence:
                    best_confidence = confidence
                    matches = [sample]
                elif confidence == best_confidence:
                    matches.append(sample)
        
        return best_confidence, matches


class SemanticMatcher(SimilarityMatcher):
    """Semantic matching using FAISS-based embeddings (placeholder)."""
    
    def __init__(self, embedding_dim: int = 384):
        """Initialize semantic matcher."""
        self.embedding_dim = embedding_dim
        self.embeddings = {}
        logger.info(f"Initialized semantic matcher with embedding dimension {embedding_dim}")
    
    def match(self, query: str, reference_samples: List[str], threshold: float = 0.8) -> tuple:
        """
        Match query against reference samples using semantic similarity.
        
        NOTE: This is a placeholder implementation. In production:
        1. Use proper embedding models (sentence-transformers)
        2. Build FAISS index for efficient search
        3. Cache embeddings
        
        Args:
            query: Query string to match
            reference_samples: List of reference samples
            threshold: Minimum similarity score to consider a match
        
        Returns:
            (confidence, matches)
        """
        # Placeholder: use simple hash-based matching
        query_hash = hash(query) % 100
        matches = []
        best_confidence = 0.0
        
        for sample in reference_samples:
            sample_hash = hash(sample) % 100
            similarity = 1.0 - (abs(query_hash - sample_hash) / 100.0)
            
            if similarity >= threshold:
                best_confidence = max(best_confidence, similarity)
                matches.append(sample)
        
        return best_confidence, matches


class SimilarityOrchestrator:
    """Orchestrates similarity matching using multiple algorithms."""
    
    def __init__(
        self,
        exact_enabled: bool = True,
        fuzzy_enabled: bool = True,
        semantic_enabled: bool = True,
        fuzzy_threshold: float = 0.75,
        semantic_threshold: float = 0.7,
    ):
        """
        Initialize similarity orchestrator.
        
        Args:
            exact_enabled: Enable exact matching
            fuzzy_enabled: Enable fuzzy matching
            semantic_enabled: Enable semantic matching
            fuzzy_threshold: Minimum fuzzy match score
            semantic_threshold: Minimum semantic match score
        """
        self.exact = ExactMatcher() if exact_enabled else None
        self.fuzzy = FuzzyMatcher() if fuzzy_enabled else None
        self.semantic = SemanticMatcher() if semantic_enabled else None
        
        self.fuzzy_threshold = fuzzy_threshold
        self.semantic_threshold = semantic_threshold
        
        logger.info(
            f"Similarity orchestrator initialized: "
            f"exact={exact_enabled}, fuzzy={fuzzy_enabled}, semantic={semantic_enabled}"
        )
    
    def match(
        self,
        query: str,
        reference_samples: List[str],
    ) -> Dict[str, Any]:
        """
        Match query against reference samples using all enabled algorithms.
        
        Returns:
            {
                "matched": bool,
                "confidence": float (highest score across all algorithms),
                "best_algorithm": str,
                "algorithms": {
                    "exact": {"confidence": float, "matches": List[str]},
                    "fuzzy": {...},
                    "semantic": {...},
                }
            }
        """
        results = {
            "matched": False,
            "confidence": 0.0,
            "best_algorithm": None,
            "algorithms": {}
        }
        
        if not reference_samples or not query:
            return results
        
        # Run exact matching
        if self.exact:
            confidence, matches = self.exact.match(query, reference_samples)
            results["algorithms"]["exact"] = {
                "confidence": confidence,
                "matches": matches,
            }
            if confidence > results["confidence"]:
                results["confidence"] = confidence
                results["best_algorithm"] = "exact"
        
        # Run fuzzy matching
        if self.fuzzy:
            confidence, matches = self.fuzzy.match(query, reference_samples, self.fuzzy_threshold)
            results["algorithms"]["fuzzy"] = {
                "confidence": confidence,
                "matches": matches,
            }
            if confidence > results["confidence"]:
                results["confidence"] = confidence
                results["best_algorithm"] = "fuzzy"
        
        # Run semantic matching
        if self.semantic:
            confidence, matches = self.semantic.match(query, reference_samples, self.semantic_threshold)
            results["algorithms"]["semantic"] = {
                "confidence": confidence,
                "matches": matches,
            }
            if confidence > results["confidence"]:
                results["confidence"] = confidence
                results["best_algorithm"] = "semantic"
        
        results["matched"] = results["confidence"] > 0.0
        
        return results
