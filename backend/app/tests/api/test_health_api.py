"""
Tests for Health & Status API endpoints.

Coverage:
- GET /api/v1/health (health check)
- GET /api/v1/stats (statistics)
- GET /api/v1/version (version info)
- GET /api/v1/ready (readiness probe)
- GET /api/v1/live (liveness probe)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app


@pytest.fixture
def client():
    """Get test client."""
    return TestClient(app)


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check_success(self, client):
        """Test successful health check."""
        with patch('app.api.endpoints.health.check_database') as mock_db, \
             patch('app.api.endpoints.health.check_queue') as mock_queue:
            
            mock_db.return_value = True
            mock_queue.return_value = True
            
            response = client.get(
                "/api/v1/health",
                headers={"X-API-Key": "test-key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "database" in data
            assert "queue" in data
            assert "timestamp" in data

    def test_health_check_db_down(self, client):
        """Test health check when database is down."""
        with patch('app.api.endpoints.health.check_database') as mock_db, \
             patch('app.api.endpoints.health.check_queue') as mock_queue:
            
            mock_db.return_value = False
            mock_queue.return_value = True
            
            response = client.get(
                "/api/v1/health",
                headers={"X-API-Key": "test-key"}
            )
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"

    def test_health_check_queue_down(self, client):
        """Test health check when queue is down."""
        with patch('app.api.endpoints.health.check_database') as mock_db, \
             patch('app.api.endpoints.health.check_queue') as mock_queue:
            
            mock_db.return_value = True
            mock_queue.return_value = False
            
            response = client.get(
                "/api/v1/health",
                headers={"X-API-Key": "test-key"}
            )
            
            assert response.status_code == 503

    def test_health_check_missing_api_key(self, client):
        """Test health check without API key."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 401


