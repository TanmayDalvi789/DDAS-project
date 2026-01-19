"""
Event Processing Handler - STEP-3 + STEP-4 + STEP-5 + STEP-6 + STEP-7 + STEP-8

Processes events received from proxy and enforces security decisions.

STEP-3 Responsibilities:
- Validate event format (already done by listener)
- Normalize using adapters

STEP-4 Responsibilities:
- Extract features from files (exact, fuzzy, semantic)
- Store features in cache

STEP-5 Responsibilities:
- Perform backend lookup using extracted features
- Store lookup results in cache

STEP-6 Responsibilities:
- Make ALLOW/WARN/BLOCK decision based on lookup results
- Log decision with explanation

STEP-7 Responsibilities:
- Enforce decision (ALLOW/WARN/BLOCK)
- Show user notifications
- Collect user response for WARN decisions
- Signal enforcement result back to proxy

STEP-8 Responsibilities (NEW):
- Send audit feedback to backend after enforcement
- Include decision, user action, and reason code
- Fail gracefully if backend unreachable
"""

import logging
from typing import Callable, Optional, Dict, Any
from app.features import extract_all_features
from app.cache.repository import CacheRepository
from app.backend_client.lookup_client import perform_lookup
from app.backend_client.feedback_client import FeedbackClient
from app.backend_client.auth import BackendAuth
from app.decision.engine import DecisionEngine
from app.decision.explain import DecisionExplainer
from app.ui.notifier import Notifier
from app.ui.prompts import Prompts
from app.constants import DECISION_ALLOW, DECISION_WARN, DECISION_BLOCK

logger = logging.getLogger(__name__)


