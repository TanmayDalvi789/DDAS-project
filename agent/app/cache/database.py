"""Local cache database - SQLite for fast lookups."""

import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class CacheDatabase:
    """
    Local SQLite cache for file lookup results and features.
    
    Tables:
    - features: Extracted features (exact, fuzzy, semantic)
    - cache_entries: Decision cache (future)
    """
    
    def __init__(self, db_path: str):
        """Initialize cache database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._init_schema()
        logger.info(f"Cache database: {self.db_path}")
    
    def _init_schema(self):
        """Initialize database schema."""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            cursor = self.conn.cursor()
            
            # Features table (STEP-4 + STEP-5)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    file_path TEXT,
                    timestamp INTEGER,
                    exact_hash TEXT,
                    fuzzy_sig BLOB,
                    semantic_vec BLOB,
                    semantic_model TEXT,
                    lookup_results TEXT,
                    lookup_timestamp INTEGER,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Index for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_features_event_id
                ON features(event_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_features_file_path
                ON features(file_path)
            """)
            
            # Cache entries table (Phase-5)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT UNIQUE,
                    decision_result TEXT,
                    ttl_seconds INTEGER,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            self.conn.commit()
            logger.debug("Cache schema initialized")
        
        except Exception as e:
            logger.error(f"Failed to initialize cache schema: {e}")
            raise
    
    def save_features(self, event_id: str, file_path: str, features: dict) -> bool:
        """
        Save extracted features to cache.
        
        Args:
            event_id: Event identifier
            file_path: File path
            features: Dict with keys: exact_hash, fuzzy_sig, semantic_vec, semantic_model
        
        Returns:
            bool: True if saved, False if failed
        """
        try:
            import time
            cursor = self.conn.cursor()
            
            # Serialize complex fields
            fuzzy_sig = json.dumps(features.get('fuzzy_sig')).encode() if features.get('fuzzy_sig') else None
            semantic_vec = json.dumps(features.get('semantic_vec')).encode() if features.get('semantic_vec') else None
            
            cursor.execute("""
                INSERT INTO features
                (event_id, file_path, timestamp, exact_hash, fuzzy_sig, semantic_vec, semantic_model)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                file_path,
                int(time.time()),
                features.get('exact_hash'),
                fuzzy_sig,
                semantic_vec,
                features.get('semantic_model')
            ))
            
            self.conn.commit()
            logger.debug(f"Features saved: {event_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save features: {e}")
            return False
    
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
            bool: True if updated
        """
        try:
            import time
            cursor = self.conn.cursor()
            
            # Update features row with lookup results
            lookup_json = json.dumps(lookup_results)
            timestamp = int(time.time())
            
            cursor.execute(
                """
                UPDATE features
                SET lookup_results = ?, lookup_timestamp = ?
                WHERE event_id = ? AND file_path = ?
                """,
                (lookup_json, timestamp, event_id, file_path),
            )
            
            self.conn.commit()
            
            if cursor.rowcount > 0:
                logger.debug(f"Lookup results saved for: {event_id}")
                return True
            else:
                logger.warning(
                    f"No features row found to update lookup results: {event_id}"
                )
                return False
        
        except Exception as e:
            logger.error(f"Failed to save lookup results: {e}")
            return False
    
    def get(self, file_hash: str):
        """
        Get cached decision for file hash.
        
        Returns:
            dict or None: Cached decision or None if not found/expired
        """
        # TODO Phase-5: Query cache_entries table
        return None
    
    def set(self, file_hash: str, decision_result: dict, ttl_seconds: int):
        """
        Store decision result in cache.
        
        Args:
            file_hash: File identifier
            decision_result: Decision from engine
            ttl_seconds: Time-to-live
        
        TODO Phase-5: Implement decision caching
        """
        # TODO Phase-5: Store in cache_entries
        pass
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.debug("Cache database closed")

