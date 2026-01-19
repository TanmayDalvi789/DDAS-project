"""Detection orchestrator - coordinates all detection algorithms."""

from typing import Dict, List, Any, Optional
from app.detection.fuzzy_detection import FuzzyDetection
from app.detection.semantic_detection import SemanticDetection
from app.detection.exact_detection import ExactDetection
from app.db.repositories import SignalsRepository
import logging
import json

logger = logging.getLogger(__name__)


class DetectionOrchestrator:
    """Coordinates multiple detection algorithms.
    
    Runs fuzzy, semantic, and exact matching in parallel or sequence
    and aggregates results.
    """
    
    def __init__(
        self,
        fuzzy_threshold: float = 0.85,
        semantic_threshold: float = 0.80,
        enable_fuzzy: bool = True,
        enable_semantic: bool = True,
        enable_exact: bool = True,
    ):
        """Initialize detection orchestrator.
        
        Args:
            fuzzy_threshold: Fuzzy matching threshold
            semantic_threshold: Semantic matching threshold
            enable_fuzzy: Enable fuzzy detection
            enable_semantic: Enable semantic detection
            enable_exact: Enable exact detection
        """
        self.enable_fuzzy = enable_fuzzy
        self.enable_semantic = enable_semantic
        self.enable_exact = enable_exact
        
        self.fuzzy = FuzzyDetection(threshold=fuzzy_threshold) if enable_fuzzy else None
        self.semantic = SemanticDetection(threshold=semantic_threshold) if enable_semantic else None
        self.exact = ExactDetection() if enable_exact else None
        
        logger.info(
            f"DetectionOrchestrator initialized: "
            f"fuzzy={enable_fuzzy}, semantic={enable_semantic}, exact={enable_exact}"
        )
    
    def detect(
        self,
        event_data: Dict[str, Any],
        reference_samples: List[str],
        detection_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run all enabled detection algorithms.
        
        Args:
            event_data: Event to analyze
            reference_samples: Known bad/suspicious samples
            detection_config: Optional configuration overrides
        
        Returns:
            Aggregated detection results
        """
        logger.info(f"Running detection orchestration on event")
        
        config = detection_config or {}
        input_text = self._extract_text_from_event(event_data)
        
        results = {
            "event_id": event_data.get("event_id", "unknown"),
            "input_text": input_text,
            "algorithms_run": [],
            "individual_results": {},
            "aggregate_result": None,
            "confidence": 0.0,
            "detected": False,
        }
        
        # Run fuzzy detection
        if self.enable_fuzzy and self.fuzzy:
            try:
                fuzzy_result = self.fuzzy.detect(input_text, reference_samples)
                results["individual_results"]["fuzzy"] = fuzzy_result
                results["algorithms_run"].append("fuzzy")
                logger.debug(f"Fuzzy detection: {fuzzy_result['detected']}")
            except Exception as e:
                logger.error(f"Fuzzy detection failed: {e}")
        
        # Run semantic detection
        if self.enable_semantic and self.semantic:
            try:
                semantic_result = self.semantic.detect(input_text, reference_samples)
                results["individual_results"]["semantic"] = semantic_result
                results["algorithms_run"].append("semantic")
                logger.debug(f"Semantic detection: {semantic_result['detected']}")
            except Exception as e:
                logger.error(f"Semantic detection failed: {e}")
        
        # Run exact detection
        if self.enable_exact and self.exact:
            try:
                exact_result = self.exact.detect(input_text, reference_samples)
                results["individual_results"]["exact"] = exact_result
                results["algorithms_run"].append("exact")
                logger.debug(f"Exact detection: {exact_result['detected']}")
            except Exception as e:
                logger.error(f"Exact detection failed: {e}")
        
        # Aggregate results
        results = self._aggregate_results(results)
        
        logger.info(
            f"Detection complete: detected={results['detected']}, "
            f"confidence={results['confidence']:.4f}"
        )
        
        return results
    
    def _extract_text_from_event(self, event_data: Dict[str, Any]) -> str:
        """Extract text content from event data."""
        # Try common fields
        if "payload" in event_data:
            payload = event_data["payload"]
            if isinstance(payload, dict):
                # Join all string values
                values = []
                for v in payload.values():
                    if isinstance(v, str):
                        values.append(v)
                return " ".join(values)
            elif isinstance(payload, str):
                return payload
        
        if "text" in event_data:
            return str(event_data["text"])
        
        if "content" in event_data:
            return str(event_data["content"])
        
        # Fallback: convert whole event to string
        return json.dumps(event_data)
    
    def _aggregate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate individual detection results.
        
        Strategy:
        - If any algorithm detects with high confidence (>0.9): strong detection
        - If multiple algorithms detect: moderate detection
        - If single algorithm detects: weak detection
        """
        individual = results["individual_results"]
        
        if not individual:
            logger.warning("No detection results to aggregate")
            results["aggregate_result"] = "no_detection"
            return results
        
        # Collect confidence scores
        confidences = []
        detected_algorithms = []
        
        for algo_name, algo_result in individual.items():
            if algo_result.get("detected", False):
                detected_algorithms.append(algo_name)
                confidences.append(algo_result.get("confidence", 0.0))
        
        # Determine overall confidence and detection
        if not confidences:
            results["aggregate_result"] = "no_threat"
            results["detected"] = False
            results["confidence"] = 0.0
        else:
            # Average confidence from detecting algorithms
            avg_confidence = sum(confidences) / len(confidences)
            max_confidence = max(confidences)
            
            # Decision logic
            if max_confidence > 0.95:
                results["aggregate_result"] = "strong_detection"
                results["detected"] = True
                results["confidence"] = max_confidence
            elif len(detected_algorithms) >= 2:
                results["aggregate_result"] = "multiple_detection"
                results["detected"] = True
                results["confidence"] = avg_confidence
            else:
                results["aggregate_result"] = "weak_detection"
                results["detected"] = True
                results["confidence"] = max_confidence
        
        results["algorithms_detected"] = detected_algorithms
        results["detection_reason"] = results["aggregate_result"]
        
        return results
    
    def batch_detect(
        self,
        events: List[Dict[str, Any]],
        reference_samples: List[str],
    ) -> List[Dict[str, Any]]:
        """Run detection on multiple events.
        
        Args:
            events: List of events to analyze
            reference_samples: Known bad samples
        
        Returns:
            List of detection results
        """
        logger.info(f"Batch detection: {len(events)} events")
        
        results = []
        for event in events:
            result = self.detect(event, reference_samples)
            results.append(result)
        
        return results
    
    def update_thresholds(
        self,
        fuzzy_threshold: Optional[float] = None,
        semantic_threshold: Optional[float] = None,
    ) -> None:
        """Update detection thresholds.
        
        Args:
            fuzzy_threshold: New fuzzy matching threshold
            semantic_threshold: New semantic matching threshold
        """
        if fuzzy_threshold is not None and self.fuzzy:
            self.fuzzy.update_threshold(fuzzy_threshold)
            logger.info(f"Updated fuzzy threshold to {fuzzy_threshold}")
        
        if semantic_threshold is not None and self.semantic:
            self.semantic.update_threshold(semantic_threshold)
            logger.info(f"Updated semantic threshold to {semantic_threshold}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            "fuzzy_enabled": self.enable_fuzzy,
            "semantic_enabled": self.enable_semantic,
            "exact_enabled": self.enable_exact,
            "fuzzy_threshold": self.fuzzy.threshold if self.fuzzy else None,
            "semantic_threshold": self.semantic.threshold if self.semantic else None,
            "semantic_model": self.semantic.model_name if self.semantic else None,
        }
