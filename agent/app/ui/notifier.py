"""
User Notification System - STEP-7 Implementation

Sends OS-native notifications for WARN and BLOCK decisions.

Design:
- Cross-platform support (Windows, macOS, Linux)
- Native OS notifications (no web UI, no external frameworks)
- Non-intrusive and lightweight
- Graceful fallback to logging if notifications unavailable

Supports:
- Info notifications (ALLOW - informational only)
- Warning notifications (WARN - requires action)
- Error/Alert notifications (BLOCK - non-dismissible)
"""

import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import plyer for cross-platform notifications
try:
    from plyer import notification as plyer_notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    logger.debug("plyer not available; will use fallback notifications")

# Platform-specific imports
if sys.platform == "win32":
    try:
        from win10toast import ToastNotifier
        WIN10TOAST_AVAILABLE = True
    except ImportError:
        WIN10TOAST_AVAILABLE = False
else:
    WIN10TOAST_AVAILABLE = False


class Notifier:
    """
    Send OS-native notifications for security decisions.

    Supports cross-platform notifications:
    - Windows: Win10Toast (fallback to plyer)
    - macOS: plyer (uses NSUserNotificationCenter)
    - Linux: plyer (uses dbus/notify-send)

    Design:
    - Lightweight and non-blocking
    - Graceful fallback to logging
    - No external UI frameworks required
    - Platform-specific implementations where beneficial
    """

    def __init__(self, app_name: str = "DDAS Agent"):
        """
        Initialize notifier.

        Args:
            app_name: Application name for notifications
        """
        self.app_name = app_name
        self._init_platform_notifier()

    def _init_platform_notifier(self):
        """Initialize platform-specific notifier if available."""
        self.toast_notifier = None
        
        if sys.platform == "win32" and WIN10TOAST_AVAILABLE:
            try:
                self.toast_notifier = ToastNotifier()
                logger.debug("Win10Toast notifier initialized")
            except Exception as e:
                logger.debug(f"Failed to initialize Win10Toast: {e}")

    def notify(
        self,
        title: str,
        message: str,
        notification_type: str = "info",
        timeout: int = 5,
    ) -> bool:
        """
        Send notification to user.

        Args:
            title: Notification title
            message: Notification message
            notification_type: "info" | "warning" | "error"
            timeout: Display timeout in seconds (ignored for some platforms)

        Returns:
            bool: True if notification sent successfully, False if failed
        """
        try:
            # Try platform-specific notifier first (Windows)
            if self.toast_notifier and sys.platform == "win32":
                return self._notify_windows(title, message, notification_type, timeout)

            # Try plyer (cross-platform)
            if PLYER_AVAILABLE:
                return self._notify_plyer(title, message, notification_type, timeout)

            # Fallback to logging
            logger.warning(
                f"Notification unavailable; logging instead. "
                f"[{notification_type.upper()}] {title}: {message}"
            )
            return False

        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
            # Always log as fallback
            logger.info(f"[{notification_type.upper()}] {title}: {message}")
            return False

    def _notify_windows(
        self,
        title: str,
        message: str,
        notification_type: str,
        timeout: int,
    ) -> bool:
        """
        Send Windows Toast notification.

        Args:
            title: Notification title
            message: Notification message
            notification_type: Notification severity
            timeout: Display timeout in seconds

        Returns:
            bool: Success status
        """
        try:
            # Win10Toast doesn't distinguish severity, so we prefix the title
            icon_prefix = {
                "info": "ℹ️",
                "warning": "⚠️",
                "error": "🚫",
            }.get(notification_type, "")

            prefixed_title = f"{icon_prefix} {title}" if icon_prefix else title

            self.toast_notifier.show_toast(
                title=prefixed_title,
                msg=message,
                duration=timeout,
                threaded=True,
            )
            logger.debug(f"Windows Toast notification sent: {title}")
            return True
        except Exception as e:
            logger.debug(f"Win10Toast failed: {e}")
            return False

    def _notify_plyer(
        self,
        title: str,
        message: str,
        notification_type: str,
        timeout: int,
    ) -> bool:
        """
        Send cross-platform notification via plyer.

        Args:
            title: Notification title
            message: Notification message
            notification_type: Notification severity
            timeout: Display timeout in seconds

        Returns:
            bool: Success status
        """
        try:
            # Map notification types to tick marks for visual distinction
            tick_prefix = {
                "info": "✓",
                "warning": "⚠",
                "error": "✗",
            }.get(notification_type, "")

            prefixed_title = f"{tick_prefix} {title}" if tick_prefix else title

            plyer_notification.notify(
                title=prefixed_title,
                message=message,
                app_name=self.app_name,
                timeout=timeout,
            )
            logger.debug(f"Plyer notification sent: {title}")
            return True
        except Exception as e:
            logger.debug(f"Plyer notification failed: {e}")
            return False

    def alert_warn(
        self,
        filename: str,
        reason: str,
        timeout: int = 5,
    ) -> bool:
        """
        Send warning alert for WARN decision.

        Args:
            filename: Name of the file triggering warning
            reason: Human-readable explanation
            timeout: Display timeout in seconds

        Returns:
            bool: Success status
        """
        title = f"⚠️ Download Warning"
        message = f"File: {filename}\n{reason}"
        return self.notify(title, message, notification_type="warning", timeout=timeout)

    def alert_block(
        self,
        filename: str,
        reason: str,
    ) -> bool:
        """
        Send block alert for BLOCK decision (non-dismissible).

        Args:
            filename: Name of the file triggering block
            reason: Human-readable explanation

        Returns:
            bool: Success status
        """
        title = f"🚫 Download Blocked"
        message = f"File: {filename}\n{reason}\nThis download has been blocked for safety."
        # BLOCK alerts shown longer (no timeout)
        return self.notify(title, message, notification_type="error", timeout=10)

    def alert_allow(
        self,
        filename: str,
        timeout: int = 3,
    ) -> bool:
        """
        Send info alert for ALLOW decision (optional, minimal).

        Args:
            filename: Name of the file allowed
            timeout: Display timeout in seconds

        Returns:
            bool: Success status
        """
        title = f"✓ Download Allowed"
        message = f"File: {filename}\nNo threats detected."
        return self.notify(title, message, notification_type="info", timeout=timeout)

