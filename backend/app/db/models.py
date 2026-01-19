"""Database models for storing events, signals, alerts, and audit logs."""

from datetime import datetime
from typing import Dict, Any

from sqlalchemy import Column, String, DateTime, JSON, Integer, Float, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.db.base import Base

import logging

logger = logging.getLogger(__name__)


class RawEvent(Base):
    """Raw event model."""
    
    __tablename__ = "raw_events"
    
    event_id = Column(String(36), primary_key=True)
    source_type = Column(String(50), nullable=False)  # AGENT, PROXY, DASHBOARD
    source_id = Column(String(100), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    event_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    signals = relationship("DetectionSignal", back_populates="event", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_source_created", "source_id", "created_at"),
        Index("idx_event_type", "event_type"),
    )


class DetectionSignal(Base):
    """Detection signal/result model."""
    
    __tablename__ = "detection_signals"
    
    signal_id = Column(String(36), primary_key=True)
    event_id = Column(String(36), ForeignKey("raw_events.event_id"), nullable=False, index=True)
    detection_type = Column(String(50), nullable=False)  # fuzzy, semantic, exact
    status = Column(String(50), nullable=False, index=True)  # pending, processing, completed, failed
    confidence = Column(Float, nullable=True)
    result = Column(JSON, nullable=True)  # Detection result data
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    event = relationship("RawEvent", back_populates="signals")
    alerts = relationship("Alert", back_populates="signal", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_event_detection", "event_id", "detection_type"),
        Index("idx_status_created", "status", "created_at"),
    )


class Alert(Base):
    """Alert/decision model."""
    
    __tablename__ = "alerts"
    
    alert_id = Column(String(36), primary_key=True)
    signal_id = Column(String(36), ForeignKey("detection_signals.signal_id"), nullable=False, index=True)
    decision = Column(String(50), nullable=False)  # ALLOW, WARN, BLOCK
    status = Column(String(50), nullable=False, index=True)  # active, acknowledged, resolved
    reason = Column(String(1000), nullable=True)
    priority = Column(Integer, nullable=False, default=5)  # 1-10
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    signal = relationship("DetectionSignal", back_populates="alerts")
    
    __table_args__ = (
        Index("idx_status_priority", "status", "priority"),
        Index("idx_created_decision", "created_at", "decision"),
    )


class ProcessedSignal(Base):
    """Processed signals/aggregated results."""
    
    __tablename__ = "processed_signals"
    
    processed_id = Column(String(36), primary_key=True)
    event_id = Column(String(36), ForeignKey("raw_events.event_id"), nullable=False, index=True)
    signal_ids = Column(JSON, default=list)  # List of signal IDs that contributed
    aggregated_confidence = Column(Float, nullable=False)
    decision = Column(String(50), nullable=True)  # Final decision
    result_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)




class WorkerStatus(Base):
    """Worker/service health status."""
    
    __tablename__ = "worker_status"
    
    worker_id = Column(String(100), primary_key=True)
    status = Column(String(50), nullable=False)  # running, paused, error, offline
    last_heartbeat = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    tasks_processed = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    queue_size = Column(Integer, nullable=True)
    worker_metadata = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(Base):
    """Audit log for agent feedback and decisions (STEP-8)."""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(100), nullable=False, index=True)
    event_id = Column(String(36), nullable=False, index=True)
    decision = Column(String(50), nullable=False)  # ALLOW, WARN, BLOCK
    user_action = Column(String(50), nullable=False)  # PROCEED, CANCEL, NONE
    reason_code = Column(String(500), nullable=False)  # Deterministic explanation
    feedback_timestamp = Column(Integer, nullable=False)  # UTC epoch seconds (from agent)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        Index("idx_agent_created", "agent_id", "created_at"),
        Index("idx_event_created", "event_id", "created_at"),
        Index("idx_decision_created", "decision", "created_at"),
        Index("idx_agent_decision", "agent_id", "decision"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "event_id": self.event_id,
            "decision": self.decision,
            "user_action": self.user_action,
            "reason_code": self.reason_code,
            "feedback_timestamp": self.feedback_timestamp,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }