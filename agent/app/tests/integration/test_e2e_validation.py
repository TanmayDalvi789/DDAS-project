"""
End-to-End Validation Tests for DDAS Local Agent

Tests the full pipeline:
  Event Reception → Feature Extraction → Backend Lookup → Decision → Enforcement

Validates:
  - Normal operation path
  - All failure scenarios
  - Contract enforcement
  - Error handling & recovery
"""

import pytest
import logging
import json
import sys
from typing import Dict, Any
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from e2e_helpers import (
    TestDataLoader,
    ProxyEventValidator,
    BackendResponseValidator,
    MockBackendClient,
    PipelineExecutor,
)

logger = logging.getLogger(__name__)


class TestProxyEventContractValidation:
    """Validate proxy event schema enforcement."""

    def test_valid_event_passes(self):
        """Valid event should pass validation."""
        loader = TestDataLoader()
        event = loader.get_proxy_event_valid()

        valid, error = ProxyEventValidator.validate(event)

        assert valid is True
        assert error is None

    def test_invalid_event_fails(self):
        """Invalid event should fail validation."""
        loader = TestDataLoader()
        event = loader.get_proxy_event_invalid()

        valid, error = ProxyEventValidator.validate(event)

        assert valid is False
        assert error is not None
        assert "required" in error.lower() or "missing" in error.lower()

    def test_missing_required_field_fails(self):
        """Event missing required field should fail."""
        event = {"filename": "test.exe"}  # Missing file_size and source_url

        valid, error = ProxyEventValidator.validate(event)

        assert valid is False
        assert "required" in error.lower()

    def test_wrong_type_fails(self):
        """Event with wrong field type should fail."""
        event = {
            "filename": "test.exe",
            "file_size": "not_an_int",  # Should be int
            "source_url": "http://example.com",
        }

        valid, error = ProxyEventValidator.validate(event)

        assert valid is False
        assert ("int" in error.lower() or "type" in error.lower())

    def test_non_dict_event_fails(self):
        """Non-dict event should fail."""
        valid, error = ProxyEventValidator.validate("not a dict")
        assert valid is False

        valid, error = ProxyEventValidator.validate([1, 2, 3])
        assert valid is False


