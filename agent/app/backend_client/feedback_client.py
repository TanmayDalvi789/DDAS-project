"""Backend feedback client - STEP-8 Feedback & Audit Sync.

Sends audit feedback to backend after enforcement completes.

Responsibilities:
- Send ALLOW/WARN/BLOCK decision feedback
- Include user action (if any)
- Include decision rationale (reason_code)
- Fail gracefully if backend unreachable
- No retries, no buffering, best-effort delivery

Defensive Measures:
- Validates payload structure before sending
- Defensively parses backend response
- Logs all failures as warnings (never crashes)
- Logs all successes for audit trail
"""

import json
import logging
import time
from typing import Optional, Dict, Any

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    import urllib.request
    import urllib.error

from app.backend_client.auth import BackendAuth

logger = logging.getLogger(__name__)


def _validate_feedback_payload(
    payload: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """
    Validate feedback payload before sending.

    Expected payload:
    {
        "agent_id": string,
        "event_id": string,
        "decision": "ALLOW" | "WARN" | "BLOCK",
        "user_action": "PROCEED" | "CANCEL" | "NONE",
        "reason_code": string,
        "timestamp": int (epoch seconds) or string (ISO 8601),
    }

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(payload, dict):
        return False, f"Payload must be dict, got {type(payload)}"

    # Check required fields
    required_fields = {
        "agent_id",
        "event_id",
        "decision",
        "user_action",
        "reason_code",
        "timestamp",
    }
    missing = required_fields - set(payload.keys())
    if missing:
        return False, f"Missing required fields: {missing}"

    # Validate types
    if not isinstance(payload["agent_id"], str) or not payload["agent_id"]:
        return False, "agent_id must be non-empty string"

    if not isinstance(payload["event_id"], str) or not payload["event_id"]:
        return False, "event_id must be non-empty string"

    # Validate decision enum
    valid_decisions = {"ALLOW", "WARN", "BLOCK"}
    if payload["decision"] not in valid_decisions:
        return False, f"decision must be one of {valid_decisions}"

    # Validate user_action enum
    valid_actions = {"PROCEED", "CANCEL", "NONE"}
    if payload["user_action"] not in valid_actions:
        return False, f"user_action must be one of {valid_actions}"

    # Validate user_action consistency
    # ALLOW and BLOCK should have user_action = NONE
    if payload["decision"] in ("ALLOW", "BLOCK"):
        if payload["user_action"] != "NONE":
            return False, f"{payload['decision']} should have user_action='NONE'"

    # WARN should have user_action = PROCEED or CANCEL
    if payload["decision"] == "WARN":
        if payload["user_action"] not in ("PROCEED", "CANCEL"):
            return False, "WARN must have user_action='PROCEED' or 'CANCEL'"

    if not isinstance(payload["reason_code"], str) or not payload["reason_code"]:
        return False, "reason_code must be non-empty string"

    # Timestamp can be int or string
    timestamp = payload["timestamp"]
    if not isinstance(timestamp, (int, float, str)):
        return False, "timestamp must be int/float (epoch) or string (ISO 8601)"

    return True, None


class FeedbackClient:
    """
    Send audit feedback to backend.

    Design:
    - Best-effort delivery (no retries)
    - Fail gracefully if unreachable
    - No buffering or persistence
    - Clear logging for audit trail
    """

    def __init__(self, base_url: str, auth: BackendAuth):
        """
        Initialize feedback client.

        Args:
            base_url: Backend URL (e.g., "http://localhost:8001")
            auth: BackendAuth instance for headers
        """
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.endpoint = f"{self.base_url}/api/v1/agent/feedback"

    def send_feedback(
        self,
        agent_id: str,
        event_id: str,
        decision: str,
        user_action: Optional[str] = None,
        reason_code: Optional[str] = None,
        timestamp: Optional[int] = None,
    ) -> bool:
        """
        Send feedback to backend.

        Args:
            agent_id: Agent identifier
            event_id: Event identifier
            decision: ALLOW | WARN | BLOCK
            user_action: PROCEED | CANCEL | NONE (optional, defaults to NONE)
            reason_code: Explanation string (optional)
            timestamp: UTC epoch seconds (optional, defaults to now)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        # Normalize defaults
        if user_action is None:
            user_action = "NONE"
        if reason_code is None:
            reason_code = decision
        if timestamp is None:
            timestamp = int(time.time())

        # Build payload
        payload = {
            "agent_id": agent_id,
            "event_id": event_id,
            "decision": decision,
            "user_action": user_action,
            "reason_code": reason_code,
            "timestamp": timestamp,
        }

        # Validate payload
        valid, error = _validate_feedback_payload(payload)
        if not valid:
            logger.warning(
                f"[FEEDBACK] Invalid payload: {error} | "
                f"agent_id={agent_id}, event_id={event_id}, decision={decision}"
            )
            return False

        # Try to send
        try:
            if HTTPX_AVAILABLE:
                return self._send_with_httpx(payload)
            else:
                return self._send_with_urllib(payload)
        except Exception as e:
            logger.warning(
                f"[FEEDBACK] Failed to send: {e} | "
                f"agent_id={agent_id}, event_id={event_id}, decision={decision}"
            )
            return False

    def _send_with_httpx(self, payload: Dict[str, Any]) -> bool:
        """Send feedback using httpx."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    self.endpoint,
                    json=payload,
                    headers=self.auth.get_headers(),
                )

                # Log response
                if response.status_code == 200 or response.status_code == 201:
                    logger.info(
                        f"[FEEDBACK] Sent successfully | "
                        f"event_id={payload['event_id']}, decision={payload['decision']}, "
                        f"user_action={payload['user_action']}"
                    )
                    return True
                else:
                    logger.warning(
                        f"[FEEDBACK] Received non-success status | "
                        f"status={response.status_code}, event_id={payload['event_id']}"
                    )
                    # Log response body if available (for debugging)
                    try:
                        error_detail = response.json()
                        logger.debug(f"[FEEDBACK] Response body: {error_detail}")
                    except Exception:
                        pass
                    return False

        except Exception as e:
            logger.warning(f"[FEEDBACK] httpx error: {e}")
            return False

    def _send_with_urllib(self, payload: Dict[str, Any]) -> bool:
        """Send feedback using urllib (fallback)."""
        try:
            import json as json_module

            data = json_module.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                self.endpoint,
                data=data,
                headers=self.auth.get_headers(),
                method="POST",
            )

            with urllib.request.urlopen(request, timeout=5) as response:
                status = response.status
                if status == 200 or status == 201:
                    logger.info(
                        f"[FEEDBACK] Sent successfully | "
                        f"event_id={payload['event_id']}, decision={payload['decision']}, "
                        f"user_action={payload['user_action']}"
                    )
                    return True
                else:
                    logger.warning(
                        f"[FEEDBACK] Received non-success status | "
                        f"status={status}, event_id={payload['event_id']}"
                    )
                    return False

        except urllib.error.HTTPError as e:
            logger.warning(
                f"[FEEDBACK] HTTP error {e.code}: {e.reason} | "
                f"event_id={payload['event_id']}"
            )
            return False
        except urllib.error.URLError as e:
            logger.warning(f"[FEEDBACK] URL error: {e.reason}")
            return False
        except Exception as e:
            logger.warning(f"[FEEDBACK] urllib error: {e}")
            return False


# ============================================================================
# Module-level convenience function
# ============================================================================


def send_feedback(
    agent_id: str,
    event_id: str,
    decision: str,
    user_action: Optional[str] = None,
    reason_code: Optional[str] = None,
    timestamp: Optional[int] = None,
    backend_url: str = "http://localhost:8001",
    api_key: str = "",
) -> bool:
    """
    Module-level convenience function to send feedback.

    Args:
        agent_id: Agent identifier
        event_id: Event identifier
        decision: ALLOW | WARN | BLOCK
        user_action: User action (optional)
        reason_code: Reason code (optional)
        timestamp: Timestamp (optional)
        backend_url: Backend base URL
        api_key: API key for auth

    Returns:
        bool: True if sent successfully
    """
    auth = BackendAuth(api_key)
    client = FeedbackClient(backend_url, auth)
    return client.send_feedback(
        agent_id=agent_id,
        event_id=event_id,
        decision=decision,
        user_action=user_action,
        reason_code=reason_code,
        timestamp=timestamp,
    )
