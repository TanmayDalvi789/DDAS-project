"""
Tests for STEP-8: Feedback & Audit Sync (Agent Side)

Tests agent feedback client and integration with event handler.
"""

import pytest
import json
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Agent side
from app.backend_client.feedback_client import (
    FeedbackClient,
    _validate_feedback_payload,
    send_feedback,
)
from app.backend_client.auth import BackendAuth

import logging

logger = logging.getLogger(__name__)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def backend_auth():
    """Create mock backend auth."""
    return BackendAuth(api_key="test-api-key-12345")


@pytest.fixture
def feedback_client(backend_auth):
    """Create feedback client."""
    return FeedbackClient(
        base_url="http://localhost:8001",
        auth=backend_auth
    )


# ============================================================================
# AGENT SIDE TESTS: Feedback Payload Validation
# ============================================================================


class TestFeedbackPayloadValidation:
    """Test feedback payload validation."""
    
    def test_valid_allow_payload(self):
        """Valid ALLOW payload should pass."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            "decision": "ALLOW",
            "user_action": "NONE",
            "reason_code": "NO_MATCH",
            "timestamp": int(time.time()),
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is True
        assert error is None
    
    def test_valid_warn_proceed_payload(self):
        """Valid WARN with PROCEED should pass."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            "decision": "WARN",
            "user_action": "PROCEED",
            "reason_code": "FUZZY_MATCH",
            "timestamp": int(time.time()),
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is True
        assert error is None
    
    def test_valid_warn_cancel_payload(self):
        """Valid WARN with CANCEL should pass."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            "decision": "WARN",
            "user_action": "CANCEL",
            "reason_code": "FUZZY_MATCH",
            "timestamp": int(time.time()),
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is True
        assert error is None
    
    def test_valid_block_payload(self):
        """Valid BLOCK payload should pass."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            "decision": "BLOCK",
            "user_action": "NONE",
            "reason_code": "EXACT_MATCH",
            "timestamp": int(time.time()),
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is True
        assert error is None
    
    def test_invalid_decision(self):
        """Invalid decision should fail."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            "decision": "INVALID",
            "user_action": "NONE",
            "reason_code": "NO_MATCH",
            "timestamp": int(time.time()),
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is False
        assert "INVALID" in error or "must be one of" in error
    
    def test_invalid_user_action(self):
        """Invalid user_action should fail."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            "decision": "ALLOW",
            "user_action": "INVALID",
            "reason_code": "NO_MATCH",
            "timestamp": int(time.time()),
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is False
        assert "user_action" in error
    
    def test_allow_with_non_none_action(self):
        """ALLOW with non-NONE user_action should fail."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            "decision": "ALLOW",
            "user_action": "PROCEED",  # Wrong!
            "reason_code": "NO_MATCH",
            "timestamp": int(time.time()),
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is False
        assert "should have user_action='NONE'" in error
    
    def test_warn_with_none_action(self):
        """WARN with NONE user_action should fail."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            "decision": "WARN",
            "user_action": "NONE",  # Wrong!
            "reason_code": "FUZZY_MATCH",
            "timestamp": int(time.time()),
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is False
        assert "WARN must have user_action" in error
    
    def test_missing_required_field(self):
        """Missing required field should fail."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            # decision is missing
            "user_action": "NONE",
            "reason_code": "NO_MATCH",
            "timestamp": int(time.time()),
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is False
        assert "Missing required fields" in error
    
    def test_empty_agent_id(self):
        """Empty agent_id should fail."""
        payload = {
            "agent_id": "",  # Empty!
            "event_id": "evt_123",
            "decision": "ALLOW",
            "user_action": "NONE",
            "reason_code": "NO_MATCH",
            "timestamp": int(time.time()),
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is False
        assert "agent_id" in error
    
    def test_timestamp_as_iso_string(self):
        """Timestamp as ISO string should pass."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            "decision": "ALLOW",
            "user_action": "NONE",
            "reason_code": "NO_MATCH",
            "timestamp": "2026-01-17T10:00:00Z",
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is True


# ============================================================================
# AGENT SIDE TESTS: Feedback Client
# ============================================================================


