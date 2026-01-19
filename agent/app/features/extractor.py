"""
Feature Extraction Coordinator (STEP-4)

Coordinates extraction of all features from a file.
Best-effort, graceful degradation, no blocking.
"""

import logging
from typing import Optional, Dict, Any
from app.features import extract_exact, extract_fuzzy, extract_semantic

logger = logging.getLogger(__name__)


def extract_all_features(
    file_path: str,
    metadata: Optional[Dict[str, Any]] = None,
    partial_hash_bytes: int = 4194304,  # 4 MB
) -> Dict[str, Any]:
    """
    Extract all available features from a file.
    
    This is the main entry point for feature extraction.
    
    Args:
        file_path: Path to file on disk
        metadata: Optional metadata dict (filename, mimetype, url, etc.)
        partial_hash_bytes: Size for partial hash (default 4 MB)
    
    Returns:
        Dict with keys:
        - exact: exact hash dict or None
        - fuzzy: fuzzy signature dict or None
        - semantic: semantic embedding dict or None
        
        All values are None if extraction fails for that feature.
    """
    features = {
        "exact": None,
        "fuzzy": None,
        "semantic": None,
    }
    
    try:
        # Extract exact hash (SHA-256 of first N bytes)
        logger.debug(f"Extracting features: {file_path[:50]}")
        
        exact = extract_exact(file_path, partial_hash_bytes)
        if exact:
            features["exact"] = exact
            logger.debug(f"✓ Exact hash extracted")
        
        # Extract fuzzy signature (MinHash)
        fuzzy = extract_fuzzy(file_path)
        if fuzzy:
            features["fuzzy"] = fuzzy
            logger.debug(f"✓ Fuzzy signature extracted")
        
        # Extract semantic embedding (SBERT)
        semantic = extract_semantic(file_path, metadata)
        if semantic:
            features["semantic"] = semantic
            logger.debug(f"✓ Semantic embedding extracted")
        
        # Log summary
        extracted_count = sum(1 for v in features.values() if v is not None)
        logger.info(
            f"Features extracted: {file_path[:50]} "
            f"({extracted_count}/3 features)"
        )
        
        return features
    
    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")
        return features
