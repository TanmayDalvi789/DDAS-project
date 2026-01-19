"""
Decision Engine - STEP-6 Implementation

Makes deterministic ALLOW / WARN / BLOCK decisions based on backend lookup scores.

Key design decisions:
1. Decision made ONLY by agent (backend provides scores, never decisions)
2. Deterministic and explainable logic (no ML, no averaging)
3. Fusion rule: BLOCK > WARN > ALLOW (precedence only)
4. Fast execution (no async, no persistence)
5. Graceful handling of missing signals (ignore if feature not extracted)

Decision Rules:
A. EXACT MATCH: similarity_type == "exact" AND score == 1.0 → BLOCK
B. FUZZY MATCH: score >= FUZZY_BLOCK_THRESHOLD → BLOCK, else >= FUZZY_WARN_THRESHOLD → WARN
C. SEMANTIC MATCH: score >= SEMANTIC_BLOCK_THRESHOLD → BLOCK, else >= SEMANTIC_WARN_THRESHOLD → WARN
D. FUSION: Multiple signals → precedence (BLOCK > WARN > ALLOW)
E. DEFAULT: No rule triggers → ALLOW
"""

import logging
from typing import Dict, Any, Optional, List
from app.constants import (
    DECISION_ALLOW,
    DECISION_WARN,
    DECISION_BLOCK,
    FUZZY_WARN_THRESHOLD,
    FUZZY_BLOCK_THRESHOLD,
    SEMANTIC_WARN_THRESHOLD,
    SEMANTIC_BLOCK_THRESHOLD,
)

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Makes final ALLOW / WARN / BLOCK decisions based on backend lookup scores.

    Receives:
    - local_features (optional): exact_hash, fuzzy_sig, semantic_vec
    - backend_lookup_result (optional): matches array with scores

    Outputs:
    - decision: ALLOW | WARN | BLOCK
    - explanation: Human-readable reason
    - triggered_rules: Which rules caused this decision (for audit)
    """

    def decide(
        self,
        event_id: str,
        local_features: Optional[Dict[str, Any]] = None,
        backend_lookup_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make decision based on local features and backend lookup scores.

        Args:
            event_id: Event identifier for logging
            local_features: Extracted local features (optional)
                {
                    "exact": {"value": "hash123"},
                    "fuzzy": {"value": [...signature...]},
                    "semantic": {"vector": [...embedding...]},
                }
            backend_lookup_result: Result from backend lookup (optional)
                {
                    "matches": [
                        {
                            "match_id": "ref_123",
                            "similarity_type": "exact" | "fuzzy" | "semantic",
                            "score": 0.0-1.0,
                            "reference_metadata": {...}
                        },
                        ...
                    ],
                    "lookup_status": "success" | "error"
                }

        Returns:
            dict: Decision result
            {
                "event_id": str,
                "decision": "ALLOW" | "WARN" | "BLOCK",
                "triggered_rules": ["rule_name", ...],  # Which rules triggered
                "scores_found": {
                    "exact": float or None,
                    "fuzzy": float or None,
                    "semantic": float or None,
                },
                "explanation": str,
            }
        """
        # Initialize result structure
        result = {
            "event_id": event_id,
            "decision": DECISION_ALLOW,  # Default
            "triggered_rules": [],
            "scores_found": {
                "exact": None,
                "fuzzy": None,
                "semantic": None,
            },
            "explanation": "",
        }

        # Handle empty/missing backend lookup result
        if not backend_lookup_result or "matches" not in backend_lookup_result:
            result["explanation"] = "No backend lookup performed or no matches available. Defaulting to ALLOW."
            logger.debug(f"[{event_id}] No lookup result; decision=ALLOW")
            return result

        matches = backend_lookup_result.get("matches", [])

        # If no matches found, default to ALLOW
        if not matches:
            result["explanation"] = "No similar files found in backend database. File is ALLOWED."
            logger.debug(f"[{event_id}] No matches found; decision=ALLOW")
            return result

        # Process each match and collect scores by type
        exact_scores = []
        fuzzy_scores = []
        semantic_scores = []

        for match in matches:
            if not isinstance(match, dict):
                continue

            similarity_type = match.get("similarity_type", "").lower()
            score = match.get("score")

            # Skip invalid scores
            if score is None or not isinstance(score, (int, float)):
                continue

            # Collect scores by type
            if similarity_type == "exact":
                exact_scores.append(score)
            elif similarity_type == "fuzzy":
                fuzzy_scores.append(score)
            elif similarity_type == "semantic":
                semantic_scores.append(score)

        # Store highest score found for each type (for explanation)
        if exact_scores:
            result["scores_found"]["exact"] = max(exact_scores)
        if fuzzy_scores:
            result["scores_found"]["fuzzy"] = max(fuzzy_scores)
        if semantic_scores:
            result["scores_found"]["semantic"] = max(semantic_scores)

        # ====================================================================
        # Apply Decision Rules (in precedence order: BLOCK > WARN > ALLOW)
        # ====================================================================

        # RULE A: Exact Match Rule
        # If any exact match with score == 1.0 → BLOCK
        if exact_scores and any(s == 1.0 for s in exact_scores):
            result["decision"] = DECISION_BLOCK
            result["triggered_rules"].append("EXACT_MATCH")
            logger.debug(f"[{event_id}] Exact match found; decision=BLOCK")
            return result

        # RULE B: Fuzzy Match Rule - BLOCK threshold
        # If fuzzy score >= FUZZY_BLOCK_THRESHOLD → BLOCK
        if fuzzy_scores and any(s >= FUZZY_BLOCK_THRESHOLD for s in fuzzy_scores):
            result["decision"] = DECISION_BLOCK
            result["triggered_rules"].append("FUZZY_BLOCK")
            logger.debug(
                f"[{event_id}] Fuzzy BLOCK threshold reached ({max(fuzzy_scores):.2f} >= {FUZZY_BLOCK_THRESHOLD}); decision=BLOCK"
            )
            return result

        # RULE C: Semantic Match Rule - BLOCK threshold
        # If semantic score >= SEMANTIC_BLOCK_THRESHOLD → BLOCK
        if semantic_scores and any(s >= SEMANTIC_BLOCK_THRESHOLD for s in semantic_scores):
            result["decision"] = DECISION_BLOCK
            result["triggered_rules"].append("SEMANTIC_BLOCK")
            logger.debug(
                f"[{event_id}] Semantic BLOCK threshold reached ({max(semantic_scores):.2f} >= {SEMANTIC_BLOCK_THRESHOLD}); decision=BLOCK"
            )
            return result

        # RULE B (continued): Fuzzy Match Rule - WARN threshold
        # If fuzzy score >= FUZZY_WARN_THRESHOLD → WARN
        if fuzzy_scores and any(s >= FUZZY_WARN_THRESHOLD for s in fuzzy_scores):
            result["decision"] = DECISION_WARN
            result["triggered_rules"].append("FUZZY_WARN")
            logger.debug(
                f"[{event_id}] Fuzzy WARN threshold reached ({max(fuzzy_scores):.2f} >= {FUZZY_WARN_THRESHOLD}); decision=WARN"
            )
            return result

        # RULE C (continued): Semantic Match Rule - WARN threshold
        # If semantic score >= SEMANTIC_WARN_THRESHOLD → WARN
        if semantic_scores and any(s >= SEMANTIC_WARN_THRESHOLD for s in semantic_scores):
            result["decision"] = DECISION_WARN
            result["triggered_rules"].append("SEMANTIC_WARN")
            logger.debug(
                f"[{event_id}] Semantic WARN threshold reached ({max(semantic_scores):.2f} >= {SEMANTIC_WARN_THRESHOLD}); decision=WARN"
            )
            return result

        # RULE E: Default
        # No rule triggered → ALLOW
        result["decision"] = DECISION_ALLOW
        result["explanation"] = (
            "File similarity scores below warning thresholds. File is ALLOWED. "
            f"(Exact: {result['scores_found']['exact']}, "
            f"Fuzzy: {result['scores_found']['fuzzy']}, "
            f"Semantic: {result['scores_found']['semantic']})"
        )
        logger.debug(f"[{event_id}] No thresholds exceeded; decision=ALLOW")
        return result

