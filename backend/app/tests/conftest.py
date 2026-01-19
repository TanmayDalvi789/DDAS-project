"""
pytest Configuration and Fixtures for DDAS Backend Tests

Provides:
- FastAPI TestClient
- Test database (in-memory SQLite)
- Database session management
- Auth token fixtures
- Sample data fixtures
"""

import os
import pytest
from typing import Generator
from datetime import datetime, timedelta

# FastAPI and testing
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# App imports
from app.main import app
from app.db.database import Base, get_db
from app.middleware.auth import create_access_token, User


# ============================================================================
# DATABASE SETUP
# ============================================================================

@pytest.fixture(scope="function")
def db_engine():
    """Create test database engine (in-memory SQLite)."""
    # Use SQLite in-memory database for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine,
    )
    
    session = TestingSessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    """Create FastAPI TestClient with dependency override."""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Override the database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client
    test_client = TestClient(app)
    
    yield test_client
    
    # Clean up dependency overrides
    app.dependency_overrides.clear()


# ============================================================================
# AUTHENTICATION FIXTURES
# ============================================================================

@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.fixture
def registered_user(client: TestClient, test_user_data):
    """Register a test user and return user data."""
    # Register user
    response = client.post(
        "/api/v1/auth/register",
        json=test_user_data,
    )
    
    if response.status_code == 201:
        return {**test_user_data, "id": response.json().get("id")}
    elif response.status_code == 400:  # User already exists
        return test_user_data
    else:
        raise Exception(f"Failed to register user: {response.text}")


@pytest.fixture
def auth_token(client: TestClient, test_user_data):
    """Get JWT auth token for test user."""
    # Register user first
    client.post("/api/v1/auth/register", json=test_user_data)
    
    # Login to get token
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        },
    )
    
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    else:
        raise Exception(f"Failed to get auth token: {response.text}")


@pytest.fixture
def auth_headers(auth_token):
    """Get Authorization headers with JWT token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }


# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_fingerprint():
    """Sample fingerprint data for testing."""
    return {
        "fingerprint_hash": "abc123def456xyz789",
        "fingerprint_type": "browser",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "ip_address": "192.168.1.100",
        "device_id": "device_123",
        "browser": "Chrome",
        "os": "Windows",
        "tags": ["test", "demo"],
        "metadata": {
            "source": "test",
            "version": "1.0",
        }
    }


@pytest.fixture
def sample_event():
    """Sample event data for testing."""
    return {
        "event_type": "user_login",
        "user_id": "user_123",
        "timestamp": datetime.utcnow().isoformat(),
        "details": {
            "ip": "192.168.1.100",
            "user_agent": "Mozilla/5.0",
            "location": "New York",
        },
        "tags": ["login", "test"],
    }


@pytest.fixture
def sample_detection_request():
    """Sample fingerprint detection request."""
    return {
        "fingerprint_hash": "test_fingerprint_123",
        "fingerprint_type": "browser",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "ip_address": "192.168.1.100",
        "device_id": "device_123",
        "context": {
            "page": "/login",
            "referrer": "https://example.com",
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@pytest.fixture
def sample_feedback():
    """Sample feedback for decision override."""
    return {
        "fingerprint_hash": "test_fingerprint_123",
        "decision": "ALLOW",
        "confidence": 0.95,
        "reason": "User manually whitelisted",
        "feedback_type": "manual_review",
    }


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def api_prefix():
    """API prefix for all endpoints."""
    return "/api/v1"


@pytest.fixture(autouse=True)
def reset_db_state(db_session):
    """Reset database state before each test."""
    # Clear any existing data
    yield
    # Database is already clean due to function-scoped db_engine


# ============================================================================
# MARKERS FOR TEST CATEGORIZATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "health: Health check endpoint tests"
    )
    config.addinivalue_line(
        "markers", "auth: Authentication tests"
    )
    config.addinivalue_line(
        "markers", "fingerprint: Fingerprint ingestion tests"
    )
    config.addinivalue_line(
        "markers", "detection: Detection and decision engine tests"
    )
    config.addinivalue_line(
        "markers", "audit: Audit logging tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )


# ============================================================================
# DEBUG HELPER
# ============================================================================

def debug_response(response):
    """Helper to print response details for debugging."""
    print(f"\n=== Response Debug ===")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Body: {response.text}")
    print(f"=== End Debug ===\n")
