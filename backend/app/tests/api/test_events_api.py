"""
Tests for Events API endpoints.

Coverage:
- POST /api/v1/events (create event)
- GET /api/v1/events (list events)
- GET /api/v1/events/{event_id} (get specific event)
- GET /api/v1/events/{event_id}/count (count by source)
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.models.event import Event, EventSeverity
from app.db.database import SessionLocal


@pytest.fixture
def client():
    """Get test client."""
    return TestClient(app)


@pytest.fixture
def sample_event_data():
    """Sample event creation data."""
    return {
        "name": "Test Event",
        "description": "Test event description",
        "source": "test_source",
        "severity": "medium",
        "payload": {"key": "value"},
    }


@pytest.fixture
def create_sample_event():
    """Create a sample event in database."""
    db = SessionLocal()
    try:
        event = Event(
            name="Sample Event",
            description="Sample event for testing",
            source="test_source",
            severity=EventSeverity.MEDIUM,
            payload={"test": "data"},
            processed=False,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        yield event
    finally:
        db.close()


class TestCreateEvent:
    """Test event creation endpoint."""

    def test_create_event_success(self, client, sample_event_data):
        """Test successful event creation."""
        response = client.post(
            "/api/v1/events",
            json=sample_event_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_event_data["name"]
        assert data["source"] == sample_event_data["source"]
        assert data["severity"] == sample_event_data["severity"]
        assert "id" in data
        assert "created_at" in data

    def test_create_event_missing_required_field(self, client):
        """Test event creation with missing required field."""
        invalid_data = {
            "description": "Missing name",
            "source": "test_source",
        }
        
        response = client.post(
            "/api/v1/events",
            json=invalid_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    def test_create_event_invalid_severity(self, client):
        """Test event creation with invalid severity."""
        invalid_data = {
            "name": "Test",
            "source": "test",
            "severity": "invalid_severity",
        }
        
        response = client.post(
            "/api/v1/events",
            json=invalid_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    def test_create_event_missing_api_key(self, client, sample_event_data):
        """Test event creation without API key."""
        response = client.post(
            "/api/v1/events",
            json=sample_event_data,
        )
        
        assert response.status_code == 401

    def test_create_event_invalid_api_key(self, client, sample_event_data):
        """Test event creation with invalid API key."""
        response = client.post(
            "/api/v1/events",
            json=sample_event_data,
            headers={"X-API-Key": "invalid-key"}
        )
        
        assert response.status_code == 401


class TestListEvents:
    """Test event listing endpoint."""

    def test_list_events_empty(self, client):
        """Test listing events when none exist."""
        response = client.get(
            "/api/v1/events",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_events_with_pagination(self, client):
        """Test listing events with pagination."""
        response = client.get(
            "/api/v1/events?limit=10&offset=0",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_events_with_filtering(self, client, create_sample_event):
        """Test listing events with source filter."""
        response = client.get(
            "/api/v1/events?source=test_source",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_events_with_severity_filter(self, client, create_sample_event):
        """Test listing events with severity filter."""
        response = client.get(
            "/api/v1/events?severity=medium",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_events_invalid_limit(self, client):
        """Test listing events with invalid limit."""
        response = client.get(
            "/api/v1/events?limit=invalid",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    def test_list_events_missing_api_key(self, client):
        """Test listing events without API key."""
        response = client.get("/api/v1/events")
        
        assert response.status_code == 401


class TestGetEvent:
    """Test get specific event endpoint."""

    def test_get_event_success(self, client, create_sample_event):
        """Test getting specific event."""
        event = create_sample_event
        response = client.get(
            f"/api/v1/events/{event.id}",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == event.id
        assert data["name"] == event.name
        assert data["source"] == event.source

    def test_get_event_not_found(self, client):
        """Test getting non-existent event."""
        response = client.get(
            "/api/v1/events/99999",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 404

    def test_get_event_invalid_id(self, client):
        """Test getting event with invalid ID."""
        response = client.get(
            "/api/v1/events/invalid-id",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    def test_get_event_missing_api_key(self, client, create_sample_event):
        """Test getting event without API key."""
        event = create_sample_event
        response = client.get(f"/api/v1/events/{event.id}")
        
        assert response.status_code == 401


class TestEventCount:
    """Test event count endpoint."""

    def test_count_events_by_source(self, client, create_sample_event):
        """Test counting events by source."""
        event = create_sample_event
        response = client.get(
            f"/api/v1/events/{event.id}/count",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)

    def test_count_events_not_found(self, client):
        """Test counting non-existent event."""
        response = client.get(
            "/api/v1/events/99999/count",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 404


class TestEventIntegration:
    """Integration tests for event operations."""

    def test_create_and_retrieve_event(self, client, sample_event_data):
        """Test creating and retrieving event."""
        # Create
        create_response = client.post(
            "/api/v1/events",
            json=sample_event_data,
            headers={"X-API-Key": "test-key"}
        )
        assert create_response.status_code == 201
        event_id = create_response.json()["id"]
        
        # Retrieve
        get_response = client.get(
            f"/api/v1/events/{event_id}",
            headers={"X-API-Key": "test-key"}
        )
        assert get_response.status_code == 200
        assert get_response.json()["id"] == event_id

    def test_list_includes_created_event(self, client, sample_event_data):
        """Test that created event appears in list."""
        # Create
        create_response = client.post(
            "/api/v1/events",
            json=sample_event_data,
            headers={"X-API-Key": "test-key"}
        )
        assert create_response.status_code == 201
        event_id = create_response.json()["id"]
        
        # List
        list_response = client.get(
            "/api/v1/events",
            headers={"X-API-Key": "test-key"}
        )
        assert list_response.status_code == 200
        events = list_response.json()
        assert any(e["id"] == event_id for e in events)
