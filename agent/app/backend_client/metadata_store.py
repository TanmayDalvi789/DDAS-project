"""Agent metadata storage - SQLite persistence."""

import logging
import sqlite3
from pathlib import Path
from typing import Optional
import uuid

logger = logging.getLogger(__name__)


class AgentMetadataStore:
    """
    Stores agent metadata in local SQLite database.
    
    Persists:
    - agent_id (generated or confirmed by backend)
    - registration status
    - last heartbeat timestamp
    """
    
    def __init__(self, db_path: str):
        """Initialize metadata store."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
    
    def _init_schema(self):
        """Initialize SQLite schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_meta (
                    id INTEGER PRIMARY KEY,
                    agent_id TEXT UNIQUE NOT NULL,
                    registered INTEGER DEFAULT 0,
                    last_heartbeat INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.commit()
            logger.info(f"Agent metadata schema initialized: {self.db_path}")
    
    def get_agent_id(self) -> Optional[str]:
        """
        Get stored agent_id.
        
        Returns:
            str: Agent ID or None if not yet generated
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT agent_id FROM agent_meta LIMIT 1")
                row = cursor.fetchone()
                if row:
                    agent_id = row[0]
                    logger.info(f"Agent ID loaded: {agent_id}")
                    return agent_id
                return None
        except Exception as e:
            logger.error(f"Failed to load agent_id: {e}")
            return None
    
    def store_agent_id(self, agent_id: str, registered: bool = False) -> bool:
        """
        Store agent_id (generated or from backend).
        
        Args:
            agent_id: Agent identifier
            registered: Whether registration is confirmed by backend
        
        Returns:
            bool: True if successful
        """
        try:
            from datetime import datetime
            now = datetime.utcnow().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # Try insert first
                try:
                    conn.execute("""
                        INSERT INTO agent_meta (agent_id, registered, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                    """, (agent_id, 1 if registered else 0, now, now))
                except sqlite3.IntegrityError:
                    # Update if already exists
                    conn.execute("""
                        UPDATE agent_meta
                        SET registered = ?, updated_at = ?
                        WHERE agent_id = ?
                    """, (1 if registered else 0, now, agent_id))
                
                conn.commit()
            
            logger.info(f"Agent ID stored: {agent_id} (registered={registered})\")\n            return True\n            \n        except Exception as e:\n            logger.error(f\"Failed to store agent_id: {e}\")\n            return False\n    \n    def mark_heartbeat(self, agent_id: str) -> bool:\n        \"\"\"\n        Update last heartbeat timestamp.\n        \n        Args:\n            agent_id: Agent identifier\n        \n        Returns:\n            bool: True if successful\n        \"\"\"\n        try:\n            from datetime import datetime\n            now = int(datetime.utcnow().timestamp())\n            \n            with sqlite3.connect(self.db_path) as conn:\n                conn.execute(\n                    \"UPDATE agent_meta SET last_heartbeat = ? WHERE agent_id = ?\",\n                    (now, agent_id)\n                )\n                conn.commit()\n            \n            return True\n        except Exception as e:\n            logger.error(f\"Failed to update heartbeat: {e}\")\n            return False\n