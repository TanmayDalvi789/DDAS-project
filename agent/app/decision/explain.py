"""
Decision Explanation - STEP-6 Implementation

Generates human-readable explanations for ALLOW / WARN / BLOCK decisions.

Purpose:
- Convert technical scores to user-friendly descriptions
- Explain which rules triggered the decision
- Provide actionable feedback for review
- Support audit trail (deterministic, reproducible)

Design:
- No technical jargon (admin/user friendly)
- Concise yet informative
- Deterministic (same decision always produces same explanation)
"""

import logging
from typing import Dict, Any
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


class DecisionExplainer:
    """
    Generates human-readable explanations for decisions.

    Converts decision engine output to user-friendly descriptions.
    """

    @staticmethod
    def explain(decision_result: Dict[str, Any]) -> str:
        """
        Generate human-readable explanation of decision.

        Args:
            decision_result: Output from DecisionEngine.decide()
            {
                "event_id": str,
                "decision": "ALLOW" | "WARN" | "BLOCK",
                "triggered_rules": ["rule_name", ...],
                "scores_found": {
                    "exact": float or None,
                    "fuzzy": float or None,
                    "semantic": float or None,
                },
                "explanation": str,
            }

        Returns:
            str: User-friendly explanation
        """
        decision = decision_result.get("decision", DECISION_ALLOW)
        triggered_rules = decision_result.get("triggered_rules", [])
        scores = decision_result.get("scores_found", {})

        # Build explanation based on decision and triggered rules
        if decision == DECISION_ALLOW:
            return DecisionExplainer._explain_allow(scores)
        elif decision == DECISION_WARN:
            return DecisionExplainer._explain_warn(triggered_rules, scores)
        elif decision == DECISION_BLOCK:
            return DecisionExplainer._explain_block(triggered_rules, scores)
        else:
            return f"Unknown decision: {decision}"

    @staticmethod
    def _explain_allow(scores: Dict[str, Any]) -> str:
        """
        Explain ALLOW decision.

        Args:
            scores: Dictionary with exact, fuzzy, semantic scores

        Returns:
            str: User-friendly explanation
        """
        # Check if any scores were found
        scores_found = [
            (name, score)
            for name, score in scores.items()
            if score is not None
        ]

        if not scores_found:
            return "No similarity detected. File is allowed."

        # Scores found but below warning threshold
        score_summary = ", ".join(
            f"{name}: {score:.0%}" for name, score in scores_found
        )
        return f"File similarity is low ({score_summary}). File is allowed."

    @staticmethod
    def _explain_warn(triggered_rules: list, scores: Dict[str, Any]) -> str:
        """
        Explain WARN decision.

        Args:
            triggered_rules: Rules that caused WARN decision
            scores: Dictionary with exact, fuzzy, semantic scores

        Returns:
            str: User-friendly explanation
        """
        explanations = []

        if "FUZZY_WARN" in triggered_rules:
            score = scores.get("fuzzy")
            if score:
                explanations.append(
                    f"File has moderate similarity to a known file "
                    f"(fuzzy match: {score:.0%}, threshold: {FUZZY_WARN_THRESHOLD:.0%})"
                )

        if "SEMANTIC_WARN" in triggered_rules:
            score = scores.get("semantic")
            if score:
                explanations.append(
                    f"File content is moderately similar to a known file "
                    f"(semantic match: {score:.0%}, threshold: {SEMANTIC_WARN_THRESHOLD:.0%})"
                )

        if not explanations:
            explanations.append("File matches warning criteria.")

        base = ". ".join(explanations)
        return f"{base}. Please review before downloading."

    @staticmethod
    def _explain_block(triggered_rules: list, scores: Dict[str, Any]) -> str:
        """
        Explain BLOCK decision.

        Args:
            triggered_rules: Rules that caused BLOCK decision
            scores: Dictionary with exact, fuzzy, semantic scores

        Returns:
            str: User-friendly explanation
        """
        if "EXACT_MATCH" in triggered_rules:
            return "File is identical to a known file. BLOCKED for safety."

        if "FUZZY_BLOCK" in triggered_rules:
            score = scores.get("fuzzy")
            if score:
                return (
                    f"File is very similar to a known file "
                    f"(fuzzy match: {score:.0%}, threshold: {FUZZY_BLOCK_THRESHOLD:.0%}). "
                    f"BLOCKED for safety."
                )

        if "SEMANTIC_BLOCK" in triggered_rules:
            score = scores.get("semantic")
            if score:
                return (
                    f"File content is very similar to a known suspicious file "
                    f"(semantic match: {score:.0%}, threshold: {SEMANTIC_BLOCK_THRESHOLD:.0%}). "
                    f"BLOCKED for safety."
                )

        return "File matches safety criteria. BLOCKED."

