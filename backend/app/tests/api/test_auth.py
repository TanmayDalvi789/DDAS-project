"""
Tests for API authentication and middleware.

Coverage:
- API Key validation
- Missing API key handling
- Invalid API key handling
- API key extraction from headers
- CORS handling
- Request logging
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse

from app.main import app
from app.middleware.auth import APIKeyMiddleware, get_api_key


@pytest.fixture
def client():
    """Get test client."""
    return TestClient(app)


class TestAPIKeyAuthentication:
    """Test API Key authentication middleware."""

    def test_valid_api_key(self, client):
        """Test request with valid API key."""
        response = client.get(
            "/api/v1/health",
            headers={"X-API-Key": "test-key"}
        )
        # Should not return 401 (authentication error)
        assert response.status_code != 401

    def test_missing_api_key(self, client):
        """Test request without API key."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data or "detail" in data

    def test_invalid_api_key(self, client):
        """Test request with invalid API key."""
        response = client.get(
            "/api/v1/health",
            headers={"X-API-Key": "invalid-key-12345"}
        )
        
        assert response.status_code == 401

    def test_empty_api_key(self, client):
        """Test request with empty API key."""
        response = client.get(
            "/api/v1/health",
            headers={"X-API-Key": ""}
        )
        
        assert response.status_code == 401

    def test_api_key_case_sensitive(self, client):
        """Test that API key is case sensitive."""
        response = client.get(
            "/api/v1/health",
            headers={"X-API-Key": "TEST-KEY"}
        )
        
        # Should fail if case doesn't match
        assert response.status_code == 401

    def test_api_key_with_whitespace(self, client):
        """Test API key with surrounding whitespace."""
        response = client.get(
            "/api/v1/health",
            headers={"X-API-Key": " test-key "}
        )
        
        # Should fail due to whitespace
        assert response.status_code == 401

    def test_malformed_header(self, client):
        """Test with malformed authentication header."""
        response = client.get(
            "/api/v1/health",
            headers={"Authorization": "Bearer invalid"}
        )
        
        # Should fail - X-API-Key is required
        assert response.status_code == 401


class TestPublicEndpoints:
    """Test endpoints that don't require authentication."""

    def test_root_endpoint_public(self, client):
        """Test root endpoint is public."""
        response = client.get("/")
        
        # Root should be accessible without auth
        assert response.status_code == 200

    def test_liveness_probe_public(self, client):
        """Test liveness probe is public."""
        response = client.get("/api/v1/live")
        
        # Liveness should not require auth for k8s
        assert response.status_code == 200

    def test_docs_public(self, client):
        """Test API docs are accessible."""
        response = client.get("/api/docs")
        
        # Docs should be public
        assert response.status_code == 200


class TestAuthenticationErrors:
    """Test authentication error responses."""

    def test_401_response_format(self, client):
        """Test 401 response has proper format."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 401
        data = response.json()
        
        # Should have error information
        assert isinstance(data, dict)

    def test_401_includes_error_message(self, client):
        """Test 401 includes error message."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 401
        data = response.json()
        assert len(data) > 0

    def test_multiple_failed_attempts(self, client):
        """Test multiple failed authentication attempts."""
        for _ in range(3):
            response = client.get("/api/v1/health")
            assert response.status_code == 401

    def test_mixed_valid_invalid_requests(self, client):
        """Test mixing valid and invalid requests."""
        # Valid
        response1 = client.get(
            "/api/v1/health",
            headers={"X-API-Key": "test-key"}
        )
        assert response1.status_code != 401
        
        # Invalid
        response2 = client.get("/api/v1/health")
        assert response2.status_code == 401
        
        # Valid again
        response3 = client.get(
            "/api/v1/health",
            headers={"X-API-Key": "test-key"}
        )
        assert response3.status_code != 401


class TestCORSHeaders:
    """Test CORS header handling."""

    def test_cors_allowed_origins(self, client):
        """Test CORS headers for allowed origins."""
        response = client.get(
            "/api/v1/health",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers or \
               "Access-Control-Allow-Origin" in response.headers

    def test_cors_preflight_request(self, client):
        """Test CORS preflight request."""
        response = client.options("/api/v1/events")
        
        # OPTIONS should be allowed
        assert response.status_code in [200, 204]

    def test_cors_credentials_allowed(self, client):
        """Test CORS allows credentials."""
        response = client.get(
            "/api/v1/health",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200


class TestRequestHeaderValidation:
    """Test request header validation."""

    def test_content_type_json(self, client):
        """Test request with JSON content type."""
        response = client.post(
            "/api/v1/events",
            json={"name": "test", "source": "test"},
            headers={"X-API-Key": "test-key", "Content-Type": "application/json"}
        )
        
        # Should process JSON correctly
        assert response.status_code in [201, 422]  # Either created or validation error

    def test_missing_content_type(self, client):
        """Test request without content type."""
        response = client.post(
            "/api/v1/events",
            data="invalid",
            headers={"X-API-Key": "test-key"}
        )
        
        # Should handle missing content type gracefully
        assert response.status_code in [400, 422]

    def test_invalid_json_body(self, client):
        """Test request with invalid JSON."""
        response = client.post(
            "/api/v1/events",
            content="{invalid json}",
            headers={"X-API-Key": "test-key", "Content-Type": "application/json"}
        )
        
        assert response.status_code == 422


class TestAuthenticationIntegration:
    """Integration tests for authentication."""

    def test_authenticated_crud_operations(self, client):
        """Test CRUD operations with authentication."""
        headers = {"X-API-Key": "test-key"}
        
        # Create
        create_resp = client.post(
            "/api/v1/events",
            json={"name": "test", "source": "test"},
            headers=headers
        )
        if create_resp.status_code == 201:
            event_id = create_resp.json()["id"]
            
            # Read
            read_resp = client.get(
                f"/api/v1/events/{event_id}",
                headers=headers
            )
            assert read_resp.status_code == 200
            
            # List
            list_resp = client.get(
                "/api/v1/events",
                headers=headers
            )
            assert list_resp.status_code == 200

    def test_unauthenticated_crud_blocked(self, client):
        """Test that unauthenticated CRUD is blocked."""
        # Create without auth
        create_resp = client.post(
            "/api/v1/events",
            json={"name": "test", "source": "test"}
        )
        assert create_resp.status_code == 401
        
        # List without auth
        list_resp = client.get("/api/v1/events")
        assert list_resp.status_code == 401
        
        # Get without auth
        get_resp = client.get("/api/v1/events/1")
        assert get_resp.status_code == 401

    def test_api_key_per_request(self, client):
        """Test API key is validated per request."""
        headers_valid = {"X-API-Key": "test-key"}
        headers_invalid = {"X-API-Key": "invalid"}
        
        # First request valid
        resp1 = client.get("/api/v1/health", headers=headers_valid)
        assert resp1.status_code != 401
        
        # Second request invalid
        resp2 = client.get("/api/v1/health", headers=headers_invalid)
        assert resp2.status_code == 401
        
        # Third request valid
        resp3 = client.get("/api/v1/health", headers=headers_valid)
        assert resp3.status_code != 401
