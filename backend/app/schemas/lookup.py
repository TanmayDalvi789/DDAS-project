"""
Lookup-specific schemas (similarity scoring only, no decisions).
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class SimilarityScore(BaseModel):
    """Similarity score from a single algorithm."""
    algorithm: str = Field(description="Algorithm name (exact, fuzzy, semantic)")
    confidence: float = Field(ge=0.0, le=1.0, description="Similarity confidence score")
    matches: List[str] = Field(default=[], description="Matched items")


class LookupResponse(BaseModel):
    """Response: Fingerprint lookup with similarity scores only (NO DECISION)."""
    event_id: str
    fingerprint_hash: Optional[str] = Field(default=None, description="Fingerprint hash")
    matched: bool = Field(description="Whether any match was found")
    best_score: float = Field(ge=0.0, le=1.0, description="Highest similarity score")
    best_algorithm: Optional[str] = Field(default=None, description="Algorithm with best score")
    scores: List[SimilarityScore] = Field(
        description="Scores from each algorithm (no decision)",
        default=[]
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    job_id: Optional[str] = Field(default=None, description="Background job ID (if async)")
    
    class Config:
        from_attributes = True


class FingerprintLookupRequest(BaseModel):
    """Request: Lookup fingerprint similarities."""
    event_id: str = Field(..., description="Event ID to analyze")
    fingerprint_hash: str = Field(..., description="Fingerprint to look up")
    reference_samples: List[str] = Field(
        default=[],
        description="Reference samples to match against (optional)"
    )


class BatchLookupRequest(BaseModel):
    """Request: Lookup multiple fingerprints."""
    event_id: str = Field(..., description="Event ID")
    fingerprints: List[str] = Field(min_items=1, description="Fingerprints to look up")
    reference_samples: List[str] = Field(
        default=[],
        description="Reference samples to match against"
    )


class BatchLookupResponse(BaseModel):
    """Response: Multiple fingerprint lookups."""
    event_id: str
    results: List[LookupResponse] = Field(description="Lookup results for each fingerprint")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
