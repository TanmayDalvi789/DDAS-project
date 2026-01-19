"""
Tests for Detection API endpoints.

Coverage:
- POST /api/v1/detection/analyze (analyze samples)
- GET /api/v1/detection/job/{job_id}/status (check job status)
- GET /api/v1/detection/signals (list signals)
- POST /api/v1/detection/signals/{signal_id}/acknowledge (update signal)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app
from app.models.signal import Signal, SignalStatus
from app.models.detection import Detection
from app.db.database import SessionLocal


@pytest.fixture
def client():
    """Get test client."""
    return TestClient(app)


@pytest.fixture
def sample_analysis_data():
    """Sample detection analysis data."""
    return {
        "samples": [
            {"id": "sample1", "data": "raw_data_1"},
            {"id": "sample2", "data": "raw_data_2"},
        ],
        "priority": "high",
    }


@pytest.fixture
def create_sample_signal():
    """Create a sample signal in database."""
    db = SessionLocal()
    try:
        signal = Signal(
            name="Test Signal",
            source="test_detection",
            confidence=0.95,
            status=SignalStatus.PENDING,
            metadata={"type": "test"},
        )
        db.add(signal)
        db.commit()
        db.refresh(signal)
        yield signal
    finally:
        db.close()


class TestDetectionAnalyze:
    """Test detection analysis endpoint."""

    def test_analyze_success(self, client, sample_analysis_data):
        """Test successful detection analysis."""
        with patch('app.services.detection.DetectionService.analyze') as mock_analyze:
            mock_analyze.return_value = {
                "job_id": "job-123",
                "status": "queued",
                "samples_count": 2,
            }
            
            response = client.post(
                "/api/v1/detection/analyze",
                json=sample_analysis_data,
                headers={"X-API-Key": "test-key"}
            )
            
            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "queued"

    def test_analyze_missing_samples(self, client):
        """Test analysis with missing samples."""
        invalid_data = {
            "priority": "high",
        }
        
        response = client.post(
            "/api/v1/detection/analyze",
            json=invalid_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    def test_analyze_empty_samples(self, client):
        """Test analysis with empty samples."""
        invalid_data = {
            "samples": [],
            "priority": "high",
        }
        
        response = client.post(
            "/api/v1/detection/analyze",
            json=invalid_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    def test_analyze_invalid_priority(self, client, sample_analysis_data):
        """Test analysis with invalid priority."""
        sample_analysis_data["priority"] = "invalid_priority"
        
        response = client.post(
            "/api/v1/detection/analyze",
            json=sample_analysis_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    def test_analyze_missing_api_key(self, client, sample_analysis_data):
        """Test analysis without API key."""
        response = client.post(
            "/api/v1/detection/analyze",
            json=sample_analysis_data,
        )
        
        assert response.status_code == 401


class TestJobStatus:
    """Test job status endpoint."""

    def test_get_job_status_success(self, client):
        """Test getting job status."""
        with patch('app.workers.task_queue.TaskQueue.get_job_status') as mock_status:
            mock_status.return_value = {
                "job_id": "job-123",
                "status": "completed",
                "progress": 100,
                "result": {"detections": []},
            }
            
            response = client.get(
                "/api/v1/detection/job/job-123/status",
                headers={"X-API-Key": "test-key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "job-123"
            assert data["status"] == "completed"

    def test_get_job_status_not_found(self, client):
        """Test getting non-existent job status."""
        with patch('app.workers.task_queue.TaskQueue.get_job_status') as mock_status:
            mock_status.return_value = None
            
            response = client.get(
                "/api/v1/detection/job/invalid-job/status",
                headers={"X-API-Key": "test-key"}
            )
            
            assert response.status_code == 404

    def test_get_job_status_in_progress(self, client):
        """Test getting in-progress job status."""
        with patch('app.workers.task_queue.TaskQueue.get_job_status') as mock_status:
            mock_status.return_value = {
                "job_id": "job-123",
                "status": "started",
                "progress": 50,
            }
            
            response = client.get(
                "/api/v1/detection/job/job-123/status",
                headers={"X-API-Key": "test-key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["progress"] == 50

    def test_get_job_status_missing_api_key(self, client):
        """Test getting job status without API key."""
        response = client.get("/api/v1/detection/job/job-123/status")
        
        assert response.status_code == 401


class TestListSignals:
    """Test list signals endpoint."""

    def test_list_signals_empty(self, client):
        """Test listing signals when none exist."""
        response = client.get(
            "/api/v1/detection/signals",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_signals_with_status_filter(self, client, create_sample_signal):
        """Test listing signals with status filter."""
        response = client.get(
            "/api/v1/detection/signals?status=pending",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_signals_with_confidence_filter(self, client, create_sample_signal):
        """Test listing signals with confidence filter."""
        response = client.get(
            "/api/v1/detection/signals?min_confidence=0.8",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_signals_with_pagination(self, client):
        """Test listing signals with pagination."""
        response = client.get(
            "/api/v1/detection/signals?limit=10&offset=0",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_signals_invalid_confidence(self, client):
        """Test listing signals with invalid confidence."""
        response = client.get(
            "/api/v1/detection/signals?min_confidence=invalid",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    def test_list_signals_missing_api_key(self, client):
        """Test listing signals without API key."""
        response = client.get("/api/v1/detection/signals")
        
        assert response.status_code == 401


class TestAcknowledgeSignal:
    """Test acknowledge signal endpoint."""

    def test_acknowledge_signal_success(self, client, create_sample_signal):
        """Test successful signal acknowledgement."""
        signal = create_sample_signal
        update_data = {
            "status": "acknowledged",
            "comment": "Reviewed and confirmed",
        }
        
        response = client.post(
            f"/api/v1/detection/signals/{signal.id}/acknowledge",
            json=update_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == signal.id
        assert data["status"] == "acknowledged"

    def test_acknowledge_signal_not_found(self, client):
        """Test acknowledging non-existent signal."""
        update_data = {
            "status": "acknowledged",
        }
        
        response = client.post(
            "/api/v1/detection/signals/99999/acknowledge",
            json=update_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 404

    def test_acknowledge_signal_invalid_status(self, client, create_sample_signal):
        """Test acknowledging with invalid status."""
        signal = create_sample_signal
        update_data = {
            "status": "invalid_status",
        }
        
        response = client.post(
            f"/api/v1/detection/signals/{signal.id}/acknowledge",
            json=update_data,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    def test_acknowledge_signal_missing_api_key(self, client, create_sample_signal):
        """Test acknowledging without API key."""
        signal = create_sample_signal
        update_data = {
            "status": "acknowledged",
        }
        
        response = client.post(
            f"/api/v1/detection/signals/{signal.id}/acknowledge",
            json=update_data,
        )
        
        assert response.status_code == 401


class TestDetectionIntegration:
    """Integration tests for detection operations."""

    def test_analyze_and_check_job_status(self, client, sample_analysis_data):
        """Test analyzing and checking job status."""
        with patch('app.services.detection.DetectionService.analyze') as mock_analyze, \
             patch('app.workers.task_queue.TaskQueue.get_job_status') as mock_status:
            
            mock_analyze.return_value = {"job_id": "job-123", "status": "queued"}
            mock_status.return_value = {"job_id": "job-123", "status": "completed"}
            
            # Analyze
            analyze_response = client.post(
                "/api/v1/detection/analyze",
                json=sample_analysis_data,
                headers={"X-API-Key": "test-key"}
            )
            assert analyze_response.status_code == 202
            job_id = analyze_response.json()["job_id"]
            
            # Check status
            status_response = client.get(
                f"/api/v1/detection/job/{job_id}/status",
                headers={"X-API-Key": "test-key"}
            )
            assert status_response.status_code == 200

    def test_acknowledge_and_list_signals(self, client, create_sample_signal):
        """Test acknowledging and listing signals."""
        signal = create_sample_signal
        
        # Acknowledge
        ack_response = client.post(
            f"/api/v1/detection/signals/{signal.id}/acknowledge",
            json={"status": "acknowledged"},
            headers={"X-API-Key": "test-key"}
        )
        assert ack_response.status_code == 200
        
        # List
        list_response = client.get(
            "/api/v1/detection/signals",
            headers={"X-API-Key": "test-key"}
        )
        assert list_response.status_code == 200
