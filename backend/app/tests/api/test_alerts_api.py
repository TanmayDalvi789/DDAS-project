"""
Tests for Alerts API endpoints.

Coverage:
- POST /api/v1/alerts (create alert)
- GET /api/v1/alerts (list alerts)
- GET /api/v1/alerts/{alert_id} (get specific alert)
- GET /api/v1/alerts/active/count (count active)
- PUT /api/v1/alerts/{alert_id} (update alert)
- POST /api/v1/alerts/{alert_id}/resolve (resolve alert)
- POST /api/v1/alerts/{alert_id}/escalate (escalate alert)
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.models.alert import Alert, AlertStatus, AlertPriority
from app.db.database import SessionLocal


@pytest.fixture
def client():
    """Get test client."""
    return TestClient(app)


@pytest.fixture
def sample_alert_data():
    """Sample alert creation data."""
    return {
        "title": "Test Alert",
        "description": "Test alert description",
        "source": "test_source",
        "priority": "high",
        "metadata": {"key": "value"},
    }


@pytest.fixture
def create_sample_alert():
    """Create a sample alert in database."""
    db = SessionLocal()
    try:
        alert = Alert(
            title="Sample Alert",
            description="Sample alert for testing",
            source="test_source",
            priority=AlertPriority.HIGH,
            status=AlertStatus.OPEN,
            metadata={"test": "data"},
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        yield alert
    finally:
        db.close()


class TestCreateAlert:
    """Test alert creation endpoint."""

    def test_create_alert_success(self, client, sample_alert_data):
        """Test successful alert creation."""
        response = client.post(
            "/api/v1/alerts",
            json=sample_alert_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_alert_data["title"]
        assert data["source"] == sample_alert_data["source"]
        assert data["priority"] == sample_alert_data["priority"]
        assert data["status"] == "open"
        assert "id" in data

    def test_create_alert_missing_required_field(self, client):
        """Test alert creation with missing required field."""
        invalid_data = {
            "description": "Missing title",
            "source": "test_source",
        }
        
        response = client.post(
            "/api/v1/alerts",
            json=invalid_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    def test_create_alert_invalid_priority(self, client):
        """Test alert creation with invalid priority."""
        invalid_data = {
            "title": "Test",
            "source": "test",
            "priority": "invalid_priority",
        }
        
        response = client.post(
            "/api/v1/alerts",
            json=invalid_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    def test_create_alert_invalid_status(self, client, sample_alert_data):
        """Test alert creation with invalid initial status."""
        sample_alert_data["status"] = "resolved"
        
        response = client.post(
            "/api/v1/alerts",
            json=sample_alert_data,
            headers={"X-API-Key": "test-key"}
        )
        
        # Initial status should be "open"
        assert response.status_code in [201, 422]

    def test_create_alert_missing_api_key(self, client, sample_alert_data):
        """Test alert creation without API key."""
        response = client.post(
            "/api/v1/alerts",
            json=sample_alert_data,
        )
        
        assert response.status_code == 401


class TestListAlerts:
    """Test alert listing endpoint."""

    def test_list_alerts_empty(self, client):
        """Test listing alerts when none exist."""
        response = client.get(
            "/api/v1/alerts",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_alerts_with_pagination(self, client):
        """Test listing alerts with pagination."""
        response = client.get(
            "/api/v1/alerts?limit=10&offset=0",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_alerts_with_status_filter(self, client, create_sample_alert):
        """Test listing alerts with status filter."""
        response = client.get(
            "/api/v1/alerts?status=open",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_alerts_with_priority_filter(self, client, create_sample_alert):
        """Test listing alerts with priority filter."""
        response = client.get(
            "/api/v1/alerts?priority=high",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_alerts_with_source_filter(self, client, create_sample_alert):
        """Test listing alerts with source filter."""
        response = client.get(
            "/api/v1/alerts?source=test_source",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_alerts_invalid_limit(self, client):
        """Test listing alerts with invalid limit."""
        response = client.get(
            "/api/v1/alerts?limit=invalid",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    def test_list_alerts_missing_api_key(self, client):
        """Test listing alerts without API key."""
        response = client.get("/api/v1/alerts")
        
        assert response.status_code == 401


class TestGetAlert:
    """Test get specific alert endpoint."""

    def test_get_alert_success(self, client, create_sample_alert):
        """Test getting specific alert."""
        alert = create_sample_alert
        response = client.get(
            f"/api/v1/alerts/{alert.id}",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == alert.id
        assert data["title"] == alert.title
        assert data["source"] == alert.source

    def test_get_alert_not_found(self, client):
        """Test getting non-existent alert."""
        response = client.get(
            "/api/v1/alerts/99999",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 404

    def test_get_alert_invalid_id(self, client):
        """Test getting alert with invalid ID."""
        response = client.get(
            "/api/v1/alerts/invalid-id",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    def test_get_alert_missing_api_key(self, client, create_sample_alert):
        """Test getting alert without API key."""
        alert = create_sample_alert
        response = client.get(f"/api/v1/alerts/{alert.id}")
        
        assert response.status_code == 401


class TestActiveAlertCount:
    """Test active alert count endpoint."""

    def test_count_active_alerts(self, client, create_sample_alert):
        """Test counting active alerts."""
        response = client.get(
            "/api/v1/alerts/active/count",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)

    def test_count_active_alerts_missing_api_key(self, client):
        """Test counting without API key."""
        response = client.get("/api/v1/alerts/active/count")
        
        assert response.status_code == 401


class TestUpdateAlert:
    """Test alert update endpoint."""

    def test_update_alert_priority(self, client, create_sample_alert):
        """Test updating alert priority."""
        alert = create_sample_alert
        update_data = {
            "priority": "critical",
        }
        
        response = client.put(
            f"/api/v1/alerts/{alert.id}",
            json=update_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == alert.id
        assert data["priority"] == "critical"

    def test_update_alert_status(self, client, create_sample_alert):
        """Test updating alert status."""
        alert = create_sample_alert
        update_data = {
            "status": "acknowledged",
        }
        
        response = client.put(
            f"/api/v1/alerts/{alert.id}",
            json=update_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "acknowledged"

    def test_update_alert_not_found(self, client):
        """Test updating non-existent alert."""
        update_data = {
            "priority": "critical",
        }
        
        response = client.put(
            "/api/v1/alerts/99999",
            json=update_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 404

    def test_update_alert_invalid_priority(self, client, create_sample_alert):
        """Test updating with invalid priority."""
        alert = create_sample_alert
        update_data = {
            "priority": "invalid_priority",
        }
        
        response = client.put(
            f"/api/v1/alerts/{alert.id}",
            json=update_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    def test_update_alert_missing_api_key(self, client, create_sample_alert):
        """Test updating without API key."""
        alert = create_sample_alert
        update_data = {
            "priority": "critical",
        }
        
        response = client.put(
            f"/api/v1/alerts/{alert.id}",
            json=update_data,
        )
        
        assert response.status_code == 401


class TestResolveAlert:
    """Test alert resolution endpoint."""

    def test_resolve_alert_success(self, client, create_sample_alert):
        """Test successful alert resolution."""
        alert = create_sample_alert
        resolve_data = {
            "resolution": "Issue has been fixed",
        }
        
        response = client.post(
            f"/api/v1/alerts/{alert.id}/resolve",
            json=resolve_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == alert.id
        assert data["status"] == "resolved"

    def test_resolve_alert_not_found(self, client):
        """Test resolving non-existent alert."""
        resolve_data = {
            "resolution": "Fixed",
        }
        
        response = client.post(
            "/api/v1/alerts/99999/resolve",
            json=resolve_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 404

    def test_resolve_alert_missing_api_key(self, client, create_sample_alert):
        """Test resolving without API key."""
        alert = create_sample_alert
        resolve_data = {
            "resolution": "Fixed",
        }
        
        response = client.post(
            f"/api/v1/alerts/{alert.id}/resolve",
            json=resolve_data,
        )
        
        assert response.status_code == 401


class TestEscalateAlert:
    """Test alert escalation endpoint."""

    def test_escalate_alert_success(self, client, create_sample_alert):
        """Test successful alert escalation."""
        alert = create_sample_alert
        escalate_data = {
            "reason": "Issue requires immediate attention",
        }
        
        response = client.post(
            f"/api/v1/alerts/{alert.id}/escalate",
            json=escalate_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == alert.id
        assert data["priority"] == "critical"

    def test_escalate_alert_not_found(self, client):
        """Test escalating non-existent alert."""
        escalate_data = {
            "reason": "Urgent",
        }
        
        response = client.post(
            "/api/v1/alerts/99999/escalate",
            json=escalate_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 404

    def test_escalate_already_critical(self, client):
        """Test escalating already critical alert."""
        db = SessionLocal()
        try:
            alert = Alert(
                title="Critical Alert",
                source="test",
                priority=AlertPriority.CRITICAL,
                status=AlertStatus.OPEN,
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            escalate_data = {
                "reason": "Escalate",
            }
            
            response = client.post(
                f"/api/v1/alerts/{alert.id}/escalate",
                json=escalate_data,
                headers={"X-API-Key": "test-key"}
            )
            
            # Should still be critical
            assert response.status_code in [200, 400]
        finally:
            db.close()

    def test_escalate_alert_missing_api_key(self, client, create_sample_alert):
        """Test escalating without API key."""
        alert = create_sample_alert
        escalate_data = {
            "reason": "Urgent",
        }
        
        response = client.post(
            f"/api/v1/alerts/{alert.id}/escalate",
            json=escalate_data,
        )
        
        assert response.status_code == 401


class TestAlertIntegration:
    """Integration tests for alert operations."""

    def test_create_and_resolve_alert(self, client, sample_alert_data):
        """Test creating and resolving alert."""
        # Create
        create_response = client.post(
            "/api/v1/alerts",
            json=sample_alert_data,
            headers={"X-API-Key": "test-key"}
        )
        assert create_response.status_code == 201
        alert_id = create_response.json()["id"]
        
        # Resolve
        resolve_response = client.post(
            f"/api/v1/alerts/{alert_id}/resolve",
            json={"resolution": "Fixed"},
            headers={"X-API-Key": "test-key"}
        )
        assert resolve_response.status_code == 200
        assert resolve_response.json()["status"] == "resolved"

    def test_create_update_escalate_alert(self, client, sample_alert_data):
        """Test creating, updating, and escalating alert."""
        # Create
        create_response = client.post(
            "/api/v1/alerts",
            json=sample_alert_data,
            headers={"X-API-Key": "test-key"}
        )
        assert create_response.status_code == 201
        alert_id = create_response.json()["id"]
        
        # Update
        update_response = client.put(
            f"/api/v1/alerts/{alert_id}",
            json={"status": "acknowledged"},
            headers={"X-API-Key": "test-key"}
        )
        assert update_response.status_code == 200
        
        # Escalate
        escalate_response = client.post(
            f"/api/v1/alerts/{alert_id}/escalate",
            json={"reason": "Critical"},
            headers={"X-API-Key": "test-key"}
        )
        assert escalate_response.status_code == 200
        assert escalate_response.json()["priority"] == "critical"
