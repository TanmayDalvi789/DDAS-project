"""
End-to-End Validation Helpers

Shared utilities for integration tests and demo runners.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class ProxyEventValidator:
    """Validate proxy event structure."""

    REQUIRED_FIELDS = {
        "filename": str,
        "file_size": int,
        "source_url": str,
    }

    OPTIONAL_FIELDS = {
        "event_id": str,
        "timestamp": str,
        "content_hash": str,
        "mime_type": str,
        "user_id": str,
        "download_location": str,
        "browser": str,
        "ip_address": str,
    }

    @classmethod
    def validate(cls, event: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate proxy event schema.

        Returns:
            (is_valid, error_message)
        """
        if not isinstance(event, dict):
            return False, f"Event must be dict, got {type(event)}"

        # Check required fields
        for field, expected_type in cls.REQUIRED_FIELDS.items():
            if field not in event:
                return False, f"Missing required field: {field}"
            if not isinstance(event[field], expected_type):
                return False, f"Field {field} must be {expected_type.__name__}, got {type(event[field]).__name__}"

        # Optional fields are just logged if invalid
        for field, expected_type in cls.OPTIONAL_FIELDS.items():
            if field in event and not isinstance(event[field], expected_type):
                logger.warning(
                    f"Optional field {field} has wrong type: expected {expected_type.__name__}, "
                    f"got {type(event[field]).__name__}. Will skip this field."
                )

        return True, None


