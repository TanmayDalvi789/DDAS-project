"""Backend lookup client - STEP-5 Global similarity search.

Sends extracted features to backend and retrieves similarity scores.
No exceptions propagate; all failures logged as warnings.

Defensive Measures:
- Validates request payload structure
- Validates response schema strictly
- Logs validation failures (never crashes)
- Graceful degradation on malformed responses
"""

import json
import logging
from typing import Optional, Dict, Any

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    import urllib.request
    import urllib.error

logger = logging.getLogger(__name__)


def _validate_lookup_response(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate backend lookup response schema (STEP-5 contract).
    
    Expected schema:
    {
        "exact_match": {
            "is_match": bool,
            "similarity_type": "exact",
            "score": float,
            "reference_id": str or None,
            "reference_metadata": dict or None,
        },
        "fuzzy_match": {...},
        "semantic_match": {...},
    }
    
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, f"Response must be dict, got {type(data)}"
    
    # Check required keys
    required_keys = {"exact_match", "fuzzy_match", "semantic_match"}
    missing = required_keys - set(data.keys())
    if missing:
        return False, f"Missing required keys: {missing}"
    
    # Check structure of each match type
    for match_type in required_keys:
        match_data = data[match_type]
        
        if not isinstance(match_data, dict):
            return False, f"{match_type} must be dict, got {type(match_data)}"
        
        # Check required fields in match data
        required_fields = {"is_match", "similarity_type", "score", "reference_id", "reference_metadata"}
        missing_fields = required_fields - set(match_data.keys())
        if missing_fields:
            return False, f"{match_type} missing fields: {missing_fields}"
        
        # Type validation
        if not isinstance(match_data["is_match"], bool):
            return False, f"{match_type}.is_match must be bool"
        
        if not isinstance(match_data["similarity_type"], str):
            return False, f"{match_type}.similarity_type must be str"
        
        score = match_data["score"]
        if not isinstance(score, (int, float)):
            return False, f"{match_type}.score must be numeric"
        
        if not (0.0 <= score <= 1.0):
            return False, f"{match_type}.score must be 0.0-1.0, got {score}"
    
    return True, None


def perform_lookup(
    features: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    backend_base_url: str = "http://localhost:8001",
    auth_headers: Optional[Dict[str, str]] = None,
    timeout_seconds: int = 5,
) -> Dict[str, Any]:
    """
    Perform global similarity lookup on backend.
    
    STEP-5: Query backend for matches using extracted features.
    Agent sends FEATURES only, not raw file content.
    Backend returns SCORES + EVIDENCE, not decisions.
    
    Args:
        features: Dict from extract_all_features() with keys:
            - exact: {algorithm, value, bytes_read} or None
            - fuzzy: {algorithm, value, num_perm} or None
            - semantic: {model_name, vector, dimension} or None
        metadata: Optional file metadata {filename, size, mime_type, ...}
        backend_base_url: Backend API base URL
        auth_headers: Optional authentication headers
        timeout_seconds: Request timeout (default 5s)
    
    Returns:
        Dict with structure:
        {
            "matches": [
                {
                    "match_id": str,
                    "similarity_type": "exact" | "fuzzy" | "semantic",
                    "score": float (0.0-1.0),
                    "reference_metadata": {...},
                },
                ...
            ],
            "backend_timestamp": int,
            "lookup_status": "success" | "timeout" | "error"
        }
    
    NOTE:
    - If backend is unreachable: Return empty matches, log warning
    - No exceptions must propagate upward
    - No retry or backoff logic in Step-5
    - No decision logic (Phase-5 responsibility)
    """
    # Default response (used on any failure)
    default_response = {
        "matches": [],
        "backend_timestamp": None,
        "lookup_status": "error",
    }
    
    # Build request payload from available features only
    try:
        payload = {
            "agent_id": metadata.get("agent_id", "unknown") if metadata else "unknown",
            "event_id": metadata.get("event_id", "") if metadata else "",
            "metadata": metadata or {},
        }
        
        # Add only non-None feature types
        if features and features.get("exact"):
            payload["exact_hash"] = features["exact"].get("value")
        
        if features and features.get("fuzzy"):
            # MinHash signature: list of integers
            payload["fuzzy_sig"] = features["fuzzy"].get("value")
        
        if features and features.get("semantic"):
            # SBERT embedding: list of floats
            payload["semantic_vec"] = features["semantic"].get("vector")
        
        # Construct URL
        url = f"{backend_base_url.rstrip('/')}/api/v1/lookup"
        
        # Send request (defensive parsing)
        if HTTPX_AVAILABLE:
            result = _lookup_with_httpx(url, payload, auth_headers, timeout_seconds)
        else:
            result = _lookup_with_urllib(url, payload, auth_headers, timeout_seconds)
        
        return result if result is not None else default_response
    
    except Exception as e:
        logger.warning(f"Lookup exception (unexpected): {e}")
        return default_response


def _lookup_with_httpx(
    url: str,
    payload: Dict[str, Any],
    auth_headers: Optional[Dict[str, str]],
    timeout_seconds: int,
) -> Optional[Dict[str, Any]]:
    """
    Send lookup request using httpx (if available).
    Returns None on any failure (logged as warning).
    Validates response schema strictly.
    """
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                url,
                json=payload,
                headers=auth_headers or {},
            )
            
            if response.status_code != 200:
                logger.warning(
                    f"[LOOKUP] Backend returned HTTP {response.status_code}: {response.text[:200]}"
                )
                return None
            
            # Parse response
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.warning(f"[LOOKUP] Backend response is not valid JSON: {e}")
                return None
            
            # Defensive validation: check response schema
            valid, error = _validate_lookup_response(data)
            if not valid:
                logger.warning(f"[LOOKUP] Backend response schema invalid: {error}. Will degrade gracefully.")
                # Return empty response instead of crashing
                return None
            
            logger.info(f"[LOOKUP] Backend response validated successfully")
            data["lookup_status"] = "success"
            return data
    
    except httpx.TimeoutException:
        logger.warning(f"[LOOKUP] Backend timeout (>= {timeout_seconds}s); returning empty matches")
        return None
    except (httpx.ConnectError, httpx.RequestError) as e:
        logger.warning(f"[LOOKUP] Backend connection failed: {e}")
        return None
    except Exception as e:
        logger.warning(f"[LOOKUP] Backend lookup exception: {e}")
        return None


