"""
Phase 1: Database Layer Unit Tests
Tests for repositories, models, and database operations.
"""

import pytest
from datetime import datetime

from app.db.models import Event, Signal, Alert, ApiKey, WorkerStatus
from app.db.repositories.events_repo import EventsRepository
from app.db.repositories.signals_repo import SignalsRepository
from app.db.repositories.alerts_repo import AlertsRepository
from app.db.repositories.api_keys_repo import ApiKeysRepository
from app.db.repositories.worker_status_repo import WorkerStatusRepository


# ============================================================================
# EVENTS REPOSITORY TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.db
class TestEventsRepository:
    """Test EventsRepository CRUD operations."""
    
    @pytest.fixture
    def repo(self, test_db_session):
        return EventsRepository(test_db_session)
    
    def test_create_event(self, repo, test_event_data):
        """Test creating an event."""
        event = repo.create(
            source_id=test_event_data["source_id"],
            source_type=test_event_data["source_type"],
            event_type=test_event_data["event_type"],
            payload=test_event_data["payload"],
        )
        
        assert event is not None
        assert event.id is not None
        assert event.source_id == test_event_data["source_id"]
        assert event.event_type == test_event_data["event_type"]
    
    def test_get_event_by_id(self, repo, test_event):
        """Test retrieving event by ID."""
        retrieved = repo.get_by_id(test_event.id)
        
        assert retrieved is not None
        assert retrieved.id == test_event.id
        assert retrieved.source_id == test_event.source_id
    
    def test_get_nonexistent_event(self, repo):
        """Test getting nonexistent event returns None."""
        result = repo.get_by_id("nonexistent-id")
        assert result is None
    
    def test_list_events_by_source(self, repo, test_db_session):
        """Test listing events by source."""
        # Create multiple events
        repo.create("source-1", "agent", "scan", {})
        repo.create("source-1", "agent", "scan", {})
        repo.create("source-2", "proxy", "traffic", {})
        
        # List by source
        events = repo.list_by_source("source-1")
        assert len(events) == 2
        assert all(e.source_id == "source-1" for e in events)
    
    def test_list_recent_events(self, repo):
        """Test listing recent events."""
        for i in range(5):
            repo.create(f"source-{i}", "agent", "scan", {})
        
        recent = repo.list_recent(limit=3)
        assert len(recent) == 3
        
        # Should be in reverse chronological order
        assert recent[0].created_at >= recent[1].created_at
    
    def test_count_events_by_source(self, repo):
        """Test counting events by source."""
        repo.create("source-1", "agent", "scan", {})
        repo.create("source-1", "agent", "scan", {})
        repo.create("source-2", "proxy", "traffic", {})
        
        count1 = repo.count_by_source("source-1")
        count2 = repo.count_by_source("source-2")
        
        assert count1 == 2
        assert count2 == 1


# ============================================================================
# SIGNALS REPOSITORY TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.db
class TestSignalsRepository:
    """Test SignalsRepository CRUD operations."""
    
    @pytest.fixture
    def repo(self, test_db_session):
        return SignalsRepository(test_db_session)
    
    def test_create_signal(self, repo, test_event):
        """Test creating a signal."""
        signal = repo.create(
            event_id=test_event.id,
            detection_type="fuzzy",
            confidence=0.92,
            detected_items=["match"],
            raw_result={"score": 0.92},
        )
        
        assert signal is not None
        assert signal.id is not None
        assert signal.event_id == test_event.id
        assert signal.detection_type == "fuzzy"
        assert signal.confidence == 0.92
    
    def test_get_signal_by_id(self, repo, test_signal):
        """Test retrieving signal by ID."""
        retrieved = repo.get_by_id(test_signal.id)
        
        assert retrieved is not None
        assert retrieved.id == test_signal.id
        assert retrieved.detection_type == test_signal.detection_type
    
    def test_list_signals_by_event(self, repo, test_event):
        """Test listing signals by event."""
        repo.create(test_event.id, "fuzzy", 0.85, ["m1"], {})
        repo.create(test_event.id, "semantic", 0.90, ["m2"], {})
        repo.create(test_event.id, "exact", 1.0, ["m3"], {})
        
        signals = repo.list_by_event(test_event.id)
        assert len(signals) == 3
        assert all(s.event_id == test_event.id for s in signals)
    
    def test_update_signal_status(self, repo, test_signal):
        """Test updating signal status."""
        repo.update_status(test_signal.id, "alerted")
        updated = repo.get_by_id(test_signal.id)
        
        assert updated.status == "alerted"
    
    def test_list_pending_signals(self, repo, test_event):
        """Test listing pending signals."""
        repo.create(test_event.id, "fuzzy", 0.85, ["m1"], {})
        repo.create(test_event.id, "semantic", 0.90, ["m2"], {}, status="alerted")
        repo.create(test_event.id, "exact", 1.0, ["m3"], {})
        
        pending = repo.list_pending()
        assert len(pending) == 2
        assert all(s.status == "pending_alert" for s in pending)
    
    def test_count_signals_by_status(self, repo, test_event):
        """Test counting signals by status."""
        repo.create(test_event.id, "fuzzy", 0.85, ["m1"], {})
        repo.create(test_event.id, "semantic", 0.90, ["m2"], {}, status="alerted")
        repo.create(test_event.id, "exact", 1.0, ["m3"], {}, status="alerted")
        
        pending = repo.count_by_status("pending_alert")
        alerted = repo.count_by_status("alerted")
        
        assert pending == 1
        assert alerted == 2


