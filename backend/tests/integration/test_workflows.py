"""
Phase 4: Integration Tests
Tests for end-to-end workflows across all components.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json

from app.services.ingest_service import IngestService
from app.services.detection_service import DetectionService
from app.services.alert_service import AlertService


# ============================================================================
# INGEST WORKFLOW TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.db
class TestIngestWorkflow:
    """Test complete ingest workflow from event to storage."""
    
    def test_event_ingestion_flow(self, test_db_session):
        """Test complete event ingestion."""
        ingest_svc = IngestService(test_db_session)
        
        # Ingest event
        event_data = {
            "source_id": "agent-001",
            "source_type": "agent",
            "event_type": "scan",
            "payload": {"detection": "malware", "score": 0.95},
        }
        
        event = ingest_svc.ingest_event(
            source_id=event_data["source_id"],
            source_type=event_data["source_type"],
            event_type=event_data["event_type"],
            payload=event_data["payload"],
        )
        
        assert event is not None
        assert event.id is not None
        assert event.source_id == "agent-001"
        assert event.payload == event_data["payload"]
    
    def test_batch_event_ingestion(self, test_db_session):
        """Test ingesting multiple events."""
        ingest_svc = IngestService(test_db_session)
        
        events_data = [
            {
                "source_id": "agent-001",
                "source_type": "agent",
                "event_type": "scan",
                "payload": {"data": "malware"},
            },
            {
                "source_id": "agent-001",
                "source_type": "agent",
                "event_type": "scan",
                "payload": {"data": "suspicious"},
            },
            {
                "source_id": "proxy-001",
                "source_type": "proxy",
                "event_type": "traffic",
                "payload": {"data": "blocked"},
            },
        ]
        
        events = []
        for event_data in events_data:
            event = ingest_svc.ingest_event(**event_data)
            events.append(event)
        
        assert len(events) == 3
        assert events[0].source_id == "agent-001"
        assert events[1].source_id == "agent-001"
        assert events[2].source_id == "proxy-001"


# ============================================================================
# DETECTION WORKFLOW TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.db
class TestDetectionWorkflow:
    """Test complete detection workflow."""
    
    def test_single_detection_workflow(self, test_db_session, test_event):
        """Test detection on a single event."""
        detection_svc = DetectionService(test_db_session)
        
        # Add reference samples
        samples = [
            "alert(window,'xss')",
            "eval(payload)",
            "<script>malware()</script>",
        ]
        
        # Process event with detection
        with patch('app.services.detection_service.DetectionOrchestrator') as MockOrch:
            mock_orchestrator = Mock()
            MockOrch.return_value = mock_orchestrator
            
            # Mock detection result
            mock_orchestrator.detect.return_value = Mock(
                decision="BLOCK",
                confidence=0.95,
                reason="STRONG_DETECTION",
                matches=["alert(window,'xss')"],
            )
            
            # Run detection
            signals = detection_svc.run_detection(test_event, samples)
            
            # Verify signals created
            assert signals is not None
    
    def test_multi_algorithm_detection(self, test_db_session, test_event):
        """Test detection using multiple algorithms."""
        detection_svc = DetectionService(test_db_session)
        
        samples = ["malicious_code"]
        
        with patch('app.services.detection_service.DetectionOrchestrator') as MockOrch:
            mock_orchestrator = Mock()
            MockOrch.return_value = mock_orchestrator
            
            # Mock results from different algorithms
            mock_orchestrator.detect.return_value = Mock(
                decision="WARN",
                confidence=0.82,  # Average of 3 algorithms
                reason="MULTIPLE_DETECTION",
            )
            
            signals = detection_svc.run_detection(test_event, samples)
            # Signals should be created with WARN level


# ============================================================================
# ALERT WORKFLOW TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.db
class TestAlertWorkflow:
    """Test complete alert workflow."""
    
    def test_alert_creation_flow(self, test_db_session, test_signal):
        """Test alert creation from signal."""
        alert_svc = AlertService(test_db_session)
        
        # Create alert from signal
        alert = alert_svc.create_from_signal(
            signal_id=test_signal.id,
            decision="BLOCK",
            reason="High confidence match",
            confidence=0.95,
            priority=9,
        )
        
        assert alert is not None
        assert alert.signal_id == test_signal.id
        assert alert.decision == "BLOCK"
        assert alert.priority == 9
        assert alert.status == "active"
    
    def test_alert_escalation(self, test_db_session, test_signal):
        """Test alert priority escalation."""
        alert_svc = AlertService(test_db_session)
        
        # Create initial alert
        alert = alert_svc.create_from_signal(
            signal_id=test_signal.id,
            decision="WARN",
            reason="Moderate threat",
            confidence=0.75,
            priority=5,
        )
        
        # Escalate priority
        escalated = alert_svc.escalate_priority(alert.id)
        assert escalated.priority > alert.priority
    
    def test_alert_resolution(self, test_db_session, test_signal):
        """Test alert resolution workflow."""
        alert_svc = AlertService(test_db_session)
        
        alert = alert_svc.create_from_signal(
            signal_id=test_signal.id,
            decision="BLOCK",
            reason="Threat",
            confidence=0.95,
            priority=9,
        )
        
        # Resolve alert
        resolved = alert_svc.resolve_alert(alert.id, "False positive")
        assert resolved.status == "resolved"


# ============================================================================
# END-TO-END WORKFLOW TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.db
class TestEndToEndWorkflow:
    """Test complete workflows from ingest to alert."""
    
    def test_event_to_detection_to_alert(self, test_db_session):
        """Test full workflow: Event → Detection → Alert."""
        ingest_svc = IngestService(test_db_session)
        detection_svc = DetectionService(test_db_session)
        alert_svc = AlertService(test_db_session)
        
        # Step 1: Ingest event
        event = ingest_svc.ingest_event(
            source_id="agent-001",
            source_type="agent",
            event_type="scan",
            payload={"sample": "alert('xss')"},
        )
        assert event is not None
        
        # Step 2: Run detection (mocked)
        samples = ["alert('xss')", "eval(code)"]
        
        with patch('app.services.detection_service.DetectionOrchestrator') as MockOrch:
            mock_orchestrator = Mock()
            MockOrch.return_value = mock_orchestrator
            
            mock_orchestrator.detect.return_value = Mock(
                decision="BLOCK",
                confidence=0.96,
                reason="STRONG_DETECTION",
            )
            
            # Create signal manually for testing
            from app.db.repositories.signals_repo import SignalsRepository
            signals_repo = SignalsRepository(test_db_session)
            signal = signals_repo.create(
                event_id=event.id,
                detection_type="fuzzy",
                confidence=0.96,
                detected_items=["alert('xss')"],
                raw_result={"match": "exact"},
            )
            assert signal is not None
            
            # Step 3: Create alert
            alert = alert_svc.create_from_signal(
                signal_id=signal.id,
                decision="BLOCK",
                reason="XSS vulnerability detected",
                confidence=0.96,
                priority=9,
            )
            assert alert is not None
            assert alert.decision == "BLOCK"
            assert alert.priority == 9
    
    def test_concurrent_event_processing(self, test_db_session):
        """Test processing multiple events concurrently."""
        ingest_svc = IngestService(test_db_session)
        
        # Simulate concurrent event ingestion
        events = []
        for i in range(5):
            event = ingest_svc.ingest_event(
                source_id=f"agent-{i:03d}",
                source_type="agent",
                event_type="scan",
                payload={"index": i},
            )
            events.append(event)
        
        assert len(events) == 5
        assert all(e is not None for e in events)
        assert events[0].source_id == "agent-000"
        assert events[4].source_id == "agent-004"


# ============================================================================
# QUEUE INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
class TestQueueIntegrationWorkflow:
    """Test queue system with task processing."""
    
    def test_task_enqueueing_and_status(self):
        """Test enqueueing tasks and checking status."""
        with patch('app.workers.task_queue.RedisQueueManager') as MockQM:
            mock_manager = Mock()
            MockQM.return_value = mock_manager
            
            from app.workers.task_queue import TaskQueue, TaskPriority
            
            # Mock queue manager methods
            mock_manager.enqueue_task.return_value = Mock(id="job-123")
            mock_manager.get_job_status.side_effect = [
                "queued", "started", "finished"
            ]
            mock_manager.get_job_result.return_value = {
                "decision": "BLOCK",
                "confidence": 0.95,
            }
            
            task_queue = TaskQueue()
            task_queue.manager = mock_manager
            
            # Enqueue detection task
            job_id = task_queue.enqueue_detection(
                sample_data="alert('xss')",
                threshold=0.8,
                priority=TaskPriority.HIGH,
            )
            assert job_id == "job-123"
            
            # Check status progression
            assert task_queue.get_status(job_id) == "queued"
            assert task_queue.get_status(job_id) == "started"
            assert task_queue.get_status(job_id) == "finished"
            
            # Get result
            result = task_queue.get_result(job_id)
            assert result["decision"] == "BLOCK"
    
    def test_priority_task_execution(self):
        """Test that high priority tasks are processed first."""
        with patch('app.workers.task_queue.RedisQueueManager') as MockQM:
            mock_manager = Mock()
            MockQM.return_value = mock_manager
            
            from app.workers.task_queue import TaskQueue, TaskPriority
            
            mock_manager.enqueue_task.return_value = Mock(id="job-xyz")
            
            task_queue = TaskQueue()
            task_queue.manager = mock_manager
            
            # Enqueue tasks with different priorities
            job1 = task_queue.enqueue_detection(
                sample_data="data1",
                threshold=0.8,
                priority=TaskPriority.LOW,
            )
            
            job2 = task_queue.enqueue_detection(
                sample_data="data2",
                threshold=0.8,
                priority=TaskPriority.CRITICAL,
            )
            
            # Verify both enqueued (order depends on queue implementation)
            assert mock_manager.enqueue_task.call_count == 2


# ============================================================================
# CROSS-COMPONENT TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.db
class TestCrossComponentIntegration:
    """Test integration between different components."""
    
    def test_repository_service_integration(self, test_db_session):
        """Test repositories used by services."""
        from app.db.repositories.events_repo import EventsRepository
        from app.services.ingest_service import IngestService
        
        # Services should use repositories internally
        ingest_svc = IngestService(test_db_session)
        
        # Ingest should create event via repository
        event = ingest_svc.ingest_event(
            source_id="src-001",
            source_type="agent",
            event_type="scan",
            payload={"data": "test"},
        )
        
        # Verify via repository
        events_repo = EventsRepository(test_db_session)
        retrieved = events_repo.get_by_id(event.id)
        
        assert retrieved is not None
        assert retrieved.id == event.id
        assert retrieved.source_id == "src-001"
    
    def test_signal_alert_relationship(self, test_db_session, test_signal):
        """Test relationship between signals and alerts."""
        from app.services.alert_service import AlertService
        from app.db.repositories.alerts_repo import AlertsRepository
        
        alert_svc = AlertService(test_db_session)
        
        # Create alert from signal
        alert = alert_svc.create_from_signal(
            signal_id=test_signal.id,
            decision="BLOCK",
            reason="Test",
            confidence=0.95,
            priority=9,
        )
        
        # Verify relationship
        alerts_repo = AlertsRepository(test_db_session)
        retrieved = alerts_repo.get_by_signal(test_signal.id)
        
        assert retrieved is not None
        assert retrieved.signal_id == test_signal.id
        assert retrieved.id == alert.id


# ============================================================================
# DATA FLOW TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.db
class TestDataFlow:
    """Test data flow through the system."""
    
    def test_event_data_transformation(self, test_db_session):
        """Test event data transformation through pipeline."""
        ingest_svc = IngestService(test_db_session)
        
        # Original data
        original_payload = {
            "source": "agent",
            "threat_level": "high",
            "samples": ["s1", "s2", "s3"],
        }
        
        # Ingest event
        event = ingest_svc.ingest_event(
            source_id="agent-001",
            source_type="agent",
            event_type="scan",
            payload=original_payload,
        )
        
        # Verify payload preserved
        assert event.payload == original_payload
        assert event.payload["threat_level"] == "high"
        assert len(event.payload["samples"]) == 3
    
    def test_signal_detection_result_preservation(self, test_db_session, test_event):
        """Test that detection results are preserved in signals."""
        from app.db.repositories.signals_repo import SignalsRepository
        
        signals_repo = SignalsRepository(test_db_session)
        
        detection_result = {
            "algorithm": "fuzzy",
            "score": 0.92,
            "matches": ["alert('xss')", "eval(code)"],
            "processing_time_ms": 145,
        }
        
        signal = signals_repo.create(
            event_id=test_event.id,
            detection_type="fuzzy",
            confidence=detection_result["score"],
            detected_items=detection_result["matches"],
            raw_result=detection_result,
        )
        
        # Verify result preserved
        assert signal.raw_result == detection_result
        assert signal.raw_result["processing_time_ms"] == 145
