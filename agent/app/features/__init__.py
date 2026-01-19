"""
Local Feature Extraction Package (STEP-4)

Extract features from files locally on the agent.

Features:
- exact: SHA-256 hash of first N bytes
- fuzzy: MinHash for fuzzy matching
- semantic: Sentence embedding from metadata

All extractors are:
- Optional (graceful degradation)
- Non-blocking (best-effort)
- Error-safe (no fatal exceptions)
"""

from .exact import extract_exact
from .fuzzy import extract_fuzzy
from .semantic import extract_semantic
from .extractor import extract_all_features

__all__ = [
    'extract_exact',
    'extract_fuzzy',
    'extract_semantic',
    'extract_all_features',
]