# ============================================================================
# ALERTS REPOSITORY TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.db
class TestAlertsRepository:
    """Test AlertsRepository CRUD operations."""
    
    @pytest.fixture
    def repo(self, test_db_session):
        return AlertsRepository(test_db_session)
    
    def test_create_alert(self, repo, test_signal):
        """Test creating an alert."""
        alert = repo.create(
            signal_id=test_signal.id,
            decision="BLOCK",
            reason="Match found",
            confidence=0.95,
            priority=9,
        )
        
        assert alert is not None
        assert alert.id is not None
        assert alert.signal_id == test_signal.id
        assert alert.decision == "BLOCK"
        assert alert.priority == 9
    
    def test_get_alert_by_id(self, repo, test_alert):
        """Test retrieving alert by ID."""
        retrieved = repo.get_by_id(test_alert.id)
        
        assert retrieved is not None
        assert retrieved.id == test_alert.id
        assert retrieved.decision == test_alert.decision
    
    def test_get_alert_by_signal(self, repo, test_signal):
        """Test getting alert by signal ID."""
        alert = repo.create(test_signal.id, "BLOCK", "Match", 0.95, 9)
        retrieved = repo.get_by_signal(test_signal.id)
        
        assert retrieved is not None
        assert retrieved.signal_id == test_signal.id
    
    def test_list_active_alerts(self, repo, test_signal):
        """Test listing active alerts."""
        repo.create(test_signal.id, "BLOCK", "M1", 0.95, 9)
        
        # Create another signal for inactive alert
        from app.db.repositories.events_repo import EventsRepository
        event_repo = EventsRepository(repo.db)
        event = event_repo.create("src", "type", "evt", {})
        
        from app.db.repositories.signals_repo import SignalsRepository
        sig_repo = SignalsRepository(repo.db)
        sig = sig_repo.create(event.id, "fuzzy", 0.8, ["m"], {})
        
        inactive_alert = repo.create(sig.id, "WARN", "M2", 0.85, 5)
        repo.update_status(inactive_alert.id, "resolved")
        
        active = repo.list_active()
        assert len(active) == 1
        assert active[0].status == "active"
    
    def test_update_alert_status(self, repo, test_alert):
        """Test updating alert status."""
        repo.update_status(test_alert.id, "resolved")
        updated = repo.get_by_id(test_alert.id)
        
        assert updated.status == "resolved"
    
    def test_count_alerts_by_decision(self, repo, test_signal):
        """Test counting alerts by decision."""
        repo.create(test_signal.id, "BLOCK", "M1", 0.95, 9)
        repo.create(test_signal.id, "WARN", "M2", 0.85, 5)
        
        blocks = repo.count_by_decision("BLOCK")
        warns = repo.count_by_decision("WARN")
        
        assert blocks == 1
        assert warns == 1


