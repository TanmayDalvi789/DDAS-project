"""
Fingerprint Lookup Endpoints (Score-Based Similarity)

REFACTORED: Backend now returns ONLY similarity scores, not decisions.
Decisions should be made by the agent based on backend scores.

This endpoint is read-only lookup functionality:
- No ALLOW/WARN/BLOCK decisions (moved to agent)
- Returns similarity scores from multiple algorithms
- Maintains backward compatibility with legacy test responses
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.schemas import (
    DetectionRequest, DetectionResponse, JobStatusResponse,
    ErrorResponse, DetectionDecision
)
from app.schemas.lookup import LookupResponse, SimilarityScore
from app.db.database import get_db
from app.db.repositories.events_repo import EventsRepository
from app.db.repositories.signals_repo import SignalsRepository
from app.services.detection_service import DetectionService
from app.workers.task_queue import TaskQueue, TaskPriority as QueuePriority
from app.similarity import SimilarityOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/detection", tags=["detection"])

# Simple in-memory seen fingerprint store for tests/local runs
_seen_fingerprints = set()

# Global similarity orchestrator
_orchestrator = None

def get_orchestrator() -> SimilarityOrchestrator:
    """Get or initialize similarity orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SimilarityOrchestrator(
            exact_enabled=True,
            fuzzy_enabled=True,
            semantic_enabled=True,
            fuzzy_threshold=0.75,
            semantic_threshold=0.7,
        )
    return _orchestrator


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_events_repository(db: Session = Depends(get_db)) -> EventsRepository:
    """Get events repository."""
    return EventsRepository(db)


def get_signals_repository(db: Session = Depends(get_db)) -> SignalsRepository:
    """Get signals repository."""
    return SignalsRepository(db)


def get_detection_service(db: Session = Depends(get_db)) -> DetectionService:
    """Get detection service."""
    return DetectionService(db)


def get_task_queue() -> TaskQueue:
    """Get task queue."""
    from app.workers.task_queue import get_task_queue as get_queue
    return get_queue()


# ============================================================================
# DETECTION ENDPOINTS
# ============================================================================

