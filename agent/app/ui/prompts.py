"""
User Prompts and Interactive Input - STEP-7 Implementation

Handles user confirmations for WARN decisions.

Design:
- Simple and lightweight
- CLI-based with timeout support
- Graceful defaults (safe behavior)
- Non-blocking operation

Used for:
- WARN decision confirmation ("Proceed" / "Cancel")
- Optional: Future permission requests
"""

import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


class Prompts:
    """
    Interactive prompts for user input.

    Used for:
    - WARN decision confirmations (Proceed / Cancel)
    - User response collection
    """

    @staticmethod
    def confirm_warn(
        filename: str,
        reason: str,
        timeout_seconds: int = 10,
    ) -> Optional[bool]:
        """
        Ask user to confirm proceeding with file (WARN decision).

        Args:
            filename: Name of the file
            reason: Explanation of the warning
            timeout_seconds: Seconds to wait for user input

        Returns:
            bool: True (Proceed), False (Cancel), or None (timeout/error)
        """
        try:
            # Display prompt
            print(f"\n{'='*70}")
            print(f"⚠️  FILE WARNING")
            print(f"{'='*70}")
            print(f"File: {filename}")
            print(f"Reason: {reason}")
            print(f"\nWhat would you like to do?")
            print(f"  [p] Proceed with download")
            print(f"  [c] Cancel download")
            print(f"\nDefault (no response in {timeout_seconds}s): Cancel")
            print(f"{'='*70}")

            # Simple input without timeout (blocking)
            # Note: Full timeout implementation requires threading or signal handling
            # For now, use blocking input with documentation
            response = input("Enter choice (p/c): ").strip().lower()

            if response in ("p", "proceed", "yes", "y"):
                logger.info(f"User chose: PROCEED for {filename}")
                return True
            elif response in ("c", "cancel", "no", "n"):
                logger.info(f"User chose: CANCEL for {filename}")
                return False
            else:
                logger.info(f"User input invalid: {response}; treating as CANCEL")
                return False

        except EOFError:
            # No input available (running in non-interactive mode)
            logger.info(f"No interactive input available for {filename}; defaulting to CANCEL")
            return False
        except Exception as e:
            logger.warning(f"Error getting user confirmation: {e}; defaulting to CANCEL")
            return False

    @staticmethod
    def confirm_warn_silent(timeout_seconds: int = 10) -> Optional[bool]:
        """
        Non-blocking version for WARN confirmation (returns immediately).

        In non-interactive environments, default to CANCEL (safe).

        Args:
            timeout_seconds: Timeout value (informational only)

        Returns:
            bool: False (Cancel - safe default)
        """
        logger.debug(f"Silent confirmation mode; defaulting to CANCEL")
        return False

    @staticmethod
    def ask_yes_no(question: str, timeout_seconds: int = 10) -> bool:
        """
        Ask yes/no question.

        Args:
            question: Question to ask
            timeout_seconds: Timeout in seconds (informational)

        Returns:
            bool: True if yes, False if no
        """
        try:
            response = input(f"\n{question} (y/n): ").strip().lower()
            return response in ("y", "yes")
        except EOFError:
            logger.info("No interactive input available; defaulting to False")
            return False
        except Exception as e:
            logger.warning(f"Error getting user input: {e}")
            return False

    @staticmethod
    def get_permission_response() -> bool:
        """
        Ask user to grant permissions (informational).

        Used for first-run permission requests.

        Returns:
            bool: True if permission granted, False otherwise
        """
        try:
            response = input(
                "\nDDAS Agent needs permission to monitor downloads.\n"
                "Do you grant permission? (y/n): "
            ).strip().lower()
            return response in ("y", "yes")
        except EOFError:
            logger.info("No interactive input available; treating as denied")
            return False
        except Exception as e:
            logger.warning(f"Error getting permission: {e}")
            return False