def _lookup_with_urllib(
    url: str,
    payload: Dict[str, Any],
    auth_headers: Optional[Dict[str, str]],
    timeout_seconds: int,
) -> Optional[Dict[str, Any]]:
    """
    Send lookup request using urllib (standard library fallback).
    Returns None on any failure (logged as warning).
    Validates response schema strictly.
    """
    try:
        # Build request
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=auth_headers or {},
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        
        # Send request
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            if response.status != 200:
                logger.warning(
                    f"[LOOKUP] Backend returned HTTP {response.status}: {response.read(200).decode('utf-8', errors='ignore')}"
                )
                return None
            
            # Parse response
            try:
                response_data = json.loads(response.read().decode("utf-8"))
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"[LOOKUP] Backend response is not valid JSON: {e}")
                return None
            
            # Defensive validation: check response schema
            valid, error = _validate_lookup_response(response_data)
            if not valid:
                logger.warning(f"[LOOKUP] Backend response schema invalid: {error}. Will degrade gracefully.")
                # Return empty response instead of crashing
                return None
            
            logger.info(f"[LOOKUP] Backend response validated successfully")
            response_data["lookup_status"] = "success"
            return response_data
    
    except urllib.error.URLError as e:
        if "timed out" in str(e).lower():
            logger.warning(f"[LOOKUP] Backend timeout (>= {timeout_seconds}s); returning empty matches")
        else:
            logger.warning(f"[LOOKUP] Backend connection failed: {e}")
        return None
    except Exception as e:
        logger.warning(f"[LOOKUP] Backend lookup exception: {e}")
        return None
