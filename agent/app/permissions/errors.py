"""Permission validation errors."""


class PermissionError(Exception):
    """Base exception for permission validation failures."""
    pass


class FileAccessDenied(PermissionError):
    """Cannot read/write required directories."""
    pass


class DatabaseAccessDenied(PermissionError):
    """Cannot access SQLite cache database directory."""
    pass


class NotificationPermissionDenied(PermissionError):
    """Cannot access notification system."""
    pass


class NetworkUnavailable(PermissionError):
    """Cannot reach backend API."""
    pass
