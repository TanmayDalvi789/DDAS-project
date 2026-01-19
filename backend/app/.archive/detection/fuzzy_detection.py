"""Fuzzy string matching detection algorithm."""

from typing import Optional, List, Dict, Any
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class FuzzyDetection:
    """Fuzzy string matching detection using difflib.
    
    Detects similar strings using sequence matching.
    Useful for typo detection, similar username detection, etc.
    """
    
    def __init__(self, threshold: float = 0.85):
        """Initialize fuzzy detection.
        
        Args:
            threshold: Similarity threshold (0-1). Default 0.85
        """
        self.threshold = threshold
        logger.info(f"FuzzyDetection initialized with threshold={threshold}")
    
    def detect(
        self,
        input_text: str,
        reference_samples: List[str],
        case_sensitive: bool = False,
    ) -> Dict[str, Any]:
        """Detect similar strings in reference samples.
        
        Args:
            input_text: Text to search for
            reference_samples: List of reference strings to compare against
            case_sensitive: Whether comparison is case sensitive
        
        Returns:
            Detection result with matches and confidence
        """
        logger.debug(f"Fuzzy detection: {input_text[:50]}... vs {len(reference_samples)} samples")
        
        if not input_text or not reference_samples:
            logger.warning("Empty input_text or reference_samples")
            return {
                "detected": False,
                "confidence": 0.0,
                "matches": [],
                "reason": "Empty input",
            }
        
        # Prepare text for comparison
        compare_text = input_text if case_sensitive else input_text.lower()
        
        # Find all matches above threshold
        matches = []
        for sample in reference_samples:
            compare_sample = sample if case_sensitive else sample.lower()
            similarity = SequenceMatcher(None, compare_text, compare_sample).ratio()
            
            if similarity >= self.threshold:
                matches.append({
                    "matched_string": sample,
                    "confidence": round(similarity, 4),
                })
        
        # Sort by confidence
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        
        detected = len(matches) > 0
        max_confidence = matches[0]["confidence"] if matches else 0.0
        
        logger.info(f"Fuzzy detection result: detected={detected}, matches={len(matches)}")
        
        return {
            "detected": detected,
            "confidence": round(max_confidence, 4),
            "matches": matches,
            "threshold_used": self.threshold,
            "algorithm": "fuzzy_matching",
        }
    
    def detect_in_text(
        self,
        input_text: str,
        reference_text: str,
        substring_threshold: float = 0.80,
    ) -> Dict[str, Any]:
        """Detect if input appears as substring match in reference text.
        
        Args:
            input_text: Text to search for
            reference_text: Text to search within
            substring_threshold: Minimum similarity for substring match
        
        Returns:
            Detection result
        """
        logger.debug(f"Substring fuzzy detection: '{input_text[:50]}'")
        
        if not input_text or not reference_text:
            return {
                "detected": False,
                "confidence": 0.0,
                "substrings_matched": [],
            }
        
        # Split reference into words and n-grams
        words = reference_text.split()
        ngrams = self._generate_ngrams(reference_text, len(input_text.split()[0]) if input_text.split() else 3)
        
        candidates = words + ngrams
        matches = []
        
        for candidate in candidates:
            similarity = SequenceMatcher(None, input_text.lower(), candidate.lower()).ratio()
            if similarity >= substring_threshold:
                matches.append({
                    "matched_substring": candidate,
                    "confidence": round(similarity, 4),
                })
        
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        
        return {
            "detected": len(matches) > 0,
            "confidence": round(matches[0]["confidence"], 4) if matches else 0.0,
            "substrings_matched": matches[:5],  # Top 5
        }
    
    def batch_detect(
        self,
        input_texts: List[str],
        reference_samples: List[str],
    ) -> List[Dict[str, Any]]:
        """Detect multiple input texts against reference samples.
        
        Args:
            input_texts: List of texts to search for
            reference_samples: List of reference strings
        
        Returns:
            List of detection results
        """
        logger.info(f"Batch fuzzy detection: {len(input_texts)} inputs vs {len(reference_samples)} samples")
        
        results = []
        for text in input_texts:
            result = self.detect(text, reference_samples)
            results.append({
                "input": text,
                **result
            })
        
        return results
    
    @staticmethod
    def _generate_ngrams(text: str, n: int = 3) -> List[str]:
        """Generate n-grams from text."""
        words = text.split()
        ngrams = []
        for i in range(len(words) - n + 1):
            ngrams.append(" ".join(words[i:i+n]))
        return ngrams
    
    def update_threshold(self, threshold: float) -> None:
        """Update detection threshold."""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0 and 1, got {threshold}")
        self.threshold = threshold
        logger.info(f"Fuzzy detection threshold updated to {threshold}")
