"""Cache repository - Data access layer."""

import logging
from app.cache.database import CacheDatabase

logger = logging.getLogger(__name__)


class CacheRepository:
    """
    Repository for cache data access.
    
    Decouples cache storage from business logic.
    
    Responsibilities:
    - Store extracted features (STEP-4)
    - Store/retrieve cached decisions (Phase-5)
    """
    
    def __init__(self, db: CacheDatabase):
        """Initialize repository."""
        self.db = db
    
    def save_features(self, event_id: str, file_path: str, features: dict) -> bool:
        """
        Save extracted features to cache.
        
        Args:
            event_id: Event identifier
            file_path: File path
            features: Dict with extracted features
        
        Returns:
            bool: True if saved
        """
        return self.db.save_features(event_id, file_path, features)
    
    def save_lookup_results(
        self, event_id: str, file_path: str, lookup_results: dict
    ) -> bool:
        """
        Save backend lookup results to cache.
        
        Args:
            event_id: Event identifier
            file_path: File path
            lookup_results: Dict from perform_lookup()
        
        Returns:
            bool: True if saved
        """
        return self.db.save_lookup_results(event_id, file_path, lookup_results)
    
    def find_by_hash(self, file_hash: str):
        """Find cached decision by file hash."""
        return self.db.get(file_hash)
    
    def save_decision(self, file_hash: str, decision_result: dict, ttl_seconds: int):
        """Save decision to cache."""
        self.db.set(file_hash, decision_result, ttl_seconds)