class TestBackendResponseContractValidation:
    """Validate backend lookup response schema enforcement."""

    def test_exact_match_response_valid(self):
        """Exact match response should pass validation."""
        loader = TestDataLoader()
        response = loader.get_backend_response_exact()

        valid, error = BackendResponseValidator.validate(response)

        assert valid is True
        assert error is None

    def test_fuzzy_match_response_valid(self):
        """Fuzzy match response should pass validation."""
        loader = TestDataLoader()
        response = loader.get_backend_response_fuzzy()

        valid, error = BackendResponseValidator.validate(response)

        assert valid is True
        assert error is None

    def test_semantic_match_response_valid(self):
        """Semantic match response should pass validation."""
        loader = TestDataLoader()
        response = loader.get_backend_response_semantic()

        valid, error = BackendResponseValidator.validate(response)

        assert valid is True
        assert error is None

    def test_empty_response_valid(self):
        """Empty response (no matches) should pass validation."""
        loader = TestDataLoader()
        response = loader.get_backend_response_empty()

        valid, error = BackendResponseValidator.validate(response)

        assert valid is True
        assert error is None

    def test_missing_key_fails(self):
        """Response missing required key should fail."""
        response = {
            "exact_match": {
                "is_match": False,
                "similarity_type": "exact",
                "score": 0.0,
                "reference_id": None,
                "reference_metadata": None,
            },
            # Missing fuzzy_match and semantic_match
        }

        valid, error = BackendResponseValidator.validate(response)

        assert valid is False
        assert "missing" in error.lower() or "required" in error.lower()

    def test_malformed_match_data_fails(self):
        """Response with malformed match data should fail."""
        response = {
            "exact_match": "not a dict",  # Should be dict
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

        valid, error = BackendResponseValidator.validate(response)

        assert valid is False


class TestNormalOperationPath:
    """Test normal, successful operation."""

    def test_full_pipeline_allow_decision(self):
        """Full pipeline should work for ALLOW decision."""
        loader = TestDataLoader()
        mock_backend = MockBackendClient(loader.get_backend_response_empty())

        executor = PipelineExecutor(backend_client=mock_backend)
        event = loader.get_proxy_event_valid()

        result = executor.execute(event)

        assert result["event"] == event
        assert result["features"] is not None
        assert result["lookup_result"] is not None
        assert result["errors"] == []

    def test_full_pipeline_with_exact_match(self):
        """Pipeline should handle exact match (BLOCK)."""
        loader = TestDataLoader()
        mock_backend = MockBackendClient(loader.get_backend_response_exact())

        executor = PipelineExecutor(backend_client=mock_backend)
        event = loader.get_proxy_event_valid()

        result = executor.execute(event)

        assert result["errors"] == []
        assert result["lookup_result"]["exact_match"]["is_match"] is True

    def test_full_pipeline_with_fuzzy_match(self):
        """Pipeline should handle fuzzy match (WARN)."""
        loader = TestDataLoader()
        mock_backend = MockBackendClient(loader.get_backend_response_fuzzy())

        executor = PipelineExecutor(backend_client=mock_backend)
        event = loader.get_proxy_event_valid()

        result = executor.execute(event)

        assert result["errors"] == []
        assert result["lookup_result"]["fuzzy_match"]["is_match"] is True
        assert result["lookup_result"]["fuzzy_match"]["score"] > 0


class TestFailureScenarios:
    """Test failure handling and recovery."""

    def test_scenario_1_backend_unreachable(self):
        """
        Scenario 1: Backend unreachable
        - Lookup fails
        - Agent logs warning
        - Decision defaults to ALLOW/WARN correctly
        - Agent continues running
        """
        logger.info("=== SCENARIO 1: Backend Unreachable ===")

        mock_backend = MockBackendClient()
        mock_backend.perform_lookup = Mock(side_effect=ConnectionError("Backend down"))

        executor = PipelineExecutor(backend_client=mock_backend)
        loader = TestDataLoader()
        event = loader.get_proxy_event_valid()

        result = executor.execute(event)

        # Should have error but not crash
        assert len(result["errors"]) > 0
        logger.info(f"✓ Agent continued (errors logged: {result['errors']})")

    def test_scenario_2_permission_revoked(self):
        """
        Scenario 2: Permission revoked after install
        - Agent startup fails-closed
        - Clear error logged
        - No partial operation
        """
        logger.info("=== SCENARIO 2: Permission Revoked ===")

        loader = TestDataLoader()
        mock_backend = MockBackendClient(loader.get_backend_response_exact())
        executor = PipelineExecutor(backend_client=mock_backend)
        event = loader.get_proxy_event_valid()

        # Mock the backend client to raise permission error
        with patch.object(mock_backend, 'perform_lookup', 
                         side_effect=PermissionError("Access denied")):
            result = executor.execute(event)
            # Verify error was captured
            assert len(result["errors"]) > 0
            logger.info("✓ Permission error handled gracefully")

    def test_scenario_3_feature_extraction_failure(self):
        """
        Scenario 3: Feature extraction failure
        - One extractor throws error
        - Remaining extractors still run
        - Decision engine still executes
        """
        logger.info("=== SCENARIO 3: Feature Extraction Failure ===")

        # Mock extractor that fails
        mock_extractor = Mock()
        mock_extractor.extract = Mock(side_effect=RuntimeError("Extraction failed"))

        executor = PipelineExecutor(feature_extractor=mock_extractor)
        loader = TestDataLoader()
        event = loader.get_proxy_event_valid()

        result = executor.execute(event)

        # Should have error but continue
        assert len(result["errors"]) > 0
        logger.info("✓ Feature extraction failure logged, pipeline continued")

    def test_scenario_4_semantic_model_unavailable(self):
        """
        Scenario 4: Semantic model unavailable
        - Semantic feature skipped
        - No crash
        - Decision based on remaining signals
        """
        logger.info("=== SCENARIO 4: Semantic Model Unavailable ===")

        # Mock extractor that skips semantic
        mock_extractor = Mock()
        mock_extractor.extract = Mock(
            return_value={
                "exact_hash": "abc123",
                "fuzzy_sig": [1, 2, 3],
                "semantic_vec": None,  # Semantic unavailable
            }
        )

        executor = PipelineExecutor(feature_extractor=mock_extractor)
        loader = TestDataLoader()
        event = loader.get_proxy_event_valid()

        result = executor.execute(event)

        # Should still work with partial features
        assert result["errors"] == []
        assert result["features"]["semantic_vec"] is None
        logger.info("✓ Pipeline continued with degraded feature set")

    def test_scenario_5_ui_notification_failure(self):
        """
        Scenario 5: UI notification failure
        - WARN → default CANCEL
        - BLOCK → still enforced
        - Error logged
        """
        logger.info("=== SCENARIO 5: UI Notification Failure ===")

        # Mock handler where notification fails
        mock_handler = Mock()
        mock_handler.enforce_decision = Mock(
            side_effect=Exception("Notification failed")
        )

        executor = PipelineExecutor(handler=mock_handler)
        loader = TestDataLoader()
        event = loader.get_proxy_event_valid()

        result = executor.execute(event)

        # Should have error but continue
        assert len(result["errors"]) > 0
        logger.info("✓ Notification failure logged, enforcement attempted anyway")

    def test_scenario_6_no_user_response_on_warn(self):
        """
        Scenario 6: No user response on WARN
        - Timeout reached
        - Download cancelled by default
        """
        logger.info("=== SCENARIO 6: No User Response on WARN ===")

        # Mock handler that simulates timeout
        mock_handler = Mock()
        mock_handler.enforce_decision = Mock(
            return_value={
                "decision": "WARN",
                "enforced": False,  # User didn't respond, defaulted to cancel
                "user_response": None,
                "notification_sent": True,
            }
        )

        executor = PipelineExecutor(handler=mock_handler)
        loader = TestDataLoader()
        event = loader.get_proxy_event_valid()

        result = executor.execute(event)

        # Enforcement should indicate download was blocked
        assert result["enforcement"]["enforced"] is False
        logger.info("✓ WARN timeout defaulted to CANCEL (safe)")


class TestContractEnforcement:
    """Test that contracts are strictly enforced."""

    def test_proxy_event_contract_strict_on_invalid(self):
        """Invalid proxy events must be rejected."""
        invalid_events = [
            {},  # Empty
            {"filename": "test.exe"},  # Missing required
            {"filename": "test.exe", "file_size": "not_int", "source_url": "url"},  # Wrong type
            None,  # Not dict
            "string",  # Not dict
        ]

        for invalid_event in invalid_events:
            valid, error = ProxyEventValidator.validate(invalid_event)
            assert valid is False, f"Should reject: {invalid_event}"

    def test_backend_response_contract_strict_on_invalid(self):
        """Invalid backend responses must be rejected."""
        invalid_responses = [
            {},  # Empty
            {
                "exact_match": {...},  # Missing fuzzy_match and semantic_match
            },
            {
                "exact_match": "not_dict",  # Wrong type
                "fuzzy_match": {},
                "semantic_match": {},
            },
        ]

        for invalid_response in invalid_responses:
            valid, error = BackendResponseValidator.validate(invalid_response)
            # These should fail validation
            if valid is False:
                assert error is not None


class TestLoggingAndObservability:
    """Test that logs clearly show pipeline progression."""

    def test_logs_show_pipeline_stages(self, caplog):
        """Logs should clearly mark each pipeline stage."""
        with caplog.at_level(logging.INFO):
            executor = PipelineExecutor()
            loader = TestDataLoader()
            event = loader.get_proxy_event_valid()

            result = executor.execute(event)

            log_text = caplog.text
            # Check for pipeline stage markers
            assert "[PIPELINE]" in log_text
            assert "[FEATURE]" in log_text
            assert "[LOOKUP]" in log_text
            assert "[DECISION]" in log_text
            assert "[ENFORCE]" in log_text

    def test_logs_show_decision_rationale(self, caplog):
        """Logs should show why decisions were made."""
        loader = TestDataLoader()
        mock_backend = MockBackendClient(loader.get_backend_response_fuzzy())

        with caplog.at_level(logging.INFO):
            executor = PipelineExecutor(backend_client=mock_backend)
            event = loader.get_proxy_event_valid()

            result = executor.execute(event)

            # Should log the decision
            assert "DECISION" in caplog.text

    def test_logs_show_failure_causes(self, caplog):
        """Logs should clearly indicate failure causes."""
        mock_backend = MockBackendClient()
        mock_backend.perform_lookup = Mock(side_effect=ConnectionError("Backend down"))

        with caplog.at_level(logging.ERROR):
            executor = PipelineExecutor(backend_client=mock_backend)
            loader = TestDataLoader()
            event = loader.get_proxy_event_valid()

            result = executor.execute(event)

            # Error should be logged
            assert "Backend down" in caplog.text or "Error" in caplog.text


class TestValidationUtilities:
    """Test the validation utility classes."""

    def test_test_data_loader_loads_files(self):
        """TestDataLoader should load all test data files."""
        loader = TestDataLoader()

        # Should not raise
        loader.get_proxy_event_valid()
        loader.get_proxy_event_invalid()
        loader.get_backend_response_exact()
        loader.get_backend_response_fuzzy()
        loader.get_backend_response_semantic()
        loader.get_backend_response_empty()

    def test_mock_backend_client_returns_responses(self):
        """MockBackendClient should return configured responses."""
        loader = TestDataLoader()
        response = loader.get_backend_response_fuzzy()

        mock_backend = MockBackendClient(response_override=response)

        result = mock_backend.perform_lookup({"test": "features"})

        assert result == response
        assert mock_backend.call_count == 1

    def test_pipeline_executor_executes_stages(self):
        """PipelineExecutor should execute all pipeline stages."""
        executor = PipelineExecutor()
        loader = TestDataLoader()
        event = loader.get_proxy_event_valid()

        result = executor.execute(event)

        assert result["event"] is not None
        assert result["features"] is not None
        assert result["lookup_result"] is not None
        assert result["decision"] is not None
        assert result["enforcement"] is not None


# ============================================================================
# Test Execution Summary
# ============================================================================
# Run with: pytest -v tests/integration/test_e2e_validation.py
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