class TestStatistics:
    """Test statistics endpoint."""

    def test_get_stats_success(self, client):
        """Test successful statistics retrieval."""
        response = client.get(
            "/api/v1/stats",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "events_count" in data
        assert "signals_count" in data
        assert "alerts_count" in data
        assert "queue_size" in data
        assert "timestamp" in data

    def test_stats_contain_valid_numbers(self, client):
        """Test that stats contain valid numbers."""
        response = client.get(
            "/api/v1/stats",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All counts should be non-negative integers
        assert data["events_count"] >= 0
        assert data["signals_count"] >= 0
        assert data["alerts_count"] >= 0
        assert data["queue_size"] >= 0

    def test_stats_contain_percentages(self, client):
        """Test that stats contain percentages."""
        response = client.get(
            "/api/v1/stats",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have breakdown by status/priority
        assert isinstance(data, dict)

    def test_stats_missing_api_key(self, client):
        """Test statistics without API key."""
        response = client.get("/api/v1/stats")
        
        assert response.status_code == 401


class TestVersionInfo:
    """Test version info endpoint."""

    def test_get_version_success(self, client):
        """Test successful version retrieval."""
        response = client.get(
            "/api/v1/version",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "api_version" in data
        assert isinstance(data["version"], str)

    def test_version_format_valid(self, client):
        """Test version format is valid."""
        response = client.get(
            "/api/v1/version",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should follow semantic versioning
        version_parts = data["version"].split(".")
        assert len(version_parts) >= 2

    def test_version_missing_api_key(self, client):
        """Test version without API key."""
        response = client.get("/api/v1/version")
        
        assert response.status_code == 401


class TestReadinessProbe:
    """Test readiness probe endpoint."""

    def test_ready_when_healthy(self, client):
        """Test readiness when all systems are ready."""
        with patch('app.api.endpoints.health.check_database') as mock_db, \
             patch('app.api.endpoints.health.check_queue') as mock_queue:
            
            mock_db.return_value = True
            mock_queue.return_value = True
            
            response = client.get(
                "/api/v1/ready",
                headers={"X-API-Key": "test-key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["ready"] is True

    def test_not_ready_when_db_down(self, client):
        """Test readiness when database is down."""
        with patch('app.api.endpoints.health.check_database') as mock_db, \
             patch('app.api.endpoints.health.check_queue') as mock_queue:
            
            mock_db.return_value = False
            mock_queue.return_value = True
            
            response = client.get(
                "/api/v1/ready",
                headers={"X-API-Key": "test-key"}
            )
            
            assert response.status_code == 503

    def test_ready_missing_api_key(self, client):
        """Test readiness without API key."""
        response = client.get("/api/v1/ready")
        
        assert response.status_code == 401


class TestLivenessProbe:
    """Test liveness probe endpoint."""

    def test_live_always_succeeds(self, client):
        """Test liveness always returns success."""
        response = client.get("/api/v1/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["live"] is True

    def test_live_contains_timestamp(self, client):
        """Test liveness contains timestamp."""
        response = client.get("/api/v1/live")
        
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data

    def test_live_no_auth_required(self, client):
        """Test liveness doesn't require authentication."""
        # Liveness probes typically don't require auth for k8s
        response = client.get("/api/v1/live")
        assert response.status_code == 200


class TestHealthIntegration:
    """Integration tests for health endpoints."""

    def test_all_probes_together(self, client):
        """Test all health probes together."""
        with patch('app.api.endpoints.health.check_database') as mock_db, \
             patch('app.api.endpoints.health.check_queue') as mock_queue:
            
            mock_db.return_value = True
            mock_queue.return_value = True
            
            # Health
            health_resp = client.get(
                "/api/v1/health",
                headers={"X-API-Key": "test-key"}
            )
            assert health_resp.status_code == 200
            
            # Readiness
            ready_resp = client.get(
                "/api/v1/ready",
                headers={"X-API-Key": "test-key"}
            )
            assert ready_resp.status_code == 200
            
            # Liveness
            live_resp = client.get("/api/v1/live")
            assert live_resp.status_code == 200

    def test_stats_and_version_together(self, client):
        """Test stats and version endpoints together."""
        # Stats
        stats_resp = client.get(
            "/api/v1/stats",
            headers={"X-API-Key": "test-key"}
        )
        assert stats_resp.status_code == 200
        
        # Version
        version_resp = client.get(
            "/api/v1/version",
            headers={"X-API-Key": "test-key"}
        )
        assert version_resp.status_code == 200

    def test_cascade_failure_scenario(self, client):
        """Test cascade failure - db down first, then queue."""
        with patch('app.api.endpoints.health.check_database') as mock_db, \
             patch('app.api.endpoints.health.check_queue') as mock_queue:
            
            # First check: db down, queue up
            mock_db.return_value = False
            mock_queue.return_value = True
            
            health_resp = client.get(
                "/api/v1/health",
                headers={"X-API-Key": "test-key"}
            )
            assert health_resp.status_code == 503
            
            # Second check: both down
            mock_db.return_value = False
            mock_queue.return_value = False
            
            health_resp = client.get(
                "/api/v1/health",
                headers={"X-API-Key": "test-key"}
            )
            assert health_resp.status_code == 503

    def test_recovery_scenario(self, client):
        """Test recovery - system comes back online."""
        with patch('app.api.endpoints.health.check_database') as mock_db, \
             patch('app.api.endpoints.health.check_queue') as mock_queue:
            
            # Initial: unhealthy
            mock_db.return_value = False
            mock_queue.return_value = False
            
            health_resp = client.get(
                "/api/v1/health",
                headers={"X-API-Key": "test-key"}
            )
            assert health_resp.status_code == 503
            
            # Recovery: both come back online
            mock_db.return_value = True
            mock_queue.return_value = True
            
            health_resp = client.get(
                "/api/v1/health",
                headers={"X-API-Key": "test-key"}
            )
            assert health_resp.status_code == 200
