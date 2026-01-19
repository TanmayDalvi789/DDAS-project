"""Exact matching detection using hashing."""

from typing import Optional, List, Dict, Any, Set
import hashlib
import logging

logger = logging.getLogger(__name__)


class ExactDetection:
    """Exact matching detection using cryptographic hashing.
    
    Detects exact matches or matches within specified edit distance.
    Fast and deterministic, useful for known bad actors.
    """
    
    def __init__(self, hash_algo: str = "sha256"):
        """Initialize exact detection.
        
        Args:
            hash_algo: Hash algorithm (sha256, md5, etc.)
        """
        self.hash_algo = hash_algo
        self.hash_index: Set[str] = set()
        self.text_to_hash: Dict[str, str] = {}
        logger.info(f"ExactDetection initialized with hash_algo={hash_algo}")
    
    def build_index(self, reference_samples: List[str]) -> None:
        """Build hash index from reference samples.
        
        Args:
            reference_samples: List of reference strings to hash and index
        """
        logger.info(f"Building exact hash index for {len(reference_samples)} samples")
        
        self.hash_index.clear()
        self.text_to_hash.clear()
        
        for sample in reference_samples:
            sample_hash = self._hash(sample)
            self.hash_index.add(sample_hash)
            self.text_to_hash[sample_hash] = sample
        
        logger.info(f"Built index with {len(self.hash_index)} unique hashes")
    
    def detect(
        self,
        input_text: str,
        reference_samples: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Detect exact matches.
        
        Args:
            input_text: Text to search for
            reference_samples: Optional list of samples (builds index if provided)
        
        Returns:
            Detection result
        """
        logger.debug(f"Exact detection: '{input_text[:50]}'")
        
        if reference_samples:
            self.build_index(reference_samples)
        
        if not self.hash_index:
            logger.warning("No samples indexed")
            return {
                "detected": False,
                "confidence": 0.0,
                "matched_hashes": [],
                "reason": "No samples indexed",
            }
        
        input_hash = self._hash(input_text)
        matched = input_hash in self.hash_index
        
        confidence = 1.0 if matched else 0.0
        
        logger.info(f"Exact detection: detected={matched}")
        
        result = {
            "detected": matched,
            "confidence": confidence,
            "algorithm": "exact_matching",
            "hash_algo": self.hash_algo,
        }
        
        if matched:
            result["matched_text"] = self.text_to_hash.get(input_hash, "")
            result["hash"] = input_hash
        
        return result
    
    def detect_partial(
        self,
        input_text: str,
        reference_samples: Optional[List[str]] = None,
        ignore_case: bool = True,
        ignore_whitespace: bool = True,
    ) -> Dict[str, Any]:
        """Detect matches with preprocessing (case/whitespace normalization).
        
        Args:
            input_text: Text to search for
            reference_samples: Optional list of samples
            ignore_case: Normalize to lowercase
            ignore_whitespace: Remove extra whitespace
        
        Returns:
            Detection result
        """
        logger.debug(f"Partial exact detection: '{input_text[:50]}'")
        
        normalized_input = self._normalize(input_text, ignore_case, ignore_whitespace)
        
        if reference_samples:
            # Normalize samples during index build
            normalized_samples = [
                self._normalize(s, ignore_case, ignore_whitespace)
                for s in reference_samples
            ]
            self.build_index(normalized_samples)
        
        return self.detect(normalized_input)
    
    def detect_substrings(
        self,
        input_text: str,
        reference_samples: List[str],
    ) -> Dict[str, Any]:
        """Detect if input appears as substring in any sample.
        
        Args:
            input_text: Text to search for
            reference_samples: List of texts to search within
        
        Returns:
            Detection result with matched substrings
        """
        logger.debug(f"Substring detection: '{input_text[:50]}'")
        
        matches = []
        
        for sample in reference_samples:
            if input_text in sample:
                matches.append({
                    "matched_substring": sample,
                    "confidence": 1.0,
                })
        
        detected = len(matches) > 0
        
        logger.info(f"Substring detection: detected={detected}, matches={len(matches)}")
        
        return {
            "detected": detected,
            "confidence": 1.0 if detected else 0.0,
            "matched_substrings": matches,
            "algorithm": "substring_matching",
        }
    
    def detect_many(
        self,
        input_texts: List[str],
        reference_samples: List[str],
    ) -> Dict[str, Any]:
        """Detect if any input matches any reference sample.
        
        Args:
            input_texts: List of texts to search for
            reference_samples: List of reference samples
        
        Returns:
            Aggregated detection result
        """
        logger.info(f"Many-to-many exact detection: {len(input_texts)} vs {len(reference_samples)}")
        
        self.build_index(reference_samples)
        
        matches = []
        for text in input_texts:
            result = self.detect(text)
            if result["detected"]:
                matches.append({
                    "input": text,
                    "matched": result.get("matched_text", ""),
                })
        
        detected = len(matches) > 0
        
        return {
            "detected": detected,
            "total_checked": len(input_texts),
            "matches_found": len(matches),
            "matches": matches,
            "algorithm": "exact_matching",
        }
    
    @staticmethod
    def _hash(text: str, algo: str = "sha256") -> str:
        """Generate hash of text."""
        if algo == "sha256":
            return hashlib.sha256(text.encode()).hexdigest()
        elif algo == "md5":
            return hashlib.md5(text.encode()).hexdigest()
        elif algo == "sha1":
            return hashlib.sha1(text.encode()).hexdigest()
        else:
            return hashlib.sha256(text.encode()).hexdigest()
    
    def _hash(self, text: str) -> str:
        """Hash text using configured algorithm."""
        return self._hash.__func__(text, self.hash_algo)
    
    @staticmethod
    def _normalize(
        text: str,
        ignore_case: bool = True,
        ignore_whitespace: bool = True,
    ) -> str:
        """Normalize text for comparison."""
        normalized = text
        
        if ignore_case:
            normalized = normalized.lower()
        
        if ignore_whitespace:
            normalized = " ".join(normalized.split())
        
        return normalized
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about current index."""
        return {
            "indexed_samples": len(self.hash_index),
            "hash_algorithm": self.hash_algo,
            "unique_hashes": len(self.hash_index),
        }
