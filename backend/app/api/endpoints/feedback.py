"""
Feedback API Endpoints - STEP-8 Audit & Feedback Sync

Accepts feedback from agents and persists audit logs.
Minimal validation and storage (no ML/retraining hooks yet).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.db.database import get_db
from app.db.repositories.feedback_repo import FeedbackRepository

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["feedback"])


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================


class FeedbackCreate(BaseModel):
    """Create feedback/audit log request from agent."""
    
    agent_id: str = Field(..., description="Agent identifier")
    event_id: str = Field(..., description="Event identifier")
    decision: str = Field(..., description="ALLOW | WARN | BLOCK")
    user_action: str = Field(
        "NONE",
        description="PROCEED | CANCEL | NONE (user action for WARN decisions)"
    )
    reason_code: str = Field(..., description="Deterministic explanation")
    timestamp: int = Field(..., description="UTC epoch seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "agent_id": "agent-001",
                "event_id": "evt_12345",
                "decision": "WARN",
                "user_action": "PROCEED",
                "reason_code": "FUZZY_MATCH",
                "timestamp": 1705454400,
            }
        }


class FeedbackResponse(BaseModel):
    """Response after feedback accepted."""
    
    id: int = Field(..., description="Audit log record ID")
    agent_id: str
    event_id: str
    decision: str
    user_action: str
    reason_code: str
    feedback_timestamp: int
    created_at: Optional[str]
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "agent_id": "agent-001",
                "event_id": "evt_12345",
                "decision": "WARN",
                "user_action": "PROCEED",
                "reason_code": "FUZZY_MATCH",
                "feedback_timestamp": 1705454400,
                "created_at": "2026-01-17T10:00:00",
            }
        }


class AuditStatistics(BaseModel):
    """Statistics about audit logs."""
    
    total_logs: int
    decision_counts: Dict[str, int]
    user_action_counts: Dict[str, int]


class ErrorResponse(BaseModel):
    """Error response."""
    
    detail: str
    error_code: Optional[str] = None


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================


def get_feedback_repository(db: Session = Depends(get_db)) -> FeedbackRepository:
    """Get feedback repository."""
    return FeedbackRepository(db)


# ============================================================================
# CREATE ENDPOINTS
# ============================================================================


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Agent Feedback",
    description="Agent submits feedback/audit log for a decision",
    responses={
        201: {"description": "Feedback accepted"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    }
)
async def create_feedback(
    feedback_data: FeedbackCreate,
    repo: FeedbackRepository = Depends(get_feedback_repository),
) -> FeedbackResponse:
    """
    Accept feedback from agent.
    
    **Agent Responsibility**: Ensure payload matches contract
    
    **Backend Responsibility**: Validate enum values, reject malformed data
    
    - **agent_id**: Unique identifier for the agent
    - **event_id**: Event that triggered the decision
    - **decision**: ALLOW, WARN, or BLOCK
    - **user_action**: What the user did (PROCEED/CANCEL for WARN, NONE otherwise)
    - **reason_code**: Deterministic explanation (rule name, score, etc)
    - **timestamp**: When the decision was made (UTC epoch seconds)
    """
    try:
        # Validate enum values
        if feedback_data.decision not in ("ALLOW", "WARN", "BLOCK"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid decision: {feedback_data.decision}. Must be ALLOW, WARN, or BLOCK"
            )
        
        if feedback_data.user_action not in ("PROCEED", "CANCEL", "NONE"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user_action: {feedback_data.user_action}. Must be PROCEED, CANCEL, or NONE"
            )
        
        # Validate consistency
        if feedback_data.decision in ("ALLOW", "BLOCK"):
            if feedback_data.user_action != "NONE":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{feedback_data.decision} must have user_action='NONE'"
                )
        
        if feedback_data.decision == "WARN":
            if feedback_data.user_action not in ("PROCEED", "CANCEL"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="WARN must have user_action='PROCEED' or 'CANCEL'"
                )
        
        # Create audit log
        audit_log = repo.create_audit_log(
            agent_id=feedback_data.agent_id,
            event_id=feedback_data.event_id,
            decision=feedback_data.decision,
            user_action=feedback_data.user_action,
            reason_code=feedback_data.reason_code,
            feedback_timestamp=feedback_data.timestamp,
        )
        
        return FeedbackResponse(
            id=audit_log.id,
            agent_id=audit_log.agent_id,
            event_id=audit_log.event_id,
            decision=audit_log.decision,
            user_action=audit_log.user_action,
            reason_code=audit_log.reason_code,
            feedback_timestamp=audit_log.feedback_timestamp,
            created_at=audit_log.created_at.isoformat() if audit_log.created_at else None,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FEEDBACK] Error creating audit log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create feedback: {str(e)}"
        )


# ============================================================================
# READ ENDPOINTS
# ============================================================================


@router.get(
    "/feedback/{feedback_id}",
    response_model=FeedbackResponse,
    summary="Get Feedback by ID",
    description="Retrieve a specific audit log entry",
    responses={
        200: {"description": "Audit log found"},
        404: {"description": "Audit log not found"},
    }
)
async def get_feedback(
    feedback_id: int,
    repo: FeedbackRepository = Depends(get_feedback_repository),
) -> FeedbackResponse:
    """Get audit log by ID."""
    audit_log = repo.get_audit_log_by_id(feedback_id)
    
    if not audit_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log {feedback_id} not found"
        )
    
    return FeedbackResponse(
        id=audit_log.id,
        agent_id=audit_log.agent_id,
        event_id=audit_log.event_id,
        decision=audit_log.decision,
        user_action=audit_log.user_action,
        reason_code=audit_log.reason_code,
        feedback_timestamp=audit_log.feedback_timestamp,
        created_at=audit_log.created_at.isoformat() if audit_log.created_at else None,
    )


@router.get(
    "/feedback/event/{event_id}",
    response_model=List[FeedbackResponse],
    summary="Get Feedback by Event",
    description="Get all audit logs for a specific event",
)
async def get_feedback_by_event(
    event_id: str,
    repo: FeedbackRepository = Depends(get_feedback_repository),
) -> List[FeedbackResponse]:
    """Get audit logs for event."""
    audit_logs = repo.get_audit_logs_by_event(event_id)
    
    return [
        FeedbackResponse(
            id=log.id,
            agent_id=log.agent_id,
            event_id=log.event_id,
            decision=log.decision,
            user_action=log.user_action,
            reason_code=log.reason_code,
            feedback_timestamp=log.feedback_timestamp,
            created_at=log.created_at.isoformat() if log.created_at else None,
        )
        for log in audit_logs
    ]


@router.get(
    "/feedback/agent/{agent_id}",
    response_model=List[FeedbackResponse],
    summary="Get Feedback by Agent",
    description="Get audit logs for a specific agent (paginated)",
)
async def get_feedback_by_agent(
    agent_id: str,
    limit: int = 100,
    offset: int = 0,
    repo: FeedbackRepository = Depends(get_feedback_repository),
) -> List[FeedbackResponse]:
    """Get audit logs for agent with pagination."""
    audit_logs = repo.get_audit_logs_by_agent(agent_id, limit=limit, offset=offset)
    
    return [
        FeedbackResponse(
            id=log.id,
            agent_id=log.agent_id,
            event_id=log.event_id,
            decision=log.decision,
            user_action=log.user_action,
            reason_code=log.reason_code,
            feedback_timestamp=log.feedback_timestamp,
            created_at=log.created_at.isoformat() if log.created_at else None,
        )
        for log in audit_logs
    ]


@router.get(
    "/feedback/stats",
    response_model=Dict[str, Any],
    summary="Get Feedback Statistics",
    description="Get aggregate statistics about audit logs",
)
async def get_feedback_stats(
    agent_id: Optional[str] = None,
    repo: FeedbackRepository = Depends(get_feedback_repository),
) -> Dict[str, Any]:
    """Get statistics about feedback."""
    decision_counts = repo.count_by_decision(agent_id=agent_id)
    user_action_counts = repo.count_by_user_action(agent_id=agent_id)
    
    total = sum(decision_counts.values())
    
    return {
        "agent_id": agent_id or "all",
        "total_logs": total,
        "decision_counts": decision_counts,
        "user_action_counts": user_action_counts,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# TODO FEATURES FOR FUTURE STEPS
# ============================================================================

# TODO: Implement bulk feedback ingestion for performance
# TODO: Add feedback deduplication (same event + agent within time window)
# TODO: Add hook for retraining pipeline (when threshold of BLOCK overrides reached)
# TODO: Add admin policy tuning endpoint (change thresholds based on audit data)
# TODO: Add rate limiting for feedback submissions (detect noisy agents)
# TODO: Add audit log export/archival to cold storage
# TODO: Add analytics dashboard queries (decision trends, rule effectiveness)
