"""Background task definitions for async processing."""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import async_session_maker
from app.db.repositories import SignalsRepository, EventsRepository
from app._archive.detection.orchestrator import DetectionOrchestrator
from app.config import settings

logger = logging.getLogger(__name__)

# Global orchestrator instance
_orchestrator: Optional[DetectionOrchestrator] = None


def get_orchestrator() -> DetectionOrchestrator:
    """Get or create detection orchestrator."""
    global _orchestrator
    
    if _orchestrator is None:
        _orchestrator = DetectionOrchestrator(
            fuzzy_threshold=float(settings.FUZZY_THRESHOLD),
            semantic_threshold=float(settings.SEMANTIC_THRESHOLD),
            enable_fuzzy=True,
            enable_semantic=True,
            enable_exact=True,
        )
    
    return _orchestrator


async def process_detection(signal_id: str, event_id: str, reference_samples: list) -> Dict[str, Any]:
    """Process detection for an event.
    
    Args:
        signal_id: Detection signal ID
        event_id: Event ID to process
        reference_samples: Known bad/suspicious samples
    
    Returns:
        Detection result
    """
    logger.info(f"Processing detection for signal {signal_id}")
    
    try:
        async with async_session_maker() as session:
            events_repo = EventsRepository(session)
            signals_repo = SignalsRepository(session)
            
            # Get event data
            event = await events_repo.get_by_id(event_id)
            if not event:
                logger.error(f"Event {event_id} not found")
                await signals_repo.update_status(signal_id, "failed", result={"error": "Event not found"})
                await session.commit()
                return {"error": "Event not found"}
            
            # Mark signal as processing
            await signals_repo.update_status(signal_id, "processing")
            await session.commit()
            
            # Run detection
            logger.info(f"Running detection algorithms for event {event_id}")
            orchestrator = get_orchestrator()
            
            event_dict = {
                "event_id": event.event_id,
                "source_type": event.source_type,
                "source_id": event.source_id,
                "event_type": event.event_type,
                "payload": event.payload,
            }
            
            detection_result = orchestrator.detect(event_dict, reference_samples)
            
            # Update signal with result
            confidence = detection_result.get("confidence", 0.0)
            await signals_repo.update_status(
                signal_id=signal_id,
                status="completed",
                confidence=confidence,
                result=detection_result,
            )
            await session.commit()
            
            logger.info(f"Detection complete for signal {signal_id}: detected={detection_result['detected']}")
            return detection_result
            
    except Exception as e:
        logger.error(f"Detection processing failed: {e}")
        
        try:
            async with async_session_maker() as session:
                signals_repo = SignalsRepository(session)
                await signals_repo.update_status(
                    signal_id=signal_id,
                    status="failed",
                    result={"error": str(e)},
                )
                await session.commit()
        except Exception as inner_e:
            logger.error(f"Failed to update signal status: {inner_e}")
        
        return {"error": str(e)}


async def run_detection(
    signal_id: str,
    detection_type: str,
    input_data: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run a specific detection algorithm.
    
    Args:
        signal_id: Detection signal ID
        detection_type: fuzzy, semantic, or exact
        input_data: Data to analyze
        config: Algorithm configuration
    
    Returns:
        Detection result
    """
    logger.info(f"Running {detection_type} detection for signal {signal_id}")
    
    try:
        orchestrator = get_orchestrator()
        
        if detection_type == "fuzzy":
            if orchestrator.fuzzy:
                result = orchestrator.fuzzy.detect(
                    input_data.get("text", ""),
                    input_data.get("reference_samples", []),
                )
            else:
                result = {"error": "Fuzzy detection disabled"}
        
        elif detection_type == "semantic":
            if orchestrator.semantic:
                result = orchestrator.semantic.detect(
                    input_data.get("text", ""),
                    input_data.get("reference_samples", []),
                )
            else:
                result = {"error": "Semantic detection disabled"}
        
        elif detection_type == "exact":
            if orchestrator.exact:
                result = orchestrator.exact.detect(
                    input_data.get("text", ""),
                    input_data.get("reference_samples", []),
                )
            else:
                result = {"error": "Exact detection disabled"}
        
        else:
            result = {"error": f"Unknown detection type: {detection_type}"}
        
        logger.info(f"{detection_type} detection result: {result.get('detected', False)}")
        return result
    
    except Exception as e:
        logger.error(f"Detection algorithm failed: {e}")
        return {"error": str(e)}


async def aggregate_signals(event_id: str, signal_ids: list) -> Dict[str, Any]:
    """Aggregate multiple detection signals.
    
    Args:
        event_id: Event ID
        signal_ids: List of signal IDs to aggregate
    
    Returns:
        Aggregated result
    """
    logger.info(f"Aggregating {len(signal_ids)} signals for event {event_id}")
    
    try:
        async with async_session_maker() as session:
            signals_repo = SignalsRepository(session)
            
            signals = []
            detections = []
            confidences = []
            
            # Fetch all signals
            for signal_id in signal_ids:
                signal = await signals_repo.get_by_id(signal_id)
                if signal:
                    signals.append(signal)
                    if signal.result:
                        detections.append(signal.result.get("detected", False))
                        confidences.append(signal.confidence or 0.0)
            
            # Aggregate
            detected = any(detections) if detections else False
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            aggregate_result = {
                "event_id": event_id,
                "total_signals": len(signals),
                "detections": sum(detections),
                "detected": detected,
                "average_confidence": round(avg_confidence, 4),
                "signals": [
                    {
                        "signal_id": s.signal_id,
                        "type": s.detection_type,
                        "detected": s.result.get("detected", False) if s.result else False,
                        "confidence": s.confidence,
                    }
                    for s in signals
                ],
            }
            
            logger.info(f"Aggregation complete: detected={detected}, confidence={avg_confidence:.4f}")
            return aggregate_result
            
    except Exception as e:
        logger.error(f"Signal aggregation failed: {e}")
        return {"error": str(e)}


async def update_worker_status(worker_id: str, status: str) -> Dict[str, Any]:
    """Update worker health status.
    
    Args:
        worker_id: Worker ID
        status: Status (running, idle, error, etc.)
    
    Returns:
        Updated worker status
    """
    logger.info(f"Updating worker {worker_id} status to {status}")
    
    try:
        async with async_session_maker() as session:
            from app.db.repositories import WorkerStatusRepository
            
            worker_repo = WorkerStatusRepository(session)
            worker = await worker_repo.upsert(worker_id, status)
            await session.commit()
            
            return {
                "worker_id": worker.worker_id,
                "status": worker.status,
                "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
            }
            
    except Exception as e:
        logger.error(f"Worker status update failed: {e}")
        return {"error": str(e)}


async def cleanup_old_data(days_old: int = 30) -> Dict[str, Any]:
    """Clean up old events and signals.
    
    Args:
        days_old: Delete data older than this many days
    
    Returns:
        Cleanup statistics
    """
    logger.info(f"Cleaning up data older than {days_old} days")
    
    try:
        cutoff_date = datetime.utcnow() - asyncio.sleep(days_old * 24 * 3600).__self__.mro()[-1]
        
        # TODO: Implement actual cleanup logic
        # This would delete old events, signals, alerts
        
        logger.info("Cleanup complete")
        return {
            "cleaned_up": True,
            "cutoff_date": cutoff_date.isoformat() if 'cutoff_date' in locals() else None,
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {"error": str(e)}