# ============================================================================
# API KEYS REPOSITORY TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.db
class TestApiKeysRepository:
    """Test ApiKeysRepository operations."""
    
    @pytest.fixture
    def repo(self, test_db_session):
        return ApiKeysRepository(test_db_session)
    
    def test_create_api_key(self, repo):
        """Test creating an API key."""
        key = repo.create(
            key_hash="hash123",
            name="test-key",
            description="Test API key",
            agent_id="agent-001",
        )
        
        assert key is not None
        assert key.id is not None
        assert key.name == "test-key"
        assert key.active is True
    
    def test_get_api_key_by_hash(self, repo):
        """Test retrieving API key by hash."""
        created = repo.create("hash123", "test-key", "Test", "agent-001")
        retrieved = repo.get_by_hash("hash123")
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "test-key"
    
    def test_update_last_used(self, repo):
        """Test updating last used timestamp."""
        key = repo.create("hash123", "test-key", "Test", "agent-001")
        repo.update_last_used(key.id)
        
        updated = repo.get_by_id(key.id)
        assert updated.last_used_at is not None
    
    def test_deactivate_key(self, repo):
        """Test deactivating API key."""
        key = repo.create("hash123", "test-key", "Test", "agent-001")
        repo.deactivate(key.id)
        
        deactivated = repo.get_by_id(key.id)
        assert deactivated.active is False
    
    def test_activate_key(self, repo):
        """Test activating API key."""
        key = repo.create("hash123", "test-key", "Test", "agent-001")
        repo.deactivate(key.id)
        repo.activate(key.id)
        
        activated = repo.get_by_id(key.id)
        assert activated.active is True


# ============================================================================
# WORKER STATUS REPOSITORY TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.db
class TestWorkerStatusRepository:
    """Test WorkerStatusRepository operations."""
    
    @pytest.fixture
    def repo(self, test_db_session):
        return WorkerStatusRepository(test_db_session)
    
    def test_upsert_worker_status(self, repo):
        """Test upserting worker status."""
        status = repo.upsert(
            worker_id="worker-001",
            status="running",
            jobs_processed=0,
            jobs_failed=0,
        )
        
        assert status is not None
        assert status.worker_id == "worker-001"
        assert status.status == "running"
    
    def test_increment_tasks(self, repo):
        """Test incrementing task count."""
        status = repo.upsert("worker-001", "running", 0, 0)
        repo.increment_tasks(status.id, 5)
        
        updated = repo.get_by_id(status.id)
        assert updated.jobs_processed == 5
    
    def test_increment_errors(self, repo):
        """Test incrementing error count."""
        status = repo.upsert("worker-001", "running", 0, 0)
        repo.increment_errors(status.id, 2)
        
        updated = repo.get_by_id(status.id)
        assert updated.jobs_failed == 2
    
    def test_update_status(self, repo):
        """Test updating worker status."""
        status = repo.upsert("worker-001", "running", 0, 0)
        repo.update_status(status.id, "stopped")
        
        updated = repo.get_by_id(status.id)
        assert updated.status == "stopped"
    
    def test_list_all_workers(self, repo):
        """Test listing all worker statuses."""
        repo.upsert("worker-001", "running", 0, 0)
        repo.upsert("worker-002", "running", 0, 0)
        repo.upsert("worker-003", "stopped", 0, 0)
        
        all_workers = repo.list_all()
        assert len(all_workers) == 3


# ============================================================================
# DATABASE MODEL TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.db
class TestDatabaseModels:
    """Test SQLAlchemy ORM models."""
    
    def test_event_model(self, test_db_session):
        """Test Event model."""
        event = Event(
            source_id="src-001",
            source_type="agent",
            event_type="scan",
            payload={"key": "value"},
        )
        test_db_session.add(event)
        test_db_session.commit()
        
        assert event.id is not None
        assert event.created_at is not None
        assert event.payload == {"key": "value"}
    
    def test_signal_model(self, test_db_session, test_event):
        """Test Signal model."""
        signal = Signal(
            event_id=test_event.id,
            detection_type="fuzzy",
            confidence=0.85,
            detected_items=["item1", "item2"],
            raw_result={"score": 0.85},
            status="pending_alert",
        )
        test_db_session.add(signal)
        test_db_session.commit()
        
        assert signal.id is not None
        assert signal.event_id == test_event.id
        assert len(signal.detected_items) == 2
    
    def test_alert_model(self, test_db_session, test_signal):
        """Test Alert model."""
        alert = Alert(
            signal_id=test_signal.id,
            decision="BLOCK",
            reason="Threat detected",
            confidence=0.95,
            priority=9,
            status="active",
        )
        test_db_session.add(alert)
        test_db_session.commit()
        
        assert alert.id is not None
        assert alert.signal_id == test_signal.id
        assert alert.decision == "BLOCK"
        assert alert.priority == 9
