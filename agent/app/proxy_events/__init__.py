"""
Proxy event handling package.

STEP-3 Implementation:
- HTTP listener for proxy events
- Event validation (FAIL-CLOSED)
- Immediate processing via callback
"""

from .event_listener import ProxyEventListener
from .adapters import HTTPEventAdapter, FileEventAdapter, SocketEventAdapter
from .handler import EventHandler

__all__ = [
    'ProxyEventListener',
    'HTTPEventAdapter',
    'FileEventAdapter',
    'SocketEventAdapter',
    'EventHandler',
]
