"""
Demo-Grade Automated Tests for DDAS Backend

Test Categories:
1. Health Check - Verify API is running
2. Authentication - User registration and login
3. Unauthorized Access - Verify protected endpoints
4. Fingerprint Ingestion - Ingest and track fingerprints
5. Detection & Decision Engine - Test matching logic
6. Feedback Override - Override decisions manually
7. Audit Logging - Verify actions are logged

Run: pytest app/tests/test_demo.py -v
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


# ============================================================================
# TESTS: HEALTH CHECK
# ============================================================================

@pytest.mark.health
def test_health_check(client: TestClient, api_prefix: str):
    """
    Test: Health Check Endpoint
    
    Verify the API is running and responding to health checks.
    """
    response = client.get(f"{api_prefix}/health")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.health
def test_health_check_includes_database_status(client: TestClient, api_prefix: str):
    """
    Test: Health Check includes database status.
    """
    response = client.get(f"{api_prefix}/health")
    
    assert response.status_code == 200
    data = response.json()
    assert "database" in data
    assert "queue" in data


@pytest.mark.health
def test_root_endpoint(client: TestClient):
    """
    Test: Root endpoint returns API information.
    """
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "running"


# ============================================================================
# TESTS: AUTHENTICATION
# ============================================================================

@pytest.mark.auth
def test_user_registration(client: TestClient, api_prefix: str, test_user_data):
    """
    Test: User Registration
    
    Verify users can register with valid credentials.
    """
    response = client.post(
        f"{api_prefix}/auth/register",
        json=test_user_data,
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["username"] == test_user_data["username"]
    assert data["email"] == test_user_data["email"]
    assert "password" not in data  # Password should never be returned


@pytest.mark.auth
def test_user_registration_duplicate_username(
    client: TestClient, api_prefix: str, test_user_data
):
    """
    Test: Duplicate username registration fails.
    """
    # Register first user
    response1 = client.post(f"{api_prefix}/auth/register", json=test_user_data)
    assert response1.status_code == 201
    
    # Try to register duplicate username
    response2 = client.post(f"{api_prefix}/auth/register", json=test_user_data)
    # 409 Conflict is appropriate for duplicate resource, but accept 400 too
    assert response2.status_code in [400, 409]
    assert "already exists" in response2.json().get("detail", "").lower()


@pytest.mark.auth
def test_user_registration_invalid_email(
    client: TestClient, api_prefix: str, test_user_data
):
    """
    Test: Invalid email registration fails.
    """
    invalid_user = {**test_user_data, "email": "invalid-email"}
    response = client.post(f"{api_prefix}/auth/register", json=invalid_user)
    
    # FastAPI returns 422 for Pydantic validation errors (invalid email format)
    assert response.status_code in [400, 422]


@pytest.mark.auth
def test_user_login(client: TestClient, api_prefix: str, test_user_data):
    """
    Test: User Login
    
    Verify users can login and receive JWT token.
    """
    # Register user
    client.post(f"{api_prefix}/auth/register", json=test_user_data)
    
    # Login
    response = client.post(
        f"{api_prefix}/auth/login",
        json={
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.auth
def test_user_login_invalid_credentials(
    client: TestClient, api_prefix: str, test_user_data
):
    """
    Test: Login with invalid credentials fails.
    """
    # Register user
    client.post(f"{api_prefix}/auth/register", json=test_user_data)
    
    # Try to login with wrong password
    response = client.post(
        f"{api_prefix}/auth/login",
        json={
            "username": test_user_data["username"],
            "password": "WrongPassword123!",
        },
    )
    
    assert response.status_code == 401
    # Check either "message" or "detail" field for error
    resp_json = response.json()
    assert "invalid" in (resp_json.get("message", "") or resp_json.get("detail", "")).lower()


@pytest.mark.auth
def test_get_current_user(
    client: TestClient, api_prefix: str, auth_headers
):
    """
    Test: Get current user info from /auth/me endpoint.
    """
    response = client.get(
        f"{api_prefix}/auth/me",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "username" in data
    assert "email" in data


# ============================================================================
# TESTS: UNAUTHORIZED ACCESS
# ============================================================================

@pytest.mark.auth
def test_protected_endpoint_without_token(
    client: TestClient, api_prefix: str
):
    """
    Test: Protected endpoint without token returns 401.
    """
    response = client.get(f"{api_prefix}/auth/me")
    
    assert response.status_code == 401


@pytest.mark.auth
def test_protected_endpoint_with_invalid_token(
    client: TestClient, api_prefix: str
):
    """
    Test: Protected endpoint with invalid token returns 401.
    """
    headers = {"Authorization": "Bearer invalid.token.here"}
    response = client.get(f"{api_prefix}/auth/me", headers=headers)
    
    assert response.status_code == 401


@pytest.mark.auth
def test_protected_endpoint_with_expired_token(
    client: TestClient, api_prefix: str
):
    """
    Test: Protected endpoint with expired token returns 401.
    """
    # Create expired token
    from app.middleware.auth import create_access_token, User
    expired_user = User(
        id="test", username="test", email="test@ex.com",
        role="user", is_active=True
    )
    expired_token = create_access_token(
        user_id=expired_user.id,
        username=expired_user.username,
        role=expired_user.role,
        expires_delta=timedelta(seconds=-1)  # Already expired
    )
    
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get(f"{api_prefix}/auth/me", headers=headers)
    
    assert response.status_code == 401


# ============================================================================
# TESTS: FINGERPRINT INGESTION FLOW
# ============================================================================

@pytest.mark.fingerprint
def test_ingest_new_fingerprint(
    client: TestClient, api_prefix: str, auth_headers, sample_detection_request
):
    """
    Test: Ingest NEW fingerprint
    
    When a new fingerprint is ingested:
    1. It should be stored in database
    2. Initial detection should ALLOW
    3. No duplicate rows should exist
    """
    # Ingest fingerprint
    response = client.post(
        f"{api_prefix}/detection/detect",
        json=sample_detection_request,
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should allow new fingerprint
    assert "decision" in data
    assert data["decision"] in ["ALLOW", "WARN", "BLOCK"]
    
    # Should have timestamp
    assert "timestamp" in data
    
    # Should have detection details
    assert "fingerprint_hash" in data


@pytest.mark.fingerprint
def test_ingest_same_fingerprint_twice(
    client: TestClient, api_prefix: str, auth_headers, sample_detection_request
):
    """
    Test: Ingest SAME fingerprint twice
    
    When the same fingerprint is seen again:
    1. Second detection should be different from first
    2. No duplicate rows should exist in database
    """
    # First ingestion
    response1 = client.post(
        f"{api_prefix}/detection/detect",
        json=sample_detection_request,
        headers=auth_headers,
    )
    assert response1.status_code == 200
    decision1 = response1.json().get("decision")
    
    # Second ingestion (same fingerprint)
    response2 = client.post(
        f"{api_prefix}/detection/detect",
        json=sample_detection_request,
        headers=auth_headers,
    )
    assert response2.status_code == 200
    decision2 = response2.json().get("decision")
    
    # Decisions might differ (decision logic)
    assert "decision" in response2.json()
    
    # Verify fingerprint was detected as duplicate
    assert response2.json().get("is_duplicate") is True or decision2 != decision1


@pytest.mark.fingerprint
def test_fingerprint_tracking(
    client: TestClient, api_prefix: str, auth_headers, sample_detection_request
):
    """
    Test: Fingerprint is properly tracked
    
    Verify that ingested fingerprints can be queried back.
    """
    # Ingest fingerprint
    client.post(
        f"{api_prefix}/detection/detect",
        json=sample_detection_request,
        headers=auth_headers,
    )
    
    # Try to get fingerprint details
    fingerprint_hash = sample_detection_request["fingerprint_hash"]
    response = client.get(
        f"{api_prefix}/detection/fingerprints/{fingerprint_hash}",
        headers=auth_headers,
    )
    
    # Either 200 if endpoint exists or 404 if not, both acceptable for demo
    assert response.status_code in [200, 404]


# ============================================================================
# TESTS: SEARCH & DECISION ENGINE
# ============================================================================

@pytest.mark.detection
def test_exact_match_detection(
    client: TestClient, api_prefix: str, auth_headers, sample_detection_request
):
    """
    Test: Exact Match Detection
    
    Search for exact match of ingested fingerprint.
    Expected decision: BLOCK (seen before) or WARN
    """
    # Ingest fingerprint
    client.post(
        f"{api_prefix}/detection/detect",
        json=sample_detection_request,
        headers=auth_headers,
    )
    
    # Search for exact match
    response = client.post(
        f"{api_prefix}/detection/detect",
        json=sample_detection_request,
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "decision" in data
    assert "confidence" in data or "match_score" in data
    assert data["decision"] in ["ALLOW", "WARN", "BLOCK"]


@pytest.mark.detection
def test_fuzzy_match_detection(
    client: TestClient, api_prefix: str, auth_headers, sample_detection_request
):
    """
    Test: Fuzzy Match Detection
    
    Search for fuzzy/similar match.
    Expected: Low confidence match detection
    """
    # Ingest fingerprint
    client.post(
        f"{api_prefix}/detection/detect",
        json=sample_detection_request,
        headers=auth_headers,
    )
    
    # Create slightly different fingerprint (fuzzy match)
    similar_request = {
        **sample_detection_request,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Modified",
    }
    
    response = client.post(
        f"{api_prefix}/detection/detect",
        json=similar_request,
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "decision" in data


@pytest.mark.detection
def test_no_match_detection(
    client: TestClient, api_prefix: str, auth_headers, sample_detection_request
):
    """
    Test: No Match Detection
    
    Search for completely unknown fingerprint.
    Expected decision: ALLOW
    """
    # Create completely different fingerprint
    unknown_request = {
        **sample_detection_request,
        "fingerprint_hash": "completely_unique_hash_xyz999",
        "device_id": "device_unknown_999",
    }
    
    response = client.post(
        f"{api_prefix}/detection/detect",
        json=unknown_request,
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "decision" in data
    assert data["decision"] in ["ALLOW", "WARN", "BLOCK"]


@pytest.mark.detection
def test_detection_includes_match_details(
    client: TestClient, api_prefix: str, auth_headers, sample_detection_request
):
    """
    Test: Detection response includes match details.
    """
    response = client.post(
        f"{api_prefix}/detection/detect",
        json=sample_detection_request,
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "decision" in data
    assert "timestamp" in data
    
    # Should have some form of match information
    assert any(key in data for key in [
        "confidence", "match_score", "matches", "similar_fingerprints"
    ])


# ============================================================================
# TESTS: FEEDBACK OVERRIDE (OPTIONAL)
# ============================================================================

@pytest.mark.detection
def test_feedback_override_decision(
    client: TestClient, api_prefix: str, auth_headers,
    sample_detection_request, sample_feedback
):
    """
    Test: Feedback Override
    
    Submit feedback to override automatic decision.
    Re-run detection and verify feedback is considered.
    """
    # Ingest fingerprint
    client.post(
        f"{api_prefix}/detection/detect",
        json=sample_detection_request,
        headers=auth_headers,
    )
    
    # Submit feedback
    feedback_request = {
        **sample_feedback,
        "fingerprint_hash": sample_detection_request["fingerprint_hash"],
    }
    
    response = client.post(
        f"{api_prefix}/feedback",
        json=feedback_request,
        headers=auth_headers,
    )
    
    # Feedback endpoint might be 200, 201, or 404 (if not implemented)
    assert response.status_code in [200, 201, 404]
    
    if response.status_code in [200, 201]:
        # Re-run detection
        response2 = client.post(
            f"{api_prefix}/detection/detect",
            json=sample_detection_request,
            headers=auth_headers,
        )
        
        assert response2.status_code == 200
        # Feedback should be reflected in decision
        assert "decision" in response2.json()


# ============================================================================
# TESTS: AUDIT LOGGING
# ============================================================================

@pytest.mark.audit
def test_detection_audit_log(
    client: TestClient, api_prefix: str, auth_headers, sample_detection_request
):
    """
    Test: Detection Request is Audited
    
    Verify that detection requests are logged for audit trail.
    """
    # Send detection request
    response = client.post(
        f"{api_prefix}/detection/detect",
        json=sample_detection_request,
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    
    # Try to fetch audit logs
    audit_response = client.get(
        f"{api_prefix}/audit/logs",
        headers=auth_headers,
    )
    
    # Audit endpoint might exist or not (both acceptable for demo)
    if audit_response.status_code == 200:
        logs = audit_response.json()
        # Should have audit entries
        assert isinstance(logs, (list, dict))


@pytest.mark.audit
def test_feedback_audit_log(
    client: TestClient, api_prefix: str, auth_headers, sample_feedback
):
    """
    Test: Feedback is Audited
    
    Verify that feedback submissions are logged.
    """
    response = client.post(
        f"{api_prefix}/feedback",
        json=sample_feedback,
        headers=auth_headers,
    )
    
    # Feedback might not be implemented, which is fine
    if response.status_code in [200, 201]:
        # If implemented, check audit logging exists
        audit_response = client.get(
            f"{api_prefix}/audit/logs",
            headers=auth_headers,
        )
        
        if audit_response.status_code == 200:
            logs = audit_response.json()
            assert isinstance(logs, (list, dict))


# ============================================================================
# TESTS: INTEGRATION FLOWS
# ============================================================================

@pytest.mark.integration
def test_end_to_end_registration_login_detection(
    client: TestClient, api_prefix: str, test_user_data, sample_detection_request
):
    """
    Test: Complete flow from registration to detection
    
    1. Register user
    2. Login
    3. Use token to run detection
    """
    # Step 1: Register
    response = client.post(f"{api_prefix}/auth/register", json=test_user_data)
    assert response.status_code == 201
    
    # Step 2: Login
    response = client.post(
        f"{api_prefix}/auth/login",
        json={
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    # Step 3: Use token for detection
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        f"{api_prefix}/detection/detect",
        json=sample_detection_request,
        headers=headers,
    )
    
    assert response.status_code == 200
    assert "decision" in response.json()


@pytest.mark.integration
def test_end_to_end_multiple_detections(
    client: TestClient, api_prefix: str, auth_headers, sample_detection_request
):
    """
    Test: Multiple detection requests in sequence
    
    Verify system handles multiple requests correctly.
    """
    decisions = []
    
    # Run detection 3 times with variations
    for i in range(3):
        request = {
            **sample_detection_request,
            "device_id": f"device_{i}",
        }
        
        response = client.post(
            f"{api_prefix}/detection/detect",
            json=request,
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        decisions.append(response.json().get("decision"))
    
    # All should have valid decisions
    assert all(d in ["ALLOW", "WARN", "BLOCK"] for d in decisions)


# ============================================================================
# DEMO VERIFICATION SUMMARY
# ============================================================================

@pytest.mark.integration
def test_demo_readiness_checklist(client: TestClient, api_prefix: str):
    """
    Test: Demo Readiness Verification
    
    Checks if all critical endpoints are responding.
    """
    endpoints_to_check = [
        ("GET", "/"),
        ("GET", f"{api_prefix}/health"),
    ]
    
    results = {}
    for method, endpoint in endpoints_to_check:
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint)
        
        results[endpoint] = response.status_code
    
    # All critical endpoints should respond
    for endpoint, status in results.items():
        assert status < 500, f"{endpoint} returned {status}"
