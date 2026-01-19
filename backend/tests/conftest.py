"""
Test Configuration and Fixtures
Shared test setup, database fixtures, and utilities for all test modules.
"""

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import Base
from app.db.models import (
    RawEvent, DetectionSignal, Alert, ProcessedSignal, WorkerStatus, AuditLog
)
from app.config import Settings


# Test database setup
@pytest.fixture(scope="session")
def test_db_engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create a new database session for each test."""
    connection = test_db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_settings():
    """Create test settings."""
    return Settings(
        database_url="sqlite:///:memory:",
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        api_host="0.0.0.0",
        api_port=8000,
        fuzzy_threshold=0.85,
        semantic_threshold=0.80,
        debug=True,
    )


@pytest.fixture
def test_event_data():
    """Test event data."""
    return {
        "source_id": "test-agent-001",
        "source_type": "agent",
        "event_type": "file_scanned",
        "timestamp": "2024-01-15T10:00:00Z",
        "payload": {
            "file_path": "/test/file.exe",
            "file_hash": "abc123def456",
            "file_size": 1024,
        },
    }


@pytest.fixture
def test_samples():
    """Test reference samples for detection."""
    return [
        "malware_hash_001",
        "malware_hash_002",
        "admin",
        "system",
    ]


@pytest.fixture
def test_event(test_db_session, test_event_data):
    """Create a test event in database."""
    event = RawEvent(
        event_id="evt_test_001",
        source_id=test_event_data["source_id"],
        source_type=test_event_data["source_type"],
        event_type=test_event_data["event_type"],
        payload=test_event_data["payload"],
    )
    test_db_session.add(event)
    test_db_session.commit()
    return event


@pytest.fixture
def test_signal(test_db_session, test_event):
    """Create a test signal in database."""
    signal = DetectionSignal(
        signal_id="sig_test_001",
        event_id=test_event.event_id,
        detection_type="fuzzy",
        confidence=0.92,
        result={"similarity": 0.92},
        status="completed",
    )
    test_db_session.add(signal)
    test_db_session.commit()
    return signal


@pytest.fixture
def test_alert(test_db_session, test_signal):
    """Create a test alert in database."""
    alert = Alert(
        alert_id="alr_test_001",
        signal_id=test_signal.signal_id,
        decision="BLOCK",
        reason="Malware detected",
        priority=9,
        status="active",
    )
    test_db_session.add(alert)
    test_db_session.commit()
    return alert


# Markers for test categorization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests (load testing)")
    config.addinivalue_line("markers", "db: Database tests")
    config.addinivalue_line("markers", "redis: Redis/Queue tests")


# Test utility functions
def assert_response_success(response, status_code=200):
    """Assert API response is successful."""
    assert response.status_code == status_code
    assert "error" not in response.json().get("message", "").lower()


def assert_valid_uuid(value):
    """Assert value is a valid UUID."""
    import uuid
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False