class TestFeedbackClient:
    """Test feedback client."""
    
    @patch('app.backend_client.feedback_client.httpx.Client')
    def test_send_feedback_success(self, mock_httpx_client, feedback_client):
        """Feedback should send successfully."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        result = feedback_client.send_feedback(
            agent_id="agent-001",
            event_id="evt_123",
            decision="ALLOW",
            user_action="NONE",
            reason_code="NO_MATCH",
        )
        
        assert result is True
    
    @patch('app.backend_client.feedback_client.httpx.Client')
    def test_send_feedback_failure(self, mock_httpx_client, feedback_client):
        """Feedback should handle failure gracefully."""
        # Mock failure response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        result = feedback_client.send_feedback(
            agent_id="agent-001",
            event_id="evt_123",
            decision="ALLOW",
            user_action="NONE",
            reason_code="NO_MATCH",
        )
        
        assert result is False
    
    @patch('app.backend_client.feedback_client.httpx.Client')
    def test_send_feedback_timeout(self, mock_httpx_client, feedback_client):
        """Feedback should handle timeout gracefully."""
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = \
            Exception("Connection timeout")
        
        result = feedback_client.send_feedback(
            agent_id="agent-001",
            event_id="evt_123",
            decision="ALLOW",
        )
        
        assert result is False
    
    def test_send_feedback_defaults(self, feedback_client):
        """Feedback should use sensible defaults."""
        with patch.object(
            feedback_client,
            '_send_with_httpx',
            return_value=True
        ) as mock_send:
            feedback_client.send_feedback(
                agent_id="agent-001",
                event_id="evt_123",
                decision="BLOCK",
            )
            
            # Check defaults were applied
            call_args = mock_send.call_args[0][0]
            assert call_args["user_action"] == "NONE"
            assert call_args["reason_code"] == "BLOCK"
            assert isinstance(call_args["timestamp"], int)
    
    @patch('app.backend_client.feedback_client.httpx.Client')
    def test_send_feedback_http_201_accepted(self, mock_httpx_client, feedback_client):
        """Should treat 201 as success."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        result = feedback_client.send_feedback(
            agent_id="agent-001",
            event_id="evt_123",
            decision="ALLOW",
        )
        
        assert result is True
    
    @patch('app.backend_client.feedback_client.httpx.Client')
    def test_send_feedback_http_200_accepted(self, mock_httpx_client, feedback_client):
        """Should treat 200 as success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        result = feedback_client.send_feedback(
            agent_id="agent-001",
            event_id="evt_123",
            decision="ALLOW",
        )
        
        assert result is True


# ============================================================================
# INTEGRATION TESTS: Agent Feedback Flows
# ============================================================================


class TestAgentFeedbackFlows:
    """Test complete agent-side feedback flows."""
    
    def test_allow_decision_feedback(self):
        """Test ALLOW decision feedback payload."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            "decision": "ALLOW",
            "user_action": "NONE",
            "reason_code": "NO_MATCH",
            "timestamp": 1705454400,
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is True
    
    def test_warn_proceed_feedback(self):
        """Test WARN with user PROCEED feedback."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            "decision": "WARN",
            "user_action": "PROCEED",
            "reason_code": "FUZZY_MATCH | score=0.82",
            "timestamp": 1705454400,
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is True
    
    def test_warn_cancel_feedback(self):
        """Test WARN with user CANCEL feedback."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            "decision": "WARN",
            "user_action": "CANCEL",
            "reason_code": "SEMANTIC_MATCH | score=0.78",
            "timestamp": 1705454400,
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is True
    
    def test_block_decision_feedback(self):
        """Test BLOCK decision feedback."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            "decision": "BLOCK",
            "user_action": "NONE",
            "reason_code": "EXACT_MATCH | score=1.0",
            "timestamp": 1705454400,
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is True
    
    def test_multipleRule_reason_code(self):
        """Test reason code with multiple triggered rules."""
        payload = {
            "agent_id": "agent-001",
            "event_id": "evt_123",
            "decision": "WARN",
            "user_action": "PROCEED",
            "reason_code": "FUZZY_MATCH + BEHAVIORAL_ANOMALY",
            "timestamp": 1705454400,
        }
        
        valid, error = _validate_feedback_payload(payload)
        assert valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

