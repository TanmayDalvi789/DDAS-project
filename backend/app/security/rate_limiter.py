"""Rate limiting and security utilities."""

import time
from typing import Dict, Tuple
from collections import defaultdict
from datetime import datetime, timedelta


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, identifier: str) -> Tuple[bool, Dict]:
        """
        Check if request is allowed.
        
        Args:
            identifier: Unique identifier (IP, user_id, api_key, etc.)
        
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # Remove old requests outside window
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]
        
        # Count current requests
        request_count = len(self.requests[identifier])
        
        # Check if allowed
        if request_count < self.max_requests:
            self.requests[identifier].append(now)
            is_allowed = True
        else:
            is_allowed = False
        
        # Calculate reset time
        if self.requests[identifier]:
            reset_time = self.requests[identifier][0] + self.window_seconds
        else:
            reset_time = now + self.window_seconds
        
        return is_allowed, {
            "limit": self.max_requests,
            "remaining": max(0, self.max_requests - request_count),
            "reset": int(reset_time),
        }
    
    def cleanup(self):
        """Remove entries with no recent requests."""
        now = time.time()
        window_start = now - self.window_seconds
        
        to_remove = []
        for identifier, requests in self.requests.items():
            valid_requests = [r for r in requests if r > window_start]
            if not valid_requests:
                to_remove.append(identifier)
            else:
                self.requests[identifier] = valid_requests
        
        for identifier in to_remove:
            del self.requests[identifier]


class IPRateLimiter:
    """Rate limiter based on IP address."""
    
    def __init__(self, max_requests: int = 1000, window_seconds: int = 60):
        self.limiter = RateLimiter(max_requests, window_seconds)
    
    def is_allowed(self, ip: str) -> Tuple[bool, Dict]:
        """Check if IP is allowed."""
        return self.limiter.is_allowed(ip)


class UserRateLimiter:
    """Rate limiter based on user ID."""
    
    def __init__(self, max_requests: int = 500, window_seconds: int = 60):
        self.limiter = RateLimiter(max_requests, window_seconds)
    
    def is_allowed(self, user_id: str) -> Tuple[bool, Dict]:
        """Check if user is allowed."""
        return self.limiter.is_allowed(user_id)


class APIKeyRateLimiter:
    """Rate limiter based on API key."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.limiter = RateLimiter(max_requests, window_seconds)
    
    def is_allowed(self, api_key: str) -> Tuple[bool, Dict]:
        """Check if API key is allowed."""
        return self.limiter.is_allowed(api_key)


# Global rate limiters
ip_rate_limiter = IPRateLimiter(max_requests=1000, window_seconds=60)
user_rate_limiter = UserRateLimiter(max_requests=500, window_seconds=60)
api_key_rate_limiter = APIKeyRateLimiter(max_requests=100, window_seconds=60)