class BackendResponseValidator:
    """Validate backend lookup response schema."""

    REQUIRED_KEYS = {"exact_match", "fuzzy_match", "semantic_match"}

    MATCH_SCHEMA = {
        "is_match": bool,
        "similarity_type": str,
        "score": (int, float),
        "reference_id": (str, type(None)),
        "reference_metadata": (dict, type(None)),
    }

    @classmethod
    def validate(cls, response: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate backend lookup response schema.

        Returns:
            (is_valid, error_message)
        """
        if not isinstance(response, dict):
            return False, f"Response must be dict, got {type(response)}"

        # Check required keys
        if not cls.REQUIRED_KEYS.issubset(response.keys()):
            missing = cls.REQUIRED_KEYS - set(response.keys())
            return False, f"Missing required keys: {missing}"

        # Check each match type structure
        for match_type in cls.REQUIRED_KEYS:
            match_data = response[match_type]

            if not isinstance(match_data, dict):
                return False, f"{match_type} must be dict, got {type(match_data)}"

            for field, expected_type in cls.MATCH_SCHEMA.items():
                if field not in match_data:
                    return False, f"{match_type}.{field} is required"

                value = match_data[field]
                if not isinstance(value, expected_type):
                    return False, (
                        f"{match_type}.{field} must be {expected_type}, "
                        f"got {type(value)}"
                    )

        return True, None


class TestDataLoader:
    """Load test data files."""

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize loader.

        Args:
            data_dir: Directory containing test data files.
                     Defaults to <package>/data
        """
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"
        self.data_dir = data_dir

    def load_json(self, filename: str) -> Dict[str, Any]:
        """Load JSON test data file."""
        filepath = self.data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Test data not found: {filepath}")
        with open(filepath) as f:
            return json.load(f)

    def get_proxy_event_valid(self) -> Dict[str, Any]:
        """Load valid proxy event."""
        return self.load_json("test_proxy_event_valid.json")

    def get_proxy_event_invalid(self) -> Dict[str, Any]:
        """Load invalid proxy event."""
        return self.load_json("test_proxy_event_invalid.json")

    def get_backend_response_exact(self) -> Dict[str, Any]:
        """Load backend response with exact match."""
        return self.load_json("test_backend_response_exact.json")

    def get_backend_response_fuzzy(self) -> Dict[str, Any]:
        """Load backend response with fuzzy match."""
        return self.load_json("test_backend_response_fuzzy.json")

    def get_backend_response_semantic(self) -> Dict[str, Any]:
        """Load backend response with semantic match."""
        return self.load_json("test_backend_response_semantic.json")

    def get_backend_response_empty(self) -> Dict[str, Any]:
        """Load backend response with no matches."""
        return self.load_json("test_backend_response_empty.json")


class MockBackendClient:
    """
    Mock backend client for testing.

    Simulates backend lookup without making actual HTTP requests.
    """

    def __init__(self, response_override: Optional[Dict[str, Any]] = None):
        """
        Initialize mock client.

        Args:
            response_override: If provided, always return this response.
        """
        self.response_override = response_override
        self.last_request = None
        self.call_count = 0

    def perform_lookup(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Mock backend lookup."""
        self.call_count += 1
        self.last_request = features

        if self.response_override is not None:
            return self.response_override

        # Default: no matches
        return {
            "exact_match": {
                "is_match": False,
                "similarity_type": "exact",
                "score": 0.0,
                "reference_id": None,
                "reference_metadata": None,
            },
            "fuzzy_match": {
                "is_match": False,
                "similarity_type": "fuzzy",
                "score": 0.0,
                "reference_id": None,
                "reference_metadata": None,
            },
            "semantic_match": {
                "is_match": False,
                "similarity_type": "semantic",
                "score": 0.0,
                "reference_id": None,
                "reference_metadata": None,
            },
        }


class PipelineExecutor:
    """Execute full event processing pipeline for testing."""

    def __init__(
        self,
        feature_extractor=None,
        backend_client=None,
        decision_engine=None,
        handler=None,
    ):
        """
        Initialize executor with pipeline components.

        Args:
            feature_extractor: Feature extraction module
            backend_client: Backend client (real or mock)
            decision_engine: Decision engine
            handler: Event handler
        """
        self.feature_extractor = feature_extractor
        self.backend_client = backend_client
        self.decision_engine = decision_engine
        self.handler = handler

    def execute(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute full pipeline.

        Returns:
            Pipeline result with all stages
        """
        logger.info("[PIPELINE] Starting execution")

        # Validate input
        valid, error = ProxyEventValidator.validate(event)
        if not valid:
            logger.error(f"[PIPELINE] Invalid event: {error}")
            raise ValueError(f"Invalid event: {error}")

        # Execute full pipeline
        result = {
            "event": event,
            "features": None,
            "lookup_result": None,
            "decision": None,
            "decision_result": None,
            "enforcement": None,
            "errors": [],
        }

        try:
            # Feature extraction
            logger.info("[FEATURE] Starting extraction")
            if self.feature_extractor:
                result["features"] = self.feature_extractor.extract(event)
            else:
                result["features"] = self._extract_features_minimal(event)
            logger.info("[FEATURE] Extraction complete")

            # Backend lookup
            logger.info("[LOOKUP] Starting backend lookup")
            if self.backend_client:
                result["lookup_result"] = self.backend_client.perform_lookup(
                    result["features"]
                )
            else:
                result["lookup_result"] = {}
            logger.info("[LOOKUP] Backend lookup complete")

            # Decision
            logger.info("[DECISION] Starting decision engine")
            if self.decision_engine:
                decision, decision_result = self.decision_engine.decide(
                    event, result["features"], result["lookup_result"]
                )
                result["decision"] = decision
                result["decision_result"] = decision_result
            else:
                result["decision"] = "ALLOW"
                result["decision_result"] = {"explanation": "Mock decision"}
            logger.info(f"[DECISION] {result['decision']}")

            # Enforcement
            logger.info("[ENFORCE] Starting enforcement")
            if self.handler:
                result["enforcement"] = self.handler.enforce_decision(
                    decision=result["decision"],
                    decision_result=result["decision_result"],
                    filename=event.get("filename", "unknown"),
                )
            else:
                result["enforcement"] = {
                    "decision": result["decision"],
                    "enforced": True,
                    "user_response": None,
                }
            logger.info(f"[ENFORCE] Complete (enforced={result['enforcement']['enforced']})")

        except Exception as e:
            logger.error(f"[PIPELINE] Error: {e}")
            result["errors"].append(str(e))

        return result

    @staticmethod
    def _extract_features_minimal(event: Dict[str, Any]) -> Dict[str, Any]:
        """Extract minimal features (when extractor unavailable)."""
        return {
            "exact_hash": event.get("content_hash", ""),
            "fuzzy_sig": [],
            "semantic_vec": [],
        }