class EventHandler:
    """
    Processes events received from proxy (STEP-3 through STEP-7).
    
    Responsibilities:
    - Normalize events using adapter (STEP-3)
    - Extract features from files (STEP-4)
    - Perform backend lookup (STEP-5)
    - Make security decision (STEP-6)
    - Enforce decision and notify user (STEP-7)
    
    Events are already validated by ProxyEventListener.
    """
    
    def __init__(
        self,
        adapter,
        on_valid_event: Callable = None,
        cache_repo: Optional[CacheRepository] = None,
        config = None
    ):
        """
        Initialize event handler.
        
        Args:
            adapter: EventAdapter instance for normalization
            on_valid_event: Callback for valid normalized events
            cache_repo: Cache repository for storing features
            config: Agent configuration (for feature extraction params)
        """
        self.adapter = adapter
        self.on_valid_event = on_valid_event
        self.cache_repo = cache_repo
        self.config = config
        self.decision_engine = DecisionEngine()
        self.explainer = DecisionExplainer()
        self.notifier = Notifier()
        self.prompts = Prompts()
        
        # Initialize feedback client (STEP-8)
        self.feedback_client = None
        if config:
            auth = BackendAuth(config.backend_api_key)
            self.feedback_client = FeedbackClient(
                config.backend_base_url,
                auth
            )
    
    def handle(self, event: dict):
        """
        Process valid event from proxy (STEP-3 through STEP-7).
        
        Pipeline:
        [EVENT] Event received
        [FEATURE] Feature extraction
        [LOOKUP] Backend lookup
        [DECISION] Decision made
        [ENFORCE] Decision enforced
        
        Event format:
        {
            "event_type": "file_download" | ...,
            "timestamp": unix_timestamp,
            "data": {
                "filename": str,
                "download_path": str (file path on disk),
                "mime_type": str,
                "url": str,
                ...
            }
        }
        
        Args:
            event: Valid event from proxy
        """
        try:
            event_id = event.get('event_id', 'unknown')
            filename = event.get('data', {}).get('filename', 'unknown') if isinstance(event.get('data'), dict) else 'unknown'
            
            logger.info(f"[EVENT] Received: {filename}")
            
            # Normalize event using adapter (STEP-3)
            normalized = self.adapter.receive_event(event)
            
            logger.debug(
                f"[EVENT] Normalized: type={normalized.get('event_type')}, ts={normalized.get('timestamp')}"
            )
            
            # Extract features if we have file path (STEP-4)
            features = None
            file_path = None
            lookup_results = None
            decision_result = None
            enforcement_result = None
            
            if normalized.get('data'):
                file_path = normalized['data'].get('download_path')
                filename = normalized['data'].get('filename', file_path or 'unknown')
                
                if file_path:
                    logger.info(f"[FEATURE] Starting extraction for: {filename}")
                    
                    # Extract all features (STEP-4)
                    partial_hash_bytes = (
                        self.config.feature_partial_hash_bytes
                        if self.config
                        else 4194304  # 4 MB default
                    )
                    
                    features = extract_all_features(
                        file_path,
                        metadata=normalized.get('data'),
                        partial_hash_bytes=partial_hash_bytes
                    )
                    
                    logger.info(f"[FEATURE] Extraction complete")
                    
                    # Store features in cache if repo available
                    if self.cache_repo and features:
                        self.cache_repo.save_features(
                            event_id,
                            file_path,
                            features
                        )
                        logger.debug(f"[FEATURE] Cached for: {event_id}")
                    
                    # STEP-5: Perform backend lookup (best-effort, non-blocking)
                    logger.info(f"[LOOKUP] Starting backend query")
                    
                    if self.cache_repo:
                        lookup_results = perform_lookup(
                            features=features,
                            metadata=normalized.get('data'),
                            backend_base_url=(
                                self.config.backend_base_url
                                if self.config
                                else "http://localhost:8001"
                            ),
                            timeout_seconds=5,
                        )
                        
                        if lookup_results:
                            logger.info(f"[LOOKUP] Complete: {lookup_results.get('lookup_status', 'unknown')}")
                            
                            # Store lookup results in cache
                            self.cache_repo.save_lookup_results(
                                event_id,
                                file_path,
                                lookup_results
                            )
                            logger.debug(
                                f"[LOOKUP] Results cached: "
                                f"status={lookup_results.get('lookup_status')}"
                            )
                        else:
                            logger.warning(f"[LOOKUP] No response from backend; degrading gracefully")
                    
                    # STEP-6: Make security decision
                    logger.info(f"[DECISION] Evaluating security decision")
                    
                    decision_result = self.decision_engine.decide(
                        event_id=event_id,
                        local_features=features,
                        backend_lookup_result=lookup_results,
                    )
                    
                    # Generate human-readable explanation
                    explanation = self.explainer.explain(decision_result)
                    decision_result["explanation"] = explanation
                    
                    # Log decision with explanation
                    decision = decision_result.get("decision")
                    triggered_rules = decision_result.get("triggered_rules", [])
                    
                    logger.info(
                        f"[DECISION] {decision.upper()} | "
                        f"Rules: {', '.join(triggered_rules) if triggered_rules else 'DEFAULT'} | "
                        f"{explanation}"
                    )
                    
                    # STEP-7: Enforce decision and notify user
                    logger.info(f"[ENFORCE] Enforcing {decision} decision")
                    
                    enforcement_result = self._enforce_decision(
                        event_id=event_id,
                        filename=filename,
                        decision=decision,
                        explanation=explanation,
                    )
                    
                    logger.info(
                        f"[ENFORCE] Complete: enforced={enforcement_result.get('enforced')}, "
                        f"response={enforcement_result.get('user_response')}"
                    )
                    
                    # STEP-8: Send audit feedback to backend (best-effort, non-blocking)
                    self._send_feedback(
                        event_id=event_id,
                        decision=decision,
                        user_response=enforcement_result.get('user_response'),
                        triggered_rules=triggered_rules,
                    )
                
                else:
                    logger.debug("[FEATURE] No file path in event; skipping feature extraction")
            
            # Forward to next stage (detection pipeline)
            if self.on_valid_event:
                self.on_valid_event(
                    normalized,
                    features,
                    lookup_results,
                    decision_result,
                    enforcement_result  # NEW in STEP-7
                )
        
        except Exception as e:
            logger.error(f"[ERROR] Event processing failed: {e}", exc_info=True)

    def _enforce_decision(
        self,
        event_id: str,
        filename: str,
        decision: str,
        explanation: str,
    ) -> Dict[str, Any]:
        """
        Enforce decision and notify user (STEP-7).

        Args:
            event_id: Event identifier
            filename: Name of the file
            decision: Decision from engine ("ALLOW" | "WARN" | "BLOCK")
            explanation: Human-readable explanation

        Returns:
            dict: Enforcement result
            {
                "event_id": str,
                "decision": str,
                "enforced": bool,
                "user_response": str or None,  # "PROCEED" | "CANCEL" for WARN
                "notification_sent": bool,
            }
        """
        enforcement_result = {
            "event_id": event_id,
            "decision": decision,
            "enforced": False,
            "user_response": None,
            "notification_sent": False,
        }

        try:
            if decision == DECISION_ALLOW:
                # ALLOW: Optionally show notification, always allow
                if self.config and self.config.allow_enforcement:
                    self.notifier.alert_allow(filename)
                    enforcement_result["notification_sent"] = True
                enforcement_result["enforced"] = True
                logger.info(f"[{event_id}] Enforcement: ALLOW (proceeding)")

            elif decision == DECISION_WARN:
                # WARN: Show notification and wait for user response
                if self.config and self.config.warn_enforcement:
                    self.notifier.alert_warn(filename, explanation)
                    enforcement_result["notification_sent"] = True
                    
                    # Wait for user confirmation
                    user_response = self.prompts.confirm_warn(
                        filename,
                        explanation,
                        timeout_seconds=(
                            self.config.warn_confirmation_timeout
                            if self.config
                            else 10
                        ),
                    )
                    
                    if user_response is True:
                        enforcement_result["user_response"] = "PROCEED"
                        enforcement_result["enforced"] = True
                        logger.info(f"[{event_id}] Enforcement: WARN (user proceeded)")
                    else:
                        enforcement_result["user_response"] = "CANCEL"
                        enforcement_result["enforced"] = False
                        logger.info(f"[{event_id}] Enforcement: WARN (user cancelled)")
                else:
                    # Enforcement disabled, default to cancel (safe)
                    enforcement_result["user_response"] = "CANCEL"
                    enforcement_result["enforced"] = False
                    logger.info(f"[{event_id}] Enforcement: WARN enforcement disabled (defaulting to cancel)")

            elif decision == DECISION_BLOCK:
                # BLOCK: Show non-dismissible notification and block immediately
                if self.config and self.config.block_enforcement:
                    self.notifier.alert_block(filename, explanation)
                    enforcement_result["notification_sent"] = True
                
                enforcement_result["enforced"] = False  # Block means do NOT allow
                enforcement_result["user_response"] = None  # No override for BLOCK
                logger.info(f"[{event_id}] Enforcement: BLOCK (immediate block, no override)")

            else:
                logger.warning(f"[{event_id}] Unknown decision: {decision}")
                enforcement_result["enforced"] = False

        except Exception as e:
            logger.error(f"[{event_id}] Error enforcing decision: {e}")
            # Safety default: fail closed for WARN/BLOCK
            if decision in (DECISION_WARN, DECISION_BLOCK):
                enforcement_result["enforced"] = False
            enforcement_result["user_response"] = "CANCEL"

        return enforcement_result

    def _send_feedback(
        self,
        event_id: str,
        decision: str,
        user_response: Optional[str] = None,
        triggered_rules: Optional[list] = None,
    ) -> None:
        """
        Send audit feedback to backend (STEP-8).

        Best-effort delivery:
        - Fails gracefully if backend unreachable
        - Logs success/failure for audit trail
        - Does not block event processing
        - No retries

        Args:
            event_id: Event identifier
            decision: ALLOW | WARN | BLOCK
            user_response: User action (PROCEED | CANCEL | None)
            triggered_rules: List of rules that triggered decision
        """
        if not self.feedback_client:
            logger.debug("[FEEDBACK] No feedback client configured; skipping")
            return

        try:
            # Normalize user_response
            user_action = user_response or "NONE"
            
            # For ALLOW and BLOCK, always use NONE
            if decision in (DECISION_ALLOW, DECISION_BLOCK):
                user_action = "NONE"

            # Build reason code from triggered rules
            if triggered_rules:
                reason_code = " + ".join(triggered_rules)
            else:
                reason_code = decision

            # Send feedback (non-blocking)
            success = self.feedback_client.send_feedback(
                agent_id=self.config.agent_id if self.config else "agent-unknown",
                event_id=event_id,
                decision=decision,
                user_action=user_action,
                reason_code=reason_code,
            )

            if success:
                logger.info(
                    f"[FEEDBACK] Sent for {event_id}: "
                    f"decision={decision}, user_action={user_action}, "
                    f"reason_code={reason_code}"
                )
            else:
                logger.warning(
                    f"[FEEDBACK] Failed to send for {event_id} "
                    "(backend unreachable, continuing anyway)"
                )

        except Exception as e:
            # Fail gracefully - never block event processing
            logger.warning(
                f"[FEEDBACK] Error sending feedback for {event_id}: {e} "
                "(continuing anyway)"
            )


