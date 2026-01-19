"""Repository for audit logs (feedback from agents) - STEP-8."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.db.models import AuditLog

import logging

logger = logging.getLogger(__name__)


class FeedbackRepository:
    """
    Repository for accessing and storing audit logs.
    
    Responsibilities:
    - Persist agent feedback to database
    - Query audit logs for analytics/dashboard
    - No deduplication or advanced logic (yet)
    """
    
    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db
    
    def create_audit_log(
        self,
        agent_id: str,
        event_id: str,
        decision: str,
        user_action: str,
        reason_code: str,
        feedback_timestamp: int,
    ) -> AuditLog:
        """
        Create and persist an audit log entry.
        
        Args:
            agent_id: Agent identifier
            event_id: Event identifier
            decision: ALLOW | WARN | BLOCK
            user_action: PROCEED | CANCEL | NONE
            reason_code: Explanation
            feedback_timestamp: UTC epoch seconds (from agent)
        
        Returns:
            AuditLog: Created audit log record
        
        Raises:
            Exception: On database error
        """
        try:
            audit_log = AuditLog(
                agent_id=agent_id,
                event_id=event_id,
                decision=decision,
                user_action=user_action,
                reason_code=reason_code,
                feedback_timestamp=feedback_timestamp,
            )
            
            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(audit_log)
            
            logger.info(
                f"[AUDIT] Created log | agent_id={agent_id}, event_id={event_id}, "
                f"decision={decision}, user_action={user_action}"
            )
            
            return audit_log
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"[AUDIT] Failed to create log: {e}")
            raise
    
    def get_audit_log_by_id(self, log_id: int) -> Optional[AuditLog]:
        """Get audit log by ID."""
        try:
            return self.db.query(AuditLog).filter(AuditLog.id == log_id).first()
        except Exception as e:
            logger.error(f"[AUDIT] Error fetching log {log_id}: {e}")
            return None
    
    def get_audit_logs_by_event(self, event_id: str) -> List[AuditLog]:
        """Get all audit logs for a specific event."""
        try:
            return self.db.query(AuditLog)\
                .filter(AuditLog.event_id == event_id)\
                .order_by(desc(AuditLog.created_at))\
                .all()
        except Exception as e:
            logger.error(f"[AUDIT] Error fetching logs for event {event_id}: {e}")
            return []
    
    def get_audit_logs_by_agent(
        self,
        agent_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Get audit logs for a specific agent with pagination."""
        try:
            return self.db.query(AuditLog)\
                .filter(AuditLog.agent_id == agent_id)\
                .order_by(desc(AuditLog.created_at))\
                .limit(limit)\
                .offset(offset)\
                .all()
        except Exception as e:
            logger.error(
                f"[AUDIT] Error fetching logs for agent {agent_id}: {e}"
            )
            return []
    
    def get_audit_logs_by_decision(
        self,
        decision: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Get audit logs filtered by decision type."""
        try:
            return self.db.query(AuditLog)\
                .filter(AuditLog.decision == decision)\
                .order_by(desc(AuditLog.created_at))\
                .limit(limit)\
                .offset(offset)\
                .all()
        except Exception as e:
            logger.error(
                f"[AUDIT] Error fetching logs for decision {decision}: {e}"
            )
            return []
    
    def get_audit_logs_by_agent_and_decision(
        self,
        agent_id: str,
        decision: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Get audit logs for agent filtered by decision."""
        try:
            return self.db.query(AuditLog)\
                .filter(and_(
                    AuditLog.agent_id == agent_id,
                    AuditLog.decision == decision
                ))\
                .order_by(desc(AuditLog.created_at))\
                .limit(limit)\
                .offset(offset)\
                .all()
        except Exception as e:
            logger.error(
                f"[AUDIT] Error fetching logs for agent {agent_id}, decision {decision}: {e}"
            )
            return []
    
    def count_by_decision(self, agent_id: Optional[str] = None) -> Dict[str, int]:
        """
        Get count of decisions by type.
        
        Returns:
            dict: {"ALLOW": count, "WARN": count, "BLOCK": count}
        """
        try:
            result = {"ALLOW": 0, "WARN": 0, "BLOCK": 0}
            
            for decision in result.keys():
                query = self.db.query(AuditLog)\
                    .filter(AuditLog.decision == decision)
                
                if agent_id:
                    query = query.filter(AuditLog.agent_id == agent_id)
                
                result[decision] = query.count()
            
            return result
        except Exception as e:
            logger.error(f"[AUDIT] Error counting decisions: {e}")
            return {"ALLOW": 0, "WARN": 0, "BLOCK": 0}
    
    def count_by_user_action(self, agent_id: Optional[str] = None) -> Dict[str, int]:
        """
        Get count of user actions.
        
        Returns:
            dict: {"PROCEED": count, "CANCEL": count, "NONE": count}
        """
        try:
            result = {"PROCEED": 0, "CANCEL": 0, "NONE": 0}
            
            for action in result.keys():
                query = self.db.query(AuditLog)\
                    .filter(AuditLog.user_action == action)
                
                if agent_id:
                    query = query.filter(AuditLog.agent_id == agent_id)
                
                result[action] = query.count()
            
            return result
        except Exception as e:
            logger.error(f"[AUDIT] Error counting user actions: {e}")
            return {"PROCEED": 0, "CANCEL": 0, "NONE": 0}
    
    # TODO: Implement feedback batching and deduplication
    # TODO: Add hook for retraining pipeline integration
    # TODO: Add policy analytics and rule effectiveness tracking
    # TODO: Support audit log archival and retention policies