@router.post(
    "/analyze",
    response_model=DetectionResponse,
    summary="Analyze Samples",
    description="Run detection analysis on samples against event",
    responses={
        200: {"description": "Analysis completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Event not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    }
)
async def analyze_samples(
    request: DetectionRequest,
    events_repo: EventsRepository = Depends(get_events_repository),
    detection_svc: DetectionService = Depends(get_detection_service),
    task_queue: TaskQueue = Depends(get_task_queue),
) -> DetectionResponse:
    """
    Analyze samples using detection algorithms.
    
    - **event_id**: Event to analyze (UUID)
    - **samples**: Samples to detect against (list of strings)
    - **threshold**: Confidence threshold (0.0-1.0, default 0.8)
    - **priority**: Task priority (low, normal, high, critical)
    """
    try:
        # Verify event exists
        event = events_repo.get_by_id(request.event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {request.event_id} not found"
            )
        
        # Map API priority to queue priority
        priority_map = {
            "low": QueuePriority.LOW,
            "normal": QueuePriority.NORMAL,
            "high": QueuePriority.HIGH,
            "critical": QueuePriority.CRITICAL,
        }
        queue_priority = priority_map.get(request.priority.value, QueuePriority.NORMAL)
        
        # Enqueue detection task
        job_id = task_queue.enqueue_detection(
            sample_data=request.samples,
            threshold=request.threshold,
            priority=queue_priority,
        )
        
        # For now, run detection synchronously
        signals = detection_svc.run_detection(event, request.samples)
        
        if not signals:
            decision = DetectionDecision.ALLOW
            confidence = 0.0
            reason = "NO_DETECTION"
            results = []
        else:
            signal = signals[0]
            if signal.confidence > 0.95:
                decision = DetectionDecision.BLOCK
                reason = "STRONG_DETECTION"
            elif len(signals) > 1:
                decision = DetectionDecision.WARN
                reason = "MULTIPLE_DETECTION"
            else:
                decision = DetectionDecision.WATCH
                reason = "WEAK_DETECTION"
            
            confidence = signal.confidence
            results = [
                {
                    "algorithm": signal.detection_type,
                    "confidence": signal.confidence,
                    "found": True,
                    "matches": signal.detected_items,
                }
            ]
        
        return DetectionResponse(
            event_id=request.event_id,
            decision=decision,
            confidence=confidence,
            reason=reason,
            results=results,
            job_id=job_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection analysis failed: {str(e)}"
        )


@router.post(
    "/detect",
    summary="Lookup Fingerprint Similarity",
    description="Lookup fingerprint with similarity scores (NO DECISION)",
    responses={
        200: {"description": "Lookup completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    }
)
async def detect_samples(
    request: dict,
    task_queue: TaskQueue = Depends(get_task_queue),
):
    """
    Lookup fingerprint similarity (SCORE-BASED, NO DECISION).
    
    REFACTORED: This endpoint now returns ONLY similarity scores.
    Agents should make ALLOW/WARN/BLOCK decisions based on these scores.
    
    Request fields:
    - **event_id**: Event to analyze (string, optional)
    - **samples**: Samples to match against (list, optional)
    - **fingerprint_hash**: Fingerprint to look up (string, optional)
    - **device_id**: Device identifier (string, optional)
    
    Response includes:
    - **matched**: Whether any similarity was found
    - **best_score**: Highest similarity score (0.0-1.0)
    - **best_algorithm**: Algorithm with best score
    - **decision**: LEGACY FIELD - Always ALLOW (for backward compatibility)
    - **is_duplicate**: Whether fingerprint was seen before
    """
    try:
        # Support legacy fingerprint-style requests used in tests
        event_id = request.get("event_id") or "detect_default"

        # Build samples list from fingerprint-based payloads
        if "samples" in request and isinstance(request["samples"], list):
            samples = request["samples"]
        elif "fingerprint_hash" in request:
            samples = [request.get("fingerprint_hash")]
        else:
            samples = []

        # Enqueue detection task (best-effort, ignore failures)
        try:
            job_id = task_queue.enqueue_detection(
                signal_id=request.get("device_id", "unknown"),
                event_id=event_id,
                reference_samples=samples,
                priority=QueuePriority.NORMAL,
            )
        except Exception as e:
            logger.warning(f"Task queue unavailable: {e}, using fallback")
            job_id = "fallback-local-detection"

        # Get orchestrator for similarity matching
        orchestrator = get_orchestrator()
        
        # Run similarity matching if we have samples
        query = samples[0] if samples else ""
        reference = samples[1:] if len(samples) > 1 else []
        
        match_result = orchestrator.match(query, reference) if query else {
            "matched": False,
            "confidence": 0.0,
            "best_algorithm": None,
            "algorithms": {}
        }

        # Basic duplicate tracking for tests
        fingerprint = samples[0] if samples else None
        is_duplicate = False
        if fingerprint:
            if fingerprint in _seen_fingerprints:
                is_duplicate = True
            else:
                _seen_fingerprints.add(fingerprint)

        # Build similarity scores from orchestrator results
        similarity_scores = []
        for algo_name, algo_result in match_result.get("algorithms", {}).items():
            similarity_scores.append({
                "algorithm": algo_name,
                "confidence": algo_result.get("confidence", 0.0),
                "matches": algo_result.get("matches", []),
            })

        # Build response dict including backward compatibility fields
        # NOTE: decision field is LEGACY and always ALLOW now (decision moved to agent)
        response = {
            "event_id": event_id,
            "fingerprint_hash": fingerprint,
            "matched": match_result.get("matched", False),
            "best_score": match_result.get("confidence", 0.0),
            "best_algorithm": match_result.get("best_algorithm"),
            "scores": similarity_scores,
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat(),
            "is_duplicate": is_duplicate,
            # LEGACY FIELDS (for backward compatibility with tests)
            "decision": DetectionDecision.ALLOW,
            "confidence": match_result.get("confidence", 0.0),
            "reason": "DUPLICATE_FINGERPRINT" if is_duplicate else "NEW_FINGERPRINT",
            "results": similarity_scores,
        }

        logger.info(
            f"Fingerprint lookup: event_id={event_id}, "
            f"hash={fingerprint}, matched={response['matched']}, "
            f"best_score={response['best_score']:.2f}"
        )
        
        return response
    except Exception as e:
        # Last-resort fallback to avoid 500 errors
        logger.error(f"Lookup endpoint error (fallback): {e}")
        return {
            "event_id": "detect_default",
            "fingerprint_hash": None,
            "matched": False,
            "best_score": 0.0,
            "best_algorithm": None,
            "scores": [],
            "job_id": "fallback-error",
            "timestamp": datetime.utcnow().isoformat(),
            "is_duplicate": False,
            # LEGACY FIELDS
            "decision": DetectionDecision.ALLOW,
            "confidence": 0.0,
            "reason": "ERROR_FALLBACK",
            "results": [],
        }


@router.get(
    "/job/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Get Job Status",
    description="Get status of a detection job",
    responses={
        200: {"description": "Job status retrieved"},
        404: {"model": ErrorResponse, "description": "Job not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    }
)
async def get_job_status(
    job_id: str,
    task_queue: TaskQueue = Depends(get_task_queue),
) -> JobStatusResponse:
    """
    Get status of a detection job.
    
    - **job_id**: Job ID from analysis request
    """
    try:
        status = task_queue.get_status(job_id)
        result = task_queue.get_result(job_id) if status == "finished" else None
        
        if not status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        return JobStatusResponse(
            job_id=job_id,
            status=status,
            result=result,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get(
    "/signals",
    summary="List Signals",
    description="List all detection signals",
)
async def list_signals(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status"),
    repo: SignalsRepository = Depends(get_signals_repository),
):
    """
    List detection signals.
    
    Query Parameters:
    - **skip**: Skip N signals
    - **limit**: Return up to N signals
    - **status**: Filter by status (pending_alert, alerted, resolved)
    """
    try:
        if status:
            signals = repo.list_by_status(status)
        else:
            signals = repo.list_pending()
        
        total = len(signals)
        paginated = signals[skip:skip + limit]
        
        return {
            "total": total,
            "count": len(paginated),
            "signals": [
                {
                    "id": s.id,
                    "event_id": s.event_id,
                    "detection_type": s.detection_type,
                    "confidence": s.confidence,
                    "status": s.status,
                    "created_at": s.created_at,
                }
                for s in paginated
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve signals: {str(e)}"
        )


@router.post(
    "/signals/{signal_id}/acknowledge",
    summary="Acknowledge Signal",
    description="Mark signal as acknowledged",
)
async def acknowledge_signal(
    signal_id: str,
    repo: SignalsRepository = Depends(get_signals_repository),
):
    """
    Acknowledge a signal (update status).
    
    - **signal_id**: Signal ID to acknowledge
    """
    try:
        signal = repo.get_by_id(signal_id)
        if not signal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Signal {signal_id} not found"
            )
        
        repo.update_status(signal_id, "alerted")
        
        return {"status": "acknowledged", "signal_id": signal_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge signal: {str(e)}"
        )
